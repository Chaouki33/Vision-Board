"""Calcul des KPI à partir des fichiers importés.

Chaque fichier est converti en DataFrame dont les colonnes sont les champs standard
(via le mapping), avec des types propres : dates, nombres, textes. Chaque KPI calculé
renvoie une valeur, un statut d'alerte et, le cas échéant, une série pour un graphique.
"""
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd

from .calc import commercial, comptabilite, production, rh, stock, tresorerie
from .calc.common import Calculator, Chart
from .catalog import KPI, KPI_BY_CODE
from .fields import fields_for


@dataclass
class KpiResult:
    code: str
    value: float | None
    status: str | None = None  # "ok", "warning", "critical"
    detail: str | None = None
    delta: float | None = None  # variation en % par rapport au mois précédent
    chart: Chart | None = None
    error: str | None = None
    rows: int = 0


@dataclass
class Period:
    start: date | None = None
    end: date | None = None


# ---------------------------------------------------------------- Préparation des données
def _to_number(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _to_date(series: pd.Series) -> pd.Series:
    values = series.astype("string")
    iso = values.str.match(r"^\d{4}-\d{2}-\d{2}", na=False)
    parsed = pd.to_datetime(values.where(iso), errors="coerce", format="ISO8601")
    other = pd.to_datetime(values.where(~iso), errors="coerce", dayfirst=True, format="mixed")
    result = parsed.fillna(other)
    return result.dt.tz_localize(None) if result.dt.tz is not None else result


def build_frame(domain: str, rows: list[dict], mapping: dict[str, str]) -> pd.DataFrame:
    """Renomme les colonnes selon le mapping et applique les types des champs standard."""
    raw = pd.DataFrame(rows)
    frame = pd.DataFrame(index=raw.index)
    for f in fields_for(domain):
        column = mapping.get(f.code)
        if column is None or column not in raw:
            continue
        if f.type == "number":
            frame[f.code] = _to_number(raw[column])
        elif f.type == "date":
            frame[f.code] = _to_date(raw[column])
        else:
            frame[f.code] = raw[column].map(lambda v: None if v is None or pd.isna(v) else str(v).strip())
    return frame


def filter_period(df: pd.DataFrame, period: Period) -> pd.DataFrame:
    if "date" not in df or (period.start is None and period.end is None):
        return df
    if period.start:
        df = df[df["date"].ge(pd.Timestamp(period.start))]
    if period.end:
        df = df[df["date"].lt(pd.Timestamp(period.end + timedelta(days=1)))]
    return df


# ---------------------------------------------------------------- Calcul
def _status(kpi: KPI, value: float | None) -> str | None:
    if value is None or kpi.higher_is_better is None or (kpi.warning is None and kpi.critical is None):
        return None
    if kpi.higher_is_better:
        if kpi.critical is not None and value < kpi.critical:
            return "critical"
        if kpi.warning is not None and value < kpi.warning:
            return "warning"
    else:
        if kpi.critical is not None and value > kpi.critical:
            return "critical"
        if kpi.warning is not None and value > kpi.warning:
            return "warning"
    return "ok"


CALCULATORS: dict[str, Calculator] = {
    **commercial.CALCULATORS,
    **production.CALCULATORS,
    **stock.CALCULATORS,
    **rh.CALCULATORS,
    **tresorerie.CALCULATORS,
    **comptabilite.CALCULATORS,
}


def compute_kpi(code: str, df: pd.DataFrame) -> KpiResult:
    kpi = KPI_BY_CODE[code]
    calculator = CALCULATORS.get(code)
    if calculator is None:
        return KpiResult(code, None, error="Calcul disponible dans une prochaine version")
    missing = [f for f in kpi.required if f not in df]
    if missing:
        return KpiResult(code, None, error="Données manquantes")
    data = df.dropna(subset=list(kpi.required), how="all")
    if data.empty:
        return KpiResult(code, None, error="Aucune donnée sur la période")
    try:
        value, extra = calculator(data)
    except (ValueError, ZeroDivisionError, KeyError) as exc:
        return KpiResult(code, None, error=str(exc), rows=len(data))
    if value is not None:
        value = round(float(value), 2)
    return KpiResult(code, value, status=_status(kpi, value), rows=len(data), detail=extra.get("detail"),
                     delta=extra.get("delta"), chart=extra.get("chart"))


def is_computable(code: str) -> bool:
    return code in CALCULATORS
