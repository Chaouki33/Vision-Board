import re
import unicodedata
from dataclasses import asdict
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from ..database import get_db
from ..exports.data import collect
from ..exports.excel import to_xlsx
from ..exports.powerbi import to_powerbi
from ..deps import company_access
from ..kpi.accounting import analyse, statements
from ..kpi.catalog import KPI, KPI_BY_CODE, KPIS
from ..kpi.compute import KpiResult, Period, build_frame, compute_kpi, filter_period
from ..kpi.fields import DOMAIN_FIELDS
from ..kpi.recommender import best_dataset, recommend, suggested_domains
from ..kpi.dashboards import create_default_dashboards
from ..kpi.references import DOMAINS, SECTOR_DOMAINS, SECTORS, SIZES
from ..models import Company, Dashboard, Dataset
from ..schemas import (ChartOut, DashboardBulkIn, DashboardDataOut, DashboardIn, DashboardOut, KpiOut, KpiValueOut,
                       RecommendationOut, RecommendationsOut)

router = APIRouter(tags=["KPI et tableaux de bord"])


def _kpi_dict(kpi: KPI, priority: int | None = None) -> dict:
    return {
        "code": kpi.code, "domain": kpi.domain, "name": kpi.name, "description": kpi.description,
        "formula": kpi.formula, "unit": kpi.unit, "required": list(kpi.required),
        "priority": priority or kpi.priority, "higher_is_better": kpi.higher_is_better,
        "warning": kpi.warning, "critical": kpi.critical,
    }


@router.get("/meta")
def meta():
    """Référentiels utilisés par l'interface : secteurs, tailles, domaines et champs standard."""
    return {
        "sectors": SECTORS,
        "sizes": SIZES,
        "domains": DOMAINS,
        "sector_domains": SECTOR_DOMAINS,
        "fields": {d: [{"code": f.code, "label": f.label, "type": f.type} for f in fs]
                   for d, fs in DOMAIN_FIELDS.items()},
    }


@router.get("/kpis", response_model=list[KpiOut])
def catalog(domain: str | None = None):
    return [_kpi_dict(k) for k in KPIS if domain is None or k.domain == domain]


@router.get("/companies/{company_id}/recommendations", response_model=RecommendationsOut)
def recommendations(domain: str, company: Company = Depends(company_access("viewer")), db: Session = Depends(get_db)):
    if domain not in DOMAINS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Domaine inconnu")
    datasets = db.execute(
        select(Dataset.id, Dataset.mapping).where(Dataset.company_id == company.id, Dataset.domain == domain)
    ).all()
    datasets_fields = {dataset_id: set(mapping) for dataset_id, mapping in datasets}
    recs = recommend(domain, company.sector, company.size, datasets_fields)
    return RecommendationsOut(
        domain=domain,
        sector=company.sector,
        size=company.size,
        suggested_domains=suggested_domains(company.sector),
        datasets=len(datasets),
        kpis=[RecommendationOut(**_kpi_dict(r.kpi, r.priority), available=r.available,
                                missing_fields=r.missing_fields, dataset_id=r.dataset_id,
                                selected=r.selected, reasons=r.reasons) for r in recs],
    )


# ---------------------------------------------------------------- Tableaux de bord enregistrés
def _check_codes(data: DashboardIn) -> None:
    for code in data.kpi_codes:
        kpi = KPI_BY_CODE.get(code)
        if kpi is None or kpi.domain != data.domain:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"KPI invalide pour ce domaine : {code}")


def _get_dashboard(db: Session, company: Company, dashboard_id: int) -> Dashboard:
    dashboard = db.get(Dashboard, dashboard_id)
    if dashboard is None or dashboard.company_id != company.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tableau de bord introuvable")
    return dashboard


@router.get("/companies/{company_id}/dashboards", response_model=list[DashboardOut])
def list_dashboards(company: Company = Depends(company_access("viewer")), db: Session = Depends(get_db)):
    return db.scalars(select(Dashboard).where(Dashboard.company_id == company.id).order_by(Dashboard.title)).all()


@router.post("/companies/{company_id}/dashboards", response_model=DashboardOut, status_code=status.HTTP_201_CREATED)
def create_dashboard(data: DashboardIn, company: Company = Depends(company_access("editor")),
                     db: Session = Depends(get_db)):
    _check_codes(data)
    dashboard = Dashboard(company_id=company.id, **data.model_dump())
    db.add(dashboard)
    db.commit()
    return dashboard


@router.post("/companies/{company_id}/dashboards/bulk", response_model=list[DashboardOut],
             status_code=status.HTTP_201_CREATED)
def create_dashboards_bulk(data: DashboardBulkIn, company: Company = Depends(company_access("editor")),
                           db: Session = Depends(get_db)):
    """Crée en une fois plusieurs tableaux de bord, avec les KPI recommandés (domaines déjà présents ignorés)."""
    created = create_default_dashboards(db, company, data.domains)
    db.commit()
    return created


@router.put("/companies/{company_id}/dashboards/{dashboard_id}", response_model=DashboardOut)
def update_dashboard(dashboard_id: int, data: DashboardIn, company: Company = Depends(company_access("editor")),
                     db: Session = Depends(get_db)):
    _check_codes(data)
    dashboard = _get_dashboard(db, company, dashboard_id)
    for key, value in data.model_dump().items():
        setattr(dashboard, key, value)
    db.commit()
    return dashboard


@router.get("/companies/{company_id}/dashboards/{dashboard_id}/data", response_model=DashboardDataOut)
def dashboard_data(dashboard_id: int, start: date | None = None, end: date | None = None,
                   company: Company = Depends(company_access("viewer")), db: Session = Depends(get_db)):
    """Calcule les KPI du tableau de bord sur la période demandée (toutes les données par défaut)."""
    return compute_dashboard(db, company, _get_dashboard(db, company, dashboard_id), start, end)


def compute_dashboard(db: Session, company: Company, dashboard: Dashboard,
                      start: date | None = None, end: date | None = None) -> DashboardDataOut:
    datasets = db.scalars(
        select(Dataset).options(undefer(Dataset.rows))
        .where(Dataset.company_id == company.id, Dataset.domain == dashboard.domain)
    ).all()
    frames = {d.id: build_frame(d.domain, d.rows, d.mapping) for d in datasets}
    fields = {dataset_id: set(df.columns) for dataset_id, df in frames.items()}

    # Bornes des données disponibles, pour proposer la période à l'utilisateur.
    dates = [df["date"].dropna() for df in frames.values() if "date" in df]
    dates = [d for d in dates if not d.empty]
    data_start = min(d.min() for d in dates).date() if dates else None
    data_end = max(d.max() for d in dates).date() if dates else None

    period = Period(start, end)
    results = []
    for code in dashboard.kpi_codes:
        kpi = KPI_BY_CODE.get(code)
        if kpi is None:
            continue
        dataset_id, _ = best_dataset(kpi, fields)
        if dataset_id is None:
            result = KpiResult(code, None, error="Données manquantes")
        else:
            result = compute_kpi(code, filter_period(frames[dataset_id], period))
        results.append(KpiValueOut(
            code=code, name=kpi.name, description=kpi.description, formula=kpi.formula, unit=kpi.unit,
            higher_is_better=kpi.higher_is_better, value=result.value, status=result.status,
            detail=result.detail, delta=result.delta, error=result.error, rows=result.rows,
            chart=ChartOut(**asdict(result.chart)) if result.chart else None,
        ))
    return DashboardDataOut(id=dashboard.id, title=dashboard.title, domain=dashboard.domain, start=start, end=end,
                            data_start=data_start, data_end=data_end, kpis=results)


EXPORTS = {
    "xlsx": (to_xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"),
    "powerbi": (to_powerbi, "application/zip", "zip"),
}


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", ascii_text).strip("_")[:60] or "tableau_de_bord"


@router.get("/companies/{company_id}/dashboards/{dashboard_id}/export")
def export_dashboard(dashboard_id: int, format: str = "xlsx", start: date | None = None, end: date | None = None,
                     company: Company = Depends(company_access("viewer")), db: Session = Depends(get_db)):
    """Tableau de bord et données sources, en classeur Excel (xlsx) ou en projet Power BI (powerbi)."""
    if format not in EXPORTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Format inconnu : xlsx ou powerbi")
    dashboard = _get_dashboard(db, company, dashboard_id)
    data = compute_dashboard(db, company, dashboard, start, end)
    datasets = db.scalars(
        select(Dataset).options(undefer(Dataset.rows))
        .where(Dataset.company_id == company.id, Dataset.domain == dashboard.domain).order_by(Dataset.id)
    ).all()
    render, media_type, extension = EXPORTS[format]
    payload = render(collect(company, dashboard, data, datasets))
    filename = f"{_slug(company.name)}_{_slug(dashboard.title)}"
    if format == "powerbi":
        filename += "_PowerBI"
    return Response(payload, media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="{filename}.{extension}"'})


@router.get("/companies/{company_id}/accounting")
def accounting_statements(dataset_id: int | None = None, start: date | None = None, end: date | None = None,
                          company: Company = Depends(company_access("viewer")), db: Session = Depends(get_db)):
    """Balance, CPC, soldes de gestion, bilan et ratios du dernier fichier comptable importé."""
    return load_statements(db, company, dataset_id, start, end)


def load_statements(db: Session, company: Company, dataset_id: int | None = None,
                    start: date | None = None, end: date | None = None) -> dict:
    query = select(Dataset).options(undefer(Dataset.rows)).where(
        Dataset.company_id == company.id, Dataset.domain == "comptabilite")
    if dataset_id is not None:
        query = query.where(Dataset.id == dataset_id)
    dataset = db.scalars(query.order_by(Dataset.created_at.desc(), Dataset.id.desc())).first()
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucune balance ou grand livre importé pour cette société")
    df = build_frame("comptabilite", dataset.rows, dataset.mapping)
    missing = [f for f in ("compte", "debit", "credit") if f not in df]
    if missing:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Associez les colonnes Compte, Débit et Crédit du fichier dans « Données importées »")
    result = statements(analyse(filter_period(df, Period(start, end))))
    return {"dataset": {"id": dataset.id, "name": dataset.name, "source_filename": dataset.source_filename}, **result}


@router.delete("/companies/{company_id}/dashboards/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard(dashboard_id: int, company: Company = Depends(company_access("editor")),
                     db: Session = Depends(get_db)):
    db.delete(_get_dashboard(db, company, dashboard_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
