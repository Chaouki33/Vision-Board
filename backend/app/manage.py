"""Commandes de secours, à lancer sur le serveur (depuis le dossier backend).

    .venv/Scripts/python -m app.manage users                      liste les comptes
    .venv/Scripts/python -m app.manage set-password EMAIL         choisir un mot de passe (saisie masquée)
    .venv/Scripts/python -m app.manage reset-password EMAIL       nouveau mot de passe provisoire
    .venv/Scripts/python -m app.manage make-admin EMAIL           donne les droits d'administrateur

Utile notamment quand l'administrateur a oublié son mot de passe : personne d'autre ne peut
alors le réinitialiser depuis l'application. Le mot de passe provisoire est affiché et enregistré
dans backend/acces_provisoire.txt ; il devra être changé à la connexion.
"""
import argparse
import getpass
import sys
from datetime import datetime

from sqlalchemy import select

from .config import BACKEND_DIR
from .database import SessionLocal, create_schema
from .models import User
from .routers.admin import temporary_password
from .security import hash_password

ACCESS_FILE = BACKEND_DIR / "acces_provisoire.txt"


def _find(db, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if user is None:
        sys.exit(f"Aucun compte avec l'e-mail {email}")
    return user


def _read(prompt: str) -> str:
    # Saisie masquée dans un vrai terminal (PowerShell, cmd, VS Code) ; sinon (Git Bash, saisie
    # redirigée) getpass peut bloquer sous Windows : on lit alors la ligne normalement.
    if sys.stdin.isatty():
        return getpass.getpass(prompt + "(rien ne s'affiche) : ").strip()
    print(prompt + ": ", end="", flush=True)
    return sys.stdin.readline().strip()


def _ask_password() -> str:
    while True:
        first = _read("Nouveau mot de passe, 8 caractères minimum ")
        if len(first) < 8:
            print("Trop court : 8 caractères minimum.")
            continue
        if _read("Confirmez le mot de passe ") != first:
            print("Les deux saisies sont différentes, recommencez.")
            continue
        return first


def main() -> None:
    parser = argparse.ArgumentParser(description="Commandes d'administration de Vision Board")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("users", help="Liste les comptes")
    reset = sub.add_parser("reset-password", help="Génère un mot de passe provisoire")
    reset.add_argument("email")
    chosen = sub.add_parser("set-password", help="Définit un mot de passe choisi (saisie masquée)")
    chosen.add_argument("email")
    admin = sub.add_parser("make-admin", help="Donne les droits d'administrateur")
    admin.add_argument("email")
    args = parser.parse_args()

    create_schema()
    with SessionLocal() as db:
        if args.command == "users":
            for u in db.scalars(select(User).order_by(User.is_admin.desc(), User.email)):
                profile = "admin" if u.is_admin else "utilisateur"
                state = "actif" if u.is_active else "désactivé"
                print(f"{u.email:40} {profile:12} {state:10} {u.full_name}")
            return

        user = _find(db, args.email)
        if args.command == "make-admin":
            user.is_admin, user.is_active = True, True
            db.commit()
            print(f"{user.email} est administrateur.")
            return

        if args.command == "set-password":
            password = _ask_password()
            user.password_hash = hash_password(password)
            user.must_change_password = False
            user.is_active = True
            db.commit()
            print(f"Mot de passe enregistré. Connectez-vous avec {user.email} et ce mot de passe.")
            return

        password = temporary_password()
        user.password_hash = hash_password(password)
        user.must_change_password = True
        user.is_active = True
        db.commit()

    text = (f"Accès provisoire Vision Board — {datetime.now():%d/%m/%Y %H:%M}\n"
            f"  E-mail       : {user.email}\n  Mot de passe : {password}\n"
            "  À changer dès la connexion (l'application le demande automatiquement).\n\n")
    with ACCESS_FILE.open("a", encoding="utf-8") as f:
        f.write(text)
    print(text + f"Également enregistré dans {ACCESS_FILE}")


if __name__ == "__main__":
    main()
