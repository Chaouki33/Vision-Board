from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, undefer

from ..config import settings
from ..database import get_db
from ..deps import company_access, get_current_user
from ..importers.mapping import suggest_mapping, validate_mapping
from ..importers.tabular import ImportErrorFr, file_kind, parse_file
from ..kpi.references import DOMAINS
from ..models import Company, Dataset, User
from ..schemas import DatasetDetail, DatasetOut, DatasetUpdate

router = APIRouter(prefix="/companies/{company_id}/datasets", tags=["Données importées"])

PREVIEW_ROWS = 20


def _detail(dataset: Dataset, sheets: list[str] | None = None) -> DatasetDetail:
    return DatasetDetail(**DatasetOut.model_validate(dataset).model_dump(),
                         preview=dataset.rows[:PREVIEW_ROWS], sheets=sheets or [])


def _get(db: Session, company: Company, dataset_id: int) -> Dataset:
    dataset = db.scalar(
        select(Dataset).options(undefer(Dataset.rows))
        .where(Dataset.id == dataset_id, Dataset.company_id == company.id)
    )
    if dataset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fichier introuvable")
    return dataset


@router.get("", response_model=list[DatasetOut])
def list_datasets(domain: str | None = None, company: Company = Depends(company_access("viewer")),
                  db: Session = Depends(get_db)):
    query = select(Dataset).where(Dataset.company_id == company.id)
    if domain:
        query = query.where(Dataset.domain == domain)
    return db.scalars(query.order_by(Dataset.created_at.desc())).all()


@router.post("", response_model=DatasetDetail, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    domain: str = Form(...),
    name: str | None = Form(None),
    sheet: str | None = Form(None),
    company: Company = Depends(company_access("editor")),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if domain not in DOMAINS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Domaine inconnu")
    filename = file.filename or "fichier"
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            f"Fichier trop volumineux (maximum {settings.max_upload_mb} Mo)")
    try:
        kind = file_kind(filename)
        table = parse_file(filename, content, sheet)
    except ImportErrorFr as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    if len(table.rows) > settings.max_rows:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Trop de lignes ({len(table.rows)}), maximum {settings.max_rows}")

    dataset = Dataset(
        company_id=company.id,
        domain=domain,
        name=(name or filename.rsplit(".", 1)[0]).strip()[:255],
        source_filename=filename[:255],
        file_type=kind,
        row_count=len(table.rows),
        columns=table.columns,
        mapping=suggest_mapping(domain, table.columns, table.rows),
        rows=table.rows,
        uploaded_by=user.id,
    )
    db.add(dataset)
    db.commit()
    return _detail(dataset, table.sheets)


@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(dataset_id: int, company: Company = Depends(company_access("viewer")), db: Session = Depends(get_db)):
    return _detail(_get(db, company, dataset_id))


@router.patch("/{dataset_id}", response_model=DatasetDetail)
def update_dataset(dataset_id: int, data: DatasetUpdate, company: Company = Depends(company_access("editor")),
                   db: Session = Depends(get_db)):
    dataset = _get(db, company, dataset_id)
    if data.name is not None:
        dataset.name = data.name.strip()
    if data.mapping is not None:
        try:
            dataset.mapping = validate_mapping(dataset.domain, dataset.columns, data.mapping)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    db.commit()
    return _detail(dataset)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dataset(dataset_id: int, company: Company = Depends(company_access("editor")), db: Session = Depends(get_db)):
    db.delete(_get(db, company, dataset_id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
