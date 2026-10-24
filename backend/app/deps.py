from types import SimpleNamespace

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import Company, Membership, User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)

ROLE_LEVEL = {"viewer": 1, "editor": 2, "owner": 3}


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)
) -> User:
    user_id = decode_access_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session invalide ou expirée")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Réservé à l'administrateur")
    return user


def get_membership(db: Session, user: User, company_id: int, min_role: str = "viewer") -> Membership:
    membership = db.get(Membership, (user.id, company_id))
    if membership is None and user.is_admin:
        # L'administrateur a un accès complet à toutes les sociétés, sans en être membre.
        company = db.get(Company, company_id)
        if company is not None:
            # Objet d'accès non persisté (un vrai Membership serait ajouté à la session).
            return SimpleNamespace(user=user, company=company, role="owner", user_id=user.id, company_id=company.id)
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Société introuvable")
    if ROLE_LEVEL[membership.role] < ROLE_LEVEL[min_role]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Droits insuffisants pour cette action")
    return membership


def company_access(min_role: str):
    def dependency(
        company_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> Company:
        return get_membership(db, user, company_id, min_role).company

    return dependency
