import re
import unicodedata
from datetime import date, datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from ..database import SessionLocal, get_db
from ..deps import company_access, get_current_user
from ..models import Company, Dashboard, Report, User
from ..reports import writer
from ..reports.context import build_context
from ..reports.export import to_docx, to_pdf
from ..reports.rules import ENGINE_NAME, write_rules_report

router = APIRouter(prefix="/companies/{company_id}", tags=["Rapports d'analyse"])


class ReportIn(BaseModel):
    start: date | None = None
    end: date | None = None
    instructions: str | None = Field(default=None, max_length=2000)


class ReportOut(BaseModel):
    id: int
    dashboard_id: int | None
    domain: str
    title: str
    status: str
    period_start: date | None
    period_end: date | None
    instructions: str | None
    content: dict | None
    error: str | None
    model: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


def _get_report(db: Session, company: Company, report_id: int, with_context: bool = False) -> Report:
    query = select(Report).where(Report.id == report_id, Report.company_id == company.id)
    if with_context:
        query = query.options(undefer(Report.context))
    report = db.scalar(query)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rapport introuvable")
    return report


def write_report(report_id: int) -> None:
    """Tâche de fond : appel à l'IA puis enregistrement du résultat."""
    with SessionLocal() as db:
        report = db.scalar(select(Report).options(undefer(Report.context)).where(Report.id == report_id))
        if report is None:
            return
        try:
            result = writer.call_claude(report.context, report.instructions)
            report.content = result.content
            report.title = result.content.get("titre") or report.title
            report.model = result.model
            report.input_tokens, report.output_tokens = result.input_tokens, result.output_tokens
            report.status = "done"
        except writer.ReportError as exc:
            report.status, report.error = "error", str(exc)
        except Exception as exc:  # noqa: BLE001 - le rapport ne doit jamais rester « en cours »
            report.status, report.error = "error", f"Erreur inattendue lors de la rédaction : {exc}"
        report.completed_at = datetime.now(timezone.utc)
        db.commit()


@router.post("/dashboards/{dashboard_id}/reports", response_model=ReportOut, status_code=status.HTTP_202_ACCEPTED)
def create_report(dashboard_id: int, data: ReportIn, background: BackgroundTasks,
                  company: Company = Depends(company_access("editor")), user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    dashboard = db.get(Dashboard, dashboard_id)
    if dashboard is None or dashboard.company_id != company.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tableau de bord introuvable")
    context, computed = build_context(db, company, dashboard, data.start, data.end)
    report = Report(
        company_id=company.id, dashboard_id=dashboard.id, domain=dashboard.domain,
        title=f"Analyse — {dashboard.title}", period_start=data.start, period_end=data.end,
        instructions=(data.instructions or "").strip() or None, context=context, created_by=user.id,
    )
    if writer.report_engine() == "regles":
        # Analyse gratuite par règles : instantanée, pas besoin de tâche de fond.
        report.content = write_rules_report(company.name, computed, _period_text(context["periode"]))
        report.title = report.content["titre"]
        report.model = ENGINE_NAME
        report.status = "done"
        report.completed_at = datetime.now(timezone.utc)
        db.add(report)
        db.commit()
        return report
    db.add(report)
    db.commit()
    background.add_task(write_report, report.id)
    return report


def _period_text(period: dict) -> str:
    fr = lambda d: date.fromisoformat(d).strftime("%d/%m/%Y")  # noqa: E731
    if period.get("debut") and period.get("fin"):
        return f"sur la période du {fr(period['debut'])} au {fr(period['fin'])}"
    return "sur l'ensemble des données disponibles"


@router.get("/reports-config")
def reports_config(_: Company = Depends(company_access("viewer"))):
    """Moteur utilisé pour les rapports de cette installation (affiché dans l'interface)."""
    engine = writer.report_engine()
    return {"engine": engine, "label": "Rédaction par l'IA Claude" if engine == "claude" else "Analyse automatique gratuite"}


@router.get("/reports", response_model=list[ReportOut])
def list_reports(company: Company = Depends(company_access("viewer")), db: Session = Depends(get_db)):
    return db.scalars(select(Report).where(Report.company_id == company.id).order_by(Report.created_at.desc())).all()


@router.get("/reports/{report_id}", response_model=ReportOut)
def get_report(report_id: int, company: Company = Depends(company_access("viewer")), db: Session = Depends(get_db)):
    return _get_report(db, company, report_id)


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: int, company: Company = Depends(company_access("editor")), db: Session = Depends(get_db)):
    db.delete(_get_report(db, company, report_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _filename(title: str, extension: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "_", ascii_title).strip("_")[:80] or "rapport"
    return f"{slug}.{extension}"


EXPORTS = {
    "pdf": (to_pdf, "application/pdf"),
    "docx": (to_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
}


@router.get("/reports/{report_id}/export")
def export_report(report_id: int, format: str = "pdf", company: Company = Depends(company_access("viewer")),
                  db: Session = Depends(get_db)):
    if format not in EXPORTS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Format inconnu : pdf ou docx")
    report = _get_report(db, company, report_id, with_context=True)
    if report.status != "done" or not report.content:
        raise HTTPException(status.HTTP_409_CONFLICT, "Le rapport n'est pas encore rédigé")
    render, media_type = EXPORTS[format]
    payload = render({"content": report.content, "context": report.context, "model": report.model,
                      "created_at": report.created_at})
    return Response(payload, media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="{_filename(report.title, format)}"'})
