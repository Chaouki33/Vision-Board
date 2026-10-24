from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import LoginIn, PasswordChangeIn, RegisterIn, TokenOut, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["Authentification"])


def _token(user: User) -> TokenOut:
    return TokenOut(access_token=create_access_token(user.id), user=UserOut.model_validate(user))


def _no_user_yet(db: Session) -> bool:
    return db.scalar(select(func.count(User.id))) == 0


@router.get("/config")
def auth_config(db: Session = Depends(get_db)):
    """Indique à l'écran de connexion si l'inscription libre est ouverte."""
    first_install = _no_user_yet(db)
    return {"registration_open": settings.allow_registration or first_install, "first_install": first_install}


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    first_install = _no_user_yet(db)
    if not (settings.allow_registration or first_install):
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Les comptes sont créés par l'administrateur : demandez-lui vos identifiants")
    email = data.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Un compte existe déjà avec cet e-mail")
    # Le tout premier compte de l'installation devient administrateur.
    user = User(email=email, full_name=data.full_name.strip(), password_hash=hash_password(data.password),
                is_admin=first_install, last_login_at=datetime.now(timezone.utc))
    db.add(user)
    db.commit()
    return _token(user)


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.lower().strip()))
    # Tolère un espace ou un retour à la ligne collé avec le mot de passe (copier-coller).
    candidates = {data.password, data.password.strip()}
    if user is None or not any(verify_password(p, user.password_hash) for p in candidates if p):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Ce compte est désactivé : contactez l'administrateur")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    return _token(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.post("/password", response_model=UserOut)
def change_password(data: PasswordChangeIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Mot de passe actuel incorrect")
    if data.new_password == data.current_password:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Le nouveau mot de passe doit être différent de l'actuel")
    user.password_hash = hash_password(data.new_password)
    user.must_change_password = False
    db.commit()
    return user
