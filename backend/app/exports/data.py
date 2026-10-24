"""Données communes aux exports : indicateurs calculés, graphiques et fichiers sources du tableau de bord."""
import math
from dataclasses import dataclass, field
from datetime import date, datetime

import pandas as pd

from ..kpi.compute import Period, build_frame, filter_period
from ..kpi.fields import fields_for
from ..kpi.references import DOMAINS, SECTORS, SIZES
from ..schemas import DashboardDataOut, KpiValueOut

# Couleurs de l'application (thème clair, voir frontend/src/styles.css)
PALETTE = {
    "bg": "#F4F6FA", "surface": "#FFFFFF", "surface_2": "#EEF1F6", "border": "#DFE4EE",
    "text": "#14213D", "muted": "#5B6478", "primary": "#1B3A6B", "accent": "#B8892B",
    "series": "#2F62B0", "other": "#9AA5B8",
    "ok": "#1D7A3A", "ok_soft": "#E5F5EA", "warn": "#9A6200", "warn_soft": "#FFF4E0",
    "danger": "#B42318", "danger_soft": "#FDECEA",
}

# Couleur principale et secondaire de chaque secteur (voir frontend/src/sectorThemes.ts)
SECTOR_COLORS = {
    "industrie": ("#4B6584", "#F59E0B"), "agroalimentaire": ("#B45309", "#FACC15"),
    "textile": ("#9333EA", "#F472B6"), "btp": ("#C2410C", "#FACC15"), "commerce": ("#2563EB", "#38BDF8"),
    "services": ("#4F46E5", "#A5B4FC"), "tic": ("#0891B2", "#67E8F9"), "transport": ("#0F766E", "#5EEAD4"),
    "hotellerie_restauration": ("#DB2777", "#FDBA74"), "sante": ("#DC2626", "#FCA5A5"),
    "agriculture": ("#15803D", "#BEF264"), "immobilier": ("#334155", "#E2BF62"),
}

STATUS_LABELS = {"ok": "Bon niveau", "warning": "À surveiller", "critical": "Critique"}


@dataclass
class SourceTable:
    """Fichier importé, avec ses colonnes d'origine typées (date, number ou text)."""
    name: str
    source_filename: str
    columns: list[tuple[str, str]]
    rows: list[list]


@dataclass
class ExportData:
    company: str
    sector: str
    sector_label: str
    size_label: str
    city: str | None
    title: str
    domain: str
    domain_label: str
    start: date | None
    end: date | None
    data_start: date | None
    data_end: date | None
    kpis: list[KpiValueOut]
    charts: list[KpiValueOut]  # KPI dont le graphique est affiché (sans doublon)
    tables: list[SourceTable] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    @property
    def colors(self) -> tuple[str, str]:
        return SECTOR_COLORS.get(self.sector, SECTOR_COLORS["commerce"])

    @property
    def period_text(self) -> str:
        start, end = self.start or self.data_start, self.end or self.data_end
        if start and end:
            return f"du {start:%d/%m/%Y} au {end:%d/%m/%Y}"
        return "toute la période"


def _clean(value, type_: str):
    if value is None or (isinstance(value, float) and math.isnan(value)) or value is pd.NaT:
        return None
    if type_ == "date":
        return value.date() if isinstance(value, (pd.Timestamp, datetime)) else value
    if type_ == "number":
        return float(value)
    return str(value)


def _is_number(series: pd.Series) -> bool:
    values = series.dropna()
    return not values.empty and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values)


def source_table(dataset, period: Period) -> SourceTable:
    """Lignes du fichier sur la période, colonnes d'origine conservées, colonnes associées typées."""
    raw = pd.DataFrame(dataset.rows)
    typed = build_frame(dataset.domain, dataset.rows, dataset.mapping)
    kept = filter_period(typed, period).index
    raw, typed = raw.loc[kept], typed.loc[kept]
    types = {f.code: f.type for f in fields_for(dataset.domain)}
    by_column = {column: code for code, column in dataset.mapping.items() if code in typed}

    columns: list[tuple[str, str]] = []
    series: list[pd.Series] = []
    for column in dataset.columns or list(raw.columns):
        if column not in raw:
            continue
        code = by_column.get(column)
        if code:
            columns.append((column, types[code]))
            series.append(typed[code])
        else:
            columns.append((column, "number" if _is_number(raw[column]) else "text"))
            series.append(raw[column])
    rows = [[_clean(s.iloc[i], t) for s, (_, t) in zip(series, columns)] for i in range(len(raw))]
    return SourceTable(dataset.name, dataset.source_filename, columns, rows)


def collect(company, dashboard, data: DashboardDataOut, datasets) -> ExportData:
    # Un même graphique peut servir à deux KPI : on ne le garde qu'une fois, comme à l'écran.
    seen: set[str] = set()
    charts = []
    for k in data.kpis:
        if k.chart and k.chart.values and k.chart.title not in seen:
            seen.add(k.chart.title)
            charts.append(k)
    period = Period(data.start, data.end)
    return ExportData(
        company=company.name, sector=company.sector, sector_label=SECTORS.get(company.sector, company.sector),
        size_label=SIZES.get(company.size, company.size or ""), city=getattr(company, "city", None),
        title=data.title, domain=data.domain, domain_label=DOMAINS.get(data.domain, data.domain),
        start=data.start, end=data.end, data_start=data.data_start, data_end=data.data_end,
        kpis=data.kpis, charts=charts, tables=[source_table(d, period) for d in datasets],
    )
