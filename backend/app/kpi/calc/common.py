"""Outils partagés par les calculs de KPI de tous les domaines."""
from dataclasses import dataclass
from datetime import date
from typing import Callable

import pandas as pd

MONTHS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

# Un calculateur reçoit les données du domaine (champs standard) et renvoie
# (valeur, extras) ; les extras possibles sont "detail", "delta" et "chart".
Calculator = Callable[[pd.DataFrame], tuple[float | None, dict]]


@dataclass
class Chart:
    type: str  # "line" (évolution dans le temps) ou "bar" (classement)
    title: str
    labels: list[str]
    values: list[float]
    unit: str


def today() -> pd.Timestamp:
    """Date de référence des calculs (remplaçable dans les tests)."""
    return pd.Timestamp(date.today())


def month_label(p: pd.Period) -> str:
    return f"{MONTHS_FR[p.month - 1]} {p.year}"


def monthly(df: pd.DataFrame, column: str, how: str = "sum", date_col: str = "date") -> pd.Series:
    """Agrégat mensuel, sans trou entre le premier et le dernier mois."""
    data = df.dropna(subset=[date_col])
    if data.empty:
        return pd.Series(dtype=float)
    grouped = data.groupby(data[date_col].dt.to_period("M"))[column]
    series = {"sum": grouped.sum, "nunique": grouped.nunique, "mean": grouped.mean, "last": grouped.last}[how]()
    full = pd.period_range(series.index.min(), series.index.max(), freq="M")
    return series.reindex(full, fill_value=0)


def line(title: str, series: pd.Series, unit: str) -> Chart:
    return Chart("line", title, [month_label(p) for p in series.index], [round(float(v), 2) for v in series.values], unit)


def bar(title: str, series: pd.Series, unit: str, top: int = 10, fold: bool = True, sort: bool = True) -> Chart:
    """Classement décroissant ; au-delà de `top`, le reste est regroupé dans « Autres »
    (sauf pour des moyennes ou des taux, où une somme n'aurait pas de sens).
    `sort=False` garde l'ordre donné (soldes de gestion, structure du bilan)."""
    series = series.dropna()
    if sort:
        series = series.sort_values(ascending=False)
    if len(series) > top:
        rest = series.iloc[top:]
        series = series.iloc[:top]
        if fold:
            series = pd.concat([series, pd.Series({"Autres": rest.sum()})])
    return Chart("bar", title, [str(k) for k in series.index], [round(float(v), 2) for v in series.values], unit)


def pct(part: float, total: float) -> float | None:
    return round(100 * part / total, 2) if total else None


def evolution(series: pd.Series) -> float | None:
    """Variation du dernier mois par rapport au précédent."""
    if len(series) < 2 or not series.iloc[-2]:
        return None
    return round(100 * (series.iloc[-1] - series.iloc[-2]) / abs(series.iloc[-2]), 2)


def has_dates(df: pd.DataFrame, column: str = "date") -> bool:
    return column in df and df[column].notna().any()


def share_of_top(series: pd.Series, label: str) -> tuple[float | None, str | None]:
    """Part du premier élément d'une répartition, et texte de détail associé."""
    if series.empty or not series.sum():
        return None, None
    best = series.idxmax()
    return pct(series.max(), series.sum()), f"{label} : {best}"
