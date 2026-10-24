"""Forme attendue des données, modèles de fichier et saisie directe dans l'application."""
import datetime as dt

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from ..database import get_db
from ..deps import company_access, get_current_user
from ..importers.tabular import _to_number
from ..kpi.fields import fields_for
from ..kpi.references import DOMAINS
from ..kpi.templates import field_guide, template_csv, template_xlsx
from ..models import Company, Dataset, User

router = APIRouter(tags=["Modèles et saisie"])

MANUAL = "saisie"  # type des jeux de données saisis dans l'application
MAX_MANUAL_ROWS = 5000


def _check_domain(domain: str) -> None:
    if domain not in DOMAINS:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Type de données inconnu")


@router.get("/templates/{domain}")
def guide(domain: str, _: User = Depends(get_current_user)):
    """Colonnes attendues pour ce type de données : format, exemple, indicateurs alimentés."""
    _check_domain(domain)
    return field_guide(domain)


@router.get("/templates/{domain}/download")
def download_template(domain: str, format: str = "xlsx", _: User = Depends(get_current_user)):
    _check_domain(domain)
    if format == "xlsx":
        content = template_xlsx(domain)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif format == "csv":
        content, media = template_csv(domain), "text/csv; charset=utf-8"
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Format inconnu : xlsx ou csv")
    return Response(content, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="modele_{domain}.{format}"'})


# ---------------------------------------------------------------- Saisie dans l'application
class ManualIn(BaseModel):
    domain: str
    name: str = Field(min_length=1, max_length=255)
    # Une ligne par enregistrement : {code du champ standard: valeur saisie}
    rows: list[dict] = Field(max_length=MAX_MANUAL_ROWS)


class ManualRowsIn(BaseModel):
    rows: list[dict] = Field(max_length=MAX_MANUAL_ROWS)


def _parse_date(text: str) -> str | None:
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(text, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return None


def normalize_rows(domain: str, rows: list[dict]) -> tuple[list[str], list[dict], dict[str, str]]:
    """Contrôle et convertit les valeurs saisies. Renvoie (colonnes, lignes, mapping)."""
    fields = fields_for(domain)
    errors, out = [], []
    for index, row in enumerate(rows, 1):
        clean = {}
        for f in fields:
            raw = row.get(f.code)
            text = "" if raw is None else str(raw).strip()
            if not text:
                clean[f.label] = None
            elif f.type == "number":
                value = raw if isinstance(raw, (int, float)) and not isinstance(raw, bool) else _to_number(text)
                if value is None or pd.isna(value):
                    errors.append(f"Ligne {index}, « {f.label} » : nombre attendu (ex. 12 500,50)")
                clean[f.label] = value
            elif f.type == "date":
                value = _parse_date(text)
                if value is None:
                    errors.append(f"Ligne {index}, « {f.label} » : date attendue au format JJ/MM/AAAA")
                clean[f.label] = value
            else:
                clean[f.label] = text
        if any(v is not None for v in clean.values()):
            out.append(clean)
    if errors:
        more = f" (et {len(errors) - 8} autres)" if len(errors) > 8 else ""
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, " · ".join(errors[:8]) + more)
    if not out:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Le tableau est vide : saisissez au moins une ligne")
    # Seules les colonnes renseignées alimentent les indicateurs.
    mapping = {f.code: f.label for f in fields if any(r[f.label] is not None for r in out)}
    return [f.label for f in fields], out, mapping


def _get(db: Session, company: Company, dataset_id: int) -> Dataset:
    dataset = db.scalar(select(Dataset).options(undefer(Dataset.rows))
                        .where(Dataset.id == dataset_id, Dataset.company_id == company.id))
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichier introuvable")
    return dataset


@router.post("/companies/{company_id}/datasets/manual", status_code=status.HTTP_201_CREATED)
def create_manual(data: ManualIn, company: Company = Depends(company_access("editor")),
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_domain(data.domain)
    columns, rows, mapping = normalize_rows(data.domain, data.rows)
    dataset = Dataset(company_id=company.id, domain=data.domain, name=data.name.strip(),
                      source_filename="Saisie dans l'application", file_type=MANUAL, row_count=len(rows),
                      columns=columns, mapping=mapping, rows=rows, uploaded_by=user.id)
    db.add(dataset)
    db.commit()
    return {"id": dataset.id, "row_count": len(rows)}


@router.get("/companies/{company_id}/datasets/{dataset_id}/rows")
def dataset_rows(dataset_id: int, company: Company = Depends(company_access("viewer")), db: Session = Depends(get_db)):
    """Toutes les lignes, exprimées en champs standard (pour la modification d'une saisie)."""
    dataset = _get(db, company, dataset_id)
    by_label = {f.label: f.code for f in fields_for(dataset.domain)}
    rows = [{by_label[label]: value for label, value in row.items() if label in by_label} for row in dataset.rows]
    return {"id": dataset.id, "name": dataset.name, "domain": dataset.domain,
            "editable": dataset.file_type == MANUAL, "rows": rows}


@router.put("/companies/{company_id}/datasets/{dataset_id}/rows")
def update_manual(dataset_id: int, data: ManualRowsIn, company: Company = Depends(company_access("editor")),
                  db: Session = Depends(get_db)):
    dataset = _get(db, company, dataset_id)
    if dataset.file_type != MANUAL:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Seules les données saisies dans l'application sont modifiables ; importez un nouveau fichier")
    columns, rows, mapping = normalize_rows(dataset.domain, data.rows)
    dataset.columns, dataset.rows, dataset.mapping, dataset.row_count = columns, rows, mapping, len(rows)
    db.commit()
    return {"id": dataset.id, "row_count": len(rows)}
