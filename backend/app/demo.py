"""Jeu de démonstration : comptes, sociétés, fichiers importés et tableaux de bord.

Utilisation (depuis le dossier backend) :
    .venv/Scripts/python -m app.demo
    .venv/Scripts/python -m app.demo --admin-email vous@exemple.ma

Les mots de passe provisoires sont générés, affichés et enregistrés dans
backend/identifiants_demo.txt ; chacun devra être changé à la première connexion.
Le script peut être relancé : ce qui existe déjà n'est pas recréé.
"""
import argparse
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from .config import BACKEND_DIR
from .database import SessionLocal, create_schema
from .importers.mapping import suggest_mapping
from .importers.tabular import file_kind, parse_file
from .kpi.dashboards import create_default_dashboards
from .kpi.references import DOMAINS
from .models import Company, Dataset, Membership, User
from .routers.admin import temporary_password
from .security import hash_password

EXEMPLES = BACKEND_DIR.parent / "exemples"
CREDENTIALS_FILE = BACKEND_DIR / "identifiants_demo.txt"

# Une société fictive par secteur d'activité ; ses fichiers sont dans exemples/<dossier>/.
# (dossier, nom, secteur, taille, effectif, CA annuel en MAD, ville)
COMPANIES = [
    ("atlas_distribution", "Atlas Distribution SARL", "commerce", "pme", 10, 2_460_000, "Casablanca"),
    ("atlas_biscuiterie", "Atlas Biscuiterie SA", "agroalimentaire", "pme", 41, 12_200_000, "Casablanca"),
    ("maroc_metal_industries", "Maroc Métal Industries SA", "industrie", "pme", 75, 20_400_000, "Kénitra"),
    ("tissage_du_nord", "Tissage du Nord SARL", "textile", "pme", 119, 26_600_000, "Tanger"),
    ("batisseurs_du_souss", "Bâtisseurs du Souss SARL", "btp", "pme", 57, 19_700_000, "Agadir"),
    ("conseil_audit_maghreb", "Conseil & Audit Maghreb SARL", "services", "pme", 16, 5_200_000, "Rabat"),
    ("digital_souk_technologies", "Digital Souk Technologies SARL", "tic", "pme", 40, 13_800_000, "Casablanca"),
    ("trans_atlas_logistique", "Trans Atlas Logistique SA", "transport", "pme", 61, 18_700_000, "Tanger"),
    ("hotel_palmeraie_marrakech", "Hôtel Palmeraie Marrakech SARL", "hotellerie_restauration", "pme", 51, 21_600_000,
     "Marrakech"),
    ("pharmacie_al_amal", "Pharmacie Centrale Al Amal", "sante", "tpe", 6, 2_400_000, "Fès"),
    ("domaine_agrumes_berkane", "Domaine Agrumes Berkane SARL", "agriculture", "ge", 211, 29_000_000, "Berkane"),
    ("immo_prestige_casablanca", "Immo Prestige Casablanca SARL", "immobilier", "pme", 14, 12_900_000, "Casablanca"),
]

# Domaine de chaque fichier d'exemple, d'après le début de son nom.
FILE_DOMAINS = [("ventes", "commercial"), ("production", "production"), ("stock", "stock"), ("personnel", "rh"),
                ("tresorerie", "tresorerie"), ("balance", "comptabilite")]
DOMAIN_ORDER = [domain for _, domain in FILE_DOMAINS]


def company_files(folder: str) -> list[tuple[str, Path]]:
    """Fichiers d'exemple d'une société, avec leur domaine, dans l'ordre des tableaux de bord."""
    found = {}
    for path in sorted((EXEMPLES / folder).iterdir()):
        for prefix, domain in FILE_DOMAINS:
            if path.name.startswith(prefix) and domain not in found:
                found[domain] = path
    return [(domain, found[domain]) for domain in DOMAIN_ORDER if domain in found]


USERS = [
    # (nom, e-mail, société, rôle)
    ("Karim Benali", "karim.commercial@visionboard.ma", "Atlas Distribution SARL", "editor"),
    ("Salma Idrissi", "salma.direction@visionboard.ma", "Atlas Biscuiterie SA", "viewer"),
]


def _create_user(db, name: str, email: str, is_admin: bool, credentials: list) -> User:
    password = temporary_password()
    user = User(email=email, full_name=name, password_hash=hash_password(password), is_admin=is_admin,
                must_change_password=True)
    db.add(user)
    db.flush()
    credentials.append((name, email, password, "Administrateur" if is_admin else "Utilisateur"))
    return user


def _import(db, company: Company, owner: User | None, domain: str, path: Path) -> None:
    table = parse_file(path.name, path.read_bytes())
    db.add(Dataset(company_id=company.id, domain=domain, name=path.stem, source_filename=path.name,
                   file_type=file_kind(path.name), row_count=len(table.rows), columns=table.columns,
                   mapping=suggest_mapping(domain, table.columns, table.rows), rows=table.rows,
                   uploaded_by=owner.id if owner else None))
    db.flush()
    print(f"   · {DOMAINS[domain]} : {len(table.rows)} lignes importées")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crée le jeu de démonstration Vision Board")
    parser.add_argument("--admin-email", default="admin@visionboard.ma", help="E-mail du compte administrateur")
    parser.add_argument("--admin-name", default="Administrateur Vision Board")
    parser.add_argument("--donnees-seulement", action="store_true",
                        help="Charge uniquement les sociétés et leurs données, sans créer ni modifier de compte")
    args = parser.parse_args()

    create_schema()
    credentials: list[tuple[str, str, str, str]] = []
    with SessionLocal() as db:
        if args.donnees_seulement:
            # Les sociétés sont visibles par tout administrateur, même sans en être membre.
            admin = db.scalar(select(User).where(User.is_admin).order_by(User.id))
        else:
            admin = db.scalar(select(User).where(User.email == args.admin_email.lower()))
            if admin is None:
                admin = _create_user(db, args.admin_name, args.admin_email.lower(), True, credentials)
            elif not admin.is_admin:
                admin.is_admin = True
                print(f"Le compte {admin.email} est maintenant administrateur.")

        companies = {}
        for folder, name, sector, size, employees, revenue, city in COMPANIES:
            values = {"name": name, "sector": sector, "size": size, "employees": employees,
                      "annual_revenue": revenue, "city": city}
            company = db.scalar(select(Company).where(Company.name == name))
            if company is None:
                print(f"Création de « {name} »")
                company = Company(**values)
                db.add(company)
                db.flush()
            else:
                print(f"Mise à jour de « {name} »")
                for key, value in values.items():
                    setattr(company, key, value)
            if admin is not None and db.get(Membership, (admin.id, company.id)) is None:
                db.add(Membership(user_id=admin.id, company_id=company.id, role="owner"))
            # Complète les domaines manquants : un fichier et un tableau de bord par domaine.
            files = company_files(folder)
            imported = set(db.scalars(select(Dataset.domain).where(Dataset.company_id == company.id)))
            for domain, path in files:
                if domain not in imported:
                    _import(db, company, admin, domain, path)
            for dashboard in create_default_dashboards(db, company, [domain for domain, _ in files]):
                print(f"   · tableau de bord « {dashboard.title} » : {len(dashboard.kpi_codes)} indicateurs")
            companies[name] = company

        for name, email, company_name, role in ([] if args.donnees_seulement else USERS):
            if db.scalar(select(User).where(User.email == email)) is None:
                user = _create_user(db, name, email, False, credentials)
                db.add(Membership(user_id=user.id, company_id=companies[company_name].id, role=role))
        db.commit()

    if args.donnees_seulement:
        print("Données de démonstration chargées (aucun compte créé ni modifié).")
        return
    if not credentials:
        print("\nAucun nouveau compte créé (ils existent déjà). Mot de passe oublié : « Nouveau mot de passe » "
              "dans la page Administration, ou supprimez backend/visionboard.db pour repartir de zéro.")
        return

    lines = [f"Identifiants de démonstration Vision Board — créés le {datetime.now():%d/%m/%Y %H:%M}",
             "Adresse : http://localhost:5173", "Mots de passe provisoires, à changer à la première connexion.", ""]
    for name, email, password, profile in credentials:
        lines += [f"{profile} — {name}", f"  E-mail       : {email}", f"  Mot de passe : {password}", ""]
    with CREDENTIALS_FILE.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n" + "\n".join(lines))
    print(f"Ces identifiants sont aussi enregistrés dans {CREDENTIALS_FILE}")


if __name__ == "__main__":
    main()
