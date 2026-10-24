from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import company_access, get_current_user, get_membership
from ..kpi.dashboards import create_default_dashboards
from ..kpi.references import size_from_profile
from ..models import Company, Membership, User
from ..schemas import CompanyIn, CompanyOut, MemberIn, MemberOut

router = APIRouter(prefix="/companies", tags=["Sociétés"])


def _out(company: Company, role: str) -> CompanyOut:
    return CompanyOut.model_validate(company).model_copy(update={"role": role})


@router.get("", response_model=list[CompanyOut])
def list_companies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.is_admin:
        roles = {m.company_id: m.role for m in user.memberships}
        return [_out(c, roles.get(c.id, "owner")) for c in db.scalars(select(Company).order_by(Company.name))]
    rows = db.execute(
        select(Company, Membership.role)
        .join(Membership, Membership.company_id == Company.id)
        .where(Membership.user_id == user.id)
        .order_by(Company.name)
    ).all()
    return [_out(company, role) for company, role in rows]


@router.post("", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_company(data: CompanyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    values = data.model_dump(exclude={"domains"})
    values["size"] = data.size or size_from_profile(data.employees, data.annual_revenue)
    company = Company(**values)
    company.memberships.append(Membership(user=user, role="owner"))
    db.add(company)
    db.flush()
    create_default_dashboards(db, company, data.domains)
    db.commit()
    return _out(company, "owner")


@router.get("/{company_id}", response_model=CompanyOut)
def get_company(company_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    membership = get_membership(db, user, company_id)
    return _out(membership.company, membership.role)


@router.put("/{company_id}", response_model=CompanyOut)
def update_company(company_id: int, data: CompanyIn, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    membership = get_membership(db, user, company_id, "editor")
    company = membership.company
    values = data.model_dump(exclude={"domains"})
    values["size"] = data.size or size_from_profile(data.employees, data.annual_revenue)
    for key, value in values.items():
        setattr(company, key, value)
    db.commit()
    return _out(company, membership.role)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(company: Company = Depends(company_access("owner")), db: Session = Depends(get_db)):
    db.delete(company)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- Membres
@router.get("/{company_id}/members", response_model=list[MemberOut])
def list_members(company: Company = Depends(company_access("viewer"))):
    return [MemberOut(user_id=m.user_id, email=m.user.email, full_name=m.user.full_name, role=m.role)
            for m in company.memberships]


@router.post("/{company_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def add_member(data: MemberIn, company: Company = Depends(company_access("owner")), db: Session = Depends(get_db)):
    target = db.scalar(select(User).where(User.email == data.email.lower()))
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun utilisateur avec cet e-mail : il doit d'abord créer un compte")
    membership = db.get(Membership, (target.id, company.id))
    if membership is None:
        membership = Membership(user_id=target.id, company_id=company.id, role=data.role)
        db.add(membership)
    else:
        membership.role = data.role
    db.commit()
    return MemberOut(user_id=target.id, email=target.email, full_name=target.full_name, role=membership.role)


@router.delete("/{company_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(user_id: int, company: Company = Depends(company_access("owner")), db: Session = Depends(get_db)):
    membership = db.get(Membership, (user_id, company.id))
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membre introuvable")
    owners = [m for m in company.memberships if m.role == "owner"]
    if membership.role == "owner" and len(owners) == 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La société doit garder au moins un propriétaire")
    db.delete(membership)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
