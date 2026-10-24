"""Administration de la plateforme : comptes utilisateurs et accès aux sociétés."""
import secrets
import string

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import require_admin
from ..models import Company, Dashboard, Dataset, Membership, Report, User
from pydantic import BaseModel, Field

from ..schemas import AdminUserCreated, AdminUserIn, AdminUserOut, AdminUserUpdate
from ..security import hash_password

router = APIRouter(prefix="/admin", tags=["Administration"])

ROLES = {"owner", "editor", "viewer"}
_ALPHABET = string.ascii_letters + string.digits


def temporary_password() -> str:
    """Mot de passe provisoire lisible : 4 groupes de 4 caractères (ex. Xk7p-2Lmq-...)."""
    alphabet = [c for c in _ALPHABET if c not in "0O1lI"]
    return "-".join("".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4))


def _out(user: User) -> AdminUserOut:
    companies = [{"company_id": m.company_id, "name": m.company.name, "role": m.role} for m in user.memberships]
    return AdminUserOut.model_validate(user).model_copy(update={"companies": companies})


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur introuvable")
    return user


def _set_access(db: Session, user: User, access: list[dict]) -> None:
    for item in access:
        company_id, role = item.get("company_id"), item.get("role", "viewer")
        if role not in ROLES or db.get(Company, company_id) is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Accès invalide (société ou rôle inconnu)")
        membership = db.get(Membership, (user.id, company_id))
        if membership is None:
            db.add(Membership(user_id=user.id, company_id=company_id, role=role))
        else:
            membership.role = role


def _other_active_admins(db: Session, user: User) -> int:
    return db.scalar(select(func.count(User.id)).where(User.is_admin, User.is_active, User.id != user.id))


@router.get("/users", response_model=list[AdminUserOut])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return [_out(u) for u in db.scalars(select(User).order_by(User.is_admin.desc(), User.full_name))]


@router.post("/users", response_model=AdminUserCreated, status_code=status.HTTP_201_CREATED)
def create_user(data: AdminUserIn, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet e-mail")
    password = data.password or temporary_password()
    user = User(email=email, full_name=data.full_name.strip(), password_hash=hash_password(password),
                is_admin=data.is_admin, must_change_password=True)
    db.add(user)
    db.flush()
    _set_access(db, user, data.companies)
    db.commit()
    db.refresh(user)
    return AdminUserCreated(user=_out(user), temporary_password=password)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(user_id: int, data: AdminUserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    losing_admin = (data.is_admin is False and user.is_admin) or (data.is_active is False and user.is_admin)
    if losing_admin and not _other_active_admins(db, user):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La plateforme doit garder au moins un administrateur actif")
    for field in ("full_name", "is_admin", "is_active"):
        value = getattr(data, field)
        if value is not None:
            setattr(user, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    return _out(user)


@router.post("/users/{user_id}/reset-password", response_model=AdminUserCreated)
def reset_password(user_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    password = temporary_password()
    user.password_hash = hash_password(password)
    user.must_change_password = True
    db.commit()
    return AdminUserCreated(user=_out(user), temporary_password=password)


@router.put("/users/{user_id}/companies", response_model=AdminUserOut)
def set_companies(user_id: int, access: list[dict], _: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Remplace la liste des sociétés accessibles par l'utilisateur."""
    user = _get_user(db, user_id)
    wanted = {a.get("company_id") for a in access}
    for membership in list(user.memberships):
        if membership.company_id not in wanted:
            others = [m for m in membership.company.memberships if m.role == "owner" and m.user_id != user.id]
            if membership.role == "owner" and not others:
                raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                    f"« {membership.company.name} » doit garder au moins un propriétaire")
            db.delete(membership)
    db.flush()
    _set_access(db, user, access)
    db.commit()
    db.refresh(user)
    return _out(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = _get_user(db, user_id)
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Vous ne pouvez pas supprimer votre propre compte")
    if user.is_admin and not _other_active_admins(db, user):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La plateforme doit garder au moins un administrateur actif")
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- Sociétés
class CompanyIds(BaseModel):
    ids: list[int] = Field(min_length=1)


def _count(db: Session, model, company_id: int) -> int:
    return db.scalar(select(func.count()).select_from(model).where(model.company_id == company_id))


@router.get("/companies")
def list_companies(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Toutes les sociétés de la plateforme, avec leurs membres et le volume de données."""
    out = []
    for c in db.scalars(select(Company).order_by(Company.name)):
        out.append({
            "id": c.id, "name": c.name, "sector": c.sector, "size": c.size, "city": c.city,
            "created_at": c.created_at,
            "owners": [m.user.full_name for m in c.memberships if m.role == "owner"],
            "members": len(c.memberships),
            "dashboards": _count(db, Dashboard, c.id),
            "datasets": _count(db, Dataset, c.id),
            "reports": _count(db, Report, c.id),
        })
    return out


@router.post("/companies/delete")
def delete_companies(data: CompanyIds, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Supprime définitivement des sociétés avec leurs fichiers, tableaux de bord et rapports."""
    companies = db.scalars(select(Company).where(Company.id.in_(data.ids))).all()
    if len(companies) != len(set(data.ids)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Société introuvable")
    names = [c.name for c in companies]
    for company in companies:
        db.delete(company)
    db.commit()
    return {"deleted": len(names), "names": names}
