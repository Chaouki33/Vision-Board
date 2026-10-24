"""Création automatique de tableaux de bord avec les KPI recommandés."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Company, Dashboard, Dataset
from .recommender import recommend
from .references import DOMAINS

DEFAULT_TITLES = {
    "commercial": "Pilotage commercial",
    "production": "Suivi de production",
    "stock": "Gestion des stocks",
    "rh": "Ressources humaines",
    "tresorerie": "Trésorerie",
    "comptabilite": "Analyse financière",
}


def create_default_dashboards(db: Session, company: Company, domains: list[str]) -> list[Dashboard]:
    """Crée un tableau de bord par domaine demandé, sauf s'il en existe déjà un pour ce domaine.
    Les KPI retenus sont ceux recommandés pour le secteur, la taille et les données déjà importées."""
    existing = set(db.scalars(select(Dashboard.domain).where(Dashboard.company_id == company.id)))
    created = []
    for domain in dict.fromkeys(domains):  # sans doublons, dans l'ordre demandé
        if domain not in DOMAINS or domain in existing:
            continue
        datasets = db.execute(
            select(Dataset.id, Dataset.mapping).where(Dataset.company_id == company.id, Dataset.domain == domain)
        ).all()
        recs = recommend(domain, company.sector, company.size, {i: set(m) for i, m in datasets})
        codes = [r.kpi.code for r in recs if r.selected]
        if not codes:
            continue  # aucun KPI de ce domaine ne concerne le secteur (ex. production pour un cabinet)
        dashboard = Dashboard(company_id=company.id, domain=domain, title=DEFAULT_TITLES[domain], kpi_codes=codes)
        db.add(dashboard)
        created.append(dashboard)
    db.flush()
    return created
