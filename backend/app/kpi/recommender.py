"""Moteur de recommandation des KPI.

Il combine le secteur et la taille de la société, le domaine de tableau de bord choisi
par l'utilisateur et les données réellement importées pour proposer une sélection de KPI.
"""
from dataclasses import dataclass, field

from .catalog import KPIS, KPI
from .references import SECTOR_DOMAINS

# Nombre de KPI proposés par défaut selon la taille : une TPE a besoin de l'essentiel,
# une grande entreprise d'un suivi plus détaillé.
MAX_SELECTED = {"tpe": 8, "pme": 14, "ge": 25}
MAX_PRIORITY = {"tpe": 2, "pme": 3, "ge": 3}


@dataclass
class Recommendation:
    kpi: KPI
    priority: int
    available: bool
    missing_fields: list[str]
    dataset_id: int | None
    selected: bool = False
    reasons: list[str] = field(default_factory=list)


def best_dataset(kpi: KPI, datasets_fields: dict[int, set[str]]) -> tuple[int | None, list[str]]:
    """Retourne le fichier qui couvre le mieux les champs nécessaires au KPI."""
    best_id, best_missing = None, list(kpi.required)
    for dataset_id, fields in datasets_fields.items():
        missing = [f for f in kpi.required if f not in fields]
        if len(missing) < len(best_missing):
            best_id, best_missing = dataset_id, missing
    return (best_id if not best_missing else None), best_missing


def recommend(domain: str, sector: str, size: str, datasets_fields: dict[int, set[str]]) -> list[Recommendation]:
    """`datasets_fields` : pour chaque fichier importé du domaine, les champs standard reconnus."""
    candidates = [k for k in KPIS if k.domain == domain and k.applies_to(sector, size)]
    recs: list[Recommendation] = []
    for kpi in candidates:
        dataset_id, missing = best_dataset(kpi, datasets_fields)
        priority = kpi.priority_for(sector)
        reasons = []
        if sector in kpi.boost:
            reasons.append("Indicateur clé pour votre secteur")
        elif priority == 1:
            reasons.append("Indicateur essentiel du domaine")
        if kpi.sizes != ("tpe", "pme", "ge"):
            reasons.append("Adapté à la taille de votre entreprise")
        recs.append(Recommendation(kpi, priority, not missing, missing, dataset_id, reasons=reasons))

    # Les KPI calculables passent devant, puis par priorité.
    recs.sort(key=lambda r: (r.priority, not r.available))

    selected = 0
    for rec in recs:
        if rec.priority <= MAX_PRIORITY[size] and selected < MAX_SELECTED[size]:
            rec.selected = True
            selected += 1
    return recs


def suggested_domains(sector: str) -> list[str]:
    return SECTOR_DOMAINS.get(sector, [])
