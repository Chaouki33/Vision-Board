"""Données transmises à l'IA pour rédiger un rapport.

Uniquement des chiffres déjà calculés par l'application : l'IA interprète, elle ne calcule pas.
Le contexte est conservé avec le rapport pour pouvoir retracer ce qui a été analysé.
"""
from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..kpi.catalog import KPI_BY_CODE
from ..kpi.references import DOMAINS, SECTORS, SIZES
from ..models import Company, Dashboard
from ..routers.kpis import compute_dashboard, load_statements
from ..schemas import DashboardDataOut
from .formatting import STATUS_LABELS, fmt_delta, fmt_value

# Au-delà, les séries sont résumées pour garder un contexte lisible.
MAX_SERIES_POINTS = 24


def _threshold(code: str) -> str | None:
    kpi = KPI_BY_CODE[code]
    if kpi.higher_is_better is None or (kpi.warning is None and kpi.critical is None):
        return None
    sens = "au-dessus de" if kpi.higher_is_better else "en dessous de"
    parts = []
    if kpi.warning is not None:
        parts.append(f"bon niveau {sens} {fmt_value(kpi.warning, kpi.unit)}")
    if kpi.critical is not None and kpi.critical != kpi.warning:
        parts.append(f"critique {'en dessous de' if kpi.higher_is_better else 'au-dessus de'} {fmt_value(kpi.critical, kpi.unit)}")
    return " ; ".join(parts)


def build_context(db: Session, company: Company, dashboard: Dashboard,
                  start: date | None, end: date | None) -> tuple[dict, DashboardDataOut]:
    data = compute_dashboard(db, company, dashboard, start, end)
    indicators, missing = [], []
    for k in data.kpis:
        if k.error:
            missing.append({"indicateur": k.name, "raison": k.error})
            continue
        item = {
            "indicateur": k.name,
            "valeur": fmt_value(k.value, k.unit),
            "definition": k.description,
            "formule": k.formula,
        }
        if k.status:
            item["statut"] = STATUS_LABELS[k.status]
        if (threshold := _threshold(k.code)):
            item["seuils"] = threshold
        if k.delta is not None:
            item["variation"] = fmt_delta(k.delta)
        if k.detail:
            item["precision"] = k.detail
        if k.chart and k.chart.values:
            pairs = list(zip(k.chart.labels, k.chart.values))[-MAX_SERIES_POINTS:]
            item["detail_graphique"] = {
                "titre": k.chart.title,
                "type": "évolution mensuelle" if k.chart.type == "line" else "répartition",
                "valeurs": {label: fmt_value(v, k.chart.unit) for label, v in pairs},
            }
        indicators.append(item)

    if not indicators:
        raise HTTPException(422, "Aucun indicateur n'a pu être calculé : importez d'abord les données de ce tableau de bord")

    context = {
        "societe": {
            "nom": company.name,
            "secteur": SECTORS.get(company.sector, company.sector),
            "taille": SIZES.get(company.size, company.size),
            "effectif": company.employees,
            "chiffre_affaires_annuel_declare": fmt_value(company.annual_revenue, "MAD") if company.annual_revenue else None,
            "ville": company.city,
        },
        "tableau_de_bord": {"titre": data.title, "domaine": DOMAINS[data.domain]},
        "periode": {
            "debut": (start or data.data_start).isoformat() if (start or data.data_start) else None,
            "fin": (end or data.data_end).isoformat() if (end or data.data_end) else None,
        },
        "indicateurs": indicators,
        "indicateurs_non_calcules": missing,
    }
    if data.domain == "comptabilite":
        context["etats_financiers"] = _financial_summary(db, company, start, end)
    return context, data


def _financial_summary(db: Session, company: Company, start: date | None, end: date | None) -> dict | None:
    try:
        s = load_statements(db, company, None, start, end)
    except HTTPException:
        return None
    rows = lambda items: {r["label"]: fmt_value(r["value"], "MAD") for r in items if r.get("value") is not None}  # noqa: E731
    return {
        "cpc": rows(r for r in s["cpc"] if r["type"] != "header"),
        "soldes_de_gestion": rows(s["esg"]),
        "bilan_actif": {r["label"]: fmt_value(r["net"], "MAD") for r in s["bilan"]["actif"] if r["type"] in ("total", "final")},
        "bilan_passif": {r["label"]: fmt_value(r["value"], "MAD") for r in s["bilan"]["passif"] if r["type"] in ("total", "final")},
        "ratios": {r["label"]: fmt_value(r["value"], r["unit"]) for r in s["ratios"] if r["value"] is not None},
        "controles": s["checks"],
    }
