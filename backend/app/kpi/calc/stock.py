"""KPI du tableau de bord stock.

Le fichier est un état de stock (une ligne par article) ou une suite d'inventaires datés :
dans ce cas, les niveaux de stock retenus sont ceux du dernier inventaire de chaque article,
tandis que les sorties sont cumulées sur toute la période.
"""
from datetime import timedelta

import pandas as pd

from .common import Calculator, bar, has_dates, line, pct, share_of_top, today

PEREMPTION_DAYS = 30


def latest(df: pd.DataFrame) -> pd.DataFrame:
    """Dernier état connu de chaque article."""
    if not has_dates(df):
        return df
    df = df.sort_values("date", na_position="first")
    if "article" in df:
        return df.drop_duplicates("article", keep="last")
    return df[df["date"] == df["date"].max()]


def _values(df: pd.DataFrame) -> pd.Series:
    return df["quantite_stock"].fillna(0) * df["cout_unitaire"].fillna(0)


def _valeur_stock(df):
    current = latest(df)
    extras = {}
    if "article" in current:
        extras["chart"] = bar("Valeur du stock par article", _values(current).groupby(current["article"]).sum(), "MAD")
    if has_dates(df) and df["date"].nunique() > 1:
        # Plusieurs inventaires : évolution de la valeur totale (dernier inventaire de chaque mois).
        totals = df.assign(valeur=_values(df)).groupby("date")["valeur"].sum()
        by_month = totals.groupby(totals.index.to_period("M")).last()
        extras["chart"] = line("Valeur du stock par mois", by_month, "MAD")
    return float(_values(current).sum()), extras


def _nb_articles(df):
    return float(df["article"].nunique()), {}


def _articles_sous_seuil(df):
    current = latest(df).dropna(subset=["quantite_stock", "stock_minimum"])
    below = current[current["quantite_stock"] <= current["stock_minimum"]]
    gap = (below["stock_minimum"] - below["quantite_stock"]).groupby(below["article"]).sum()
    return float(len(below)), {
        "detail": f"{pct(len(below), len(current)) or 0:.0f} % des articles à réapprovisionner".replace(".", ","),
        "chart": bar("Quantités manquantes pour atteindre le seuil", gap, "nombre", fold=False) if len(gap) else None,
    }


def _taux_rupture(df):
    current = latest(df).dropna(subset=["quantite_stock"])
    out = current["quantite_stock"] <= 0
    return pct(out.sum(), len(current)), {"detail": f"{int(out.sum())} articles en rupture sur {len(current)}"}


def _average_stock(df: pd.DataFrame) -> float:
    if has_dates(df) and df["date"].nunique() > 1:
        return float(df.groupby("date")["quantite_stock"].sum().mean())
    return float(latest(df)["quantite_stock"].sum())


def _rotation_stock(df):
    average = _average_stock(df)
    if not average:
        return None, {}
    return round(df["sorties"].sum() / average, 2), {"detail": "Sorties de la période / stock moyen"}


def _couverture_stock(df):
    outflow = df["sorties"].sum()
    stock = latest(df)["quantite_stock"].sum()
    dates = df["date"].dropna()
    days = (dates.max() - dates.min()).days + 1 if dates.nunique() > 1 else 30
    detail = None if dates.nunique() > 1 else "Sorties considérées comme mensuelles (un seul inventaire)"
    if not outflow:
        return None, {"detail": "Aucune sortie enregistrée"}
    return round(stock / (outflow / days), 1), {"detail": detail}


def _stock_dormant(df):
    current = latest(df).set_index("article")["quantite_stock"]
    outflow = df.groupby("article")["sorties"].sum()
    dormant = current[(current > 0) & (outflow.reindex(current.index).fillna(0) == 0)]
    return float(len(dormant)), {"detail": f"{pct(len(dormant), len(current)) or 0:.0f} % des articles".replace(".", ",")}


def _repartition(column: str, title: str, label: str):
    def calculator(df):
        current = latest(df)
        series = _values(current).groupby(current[column]).sum()
        value, detail = share_of_top(series, label)
        return value, {"detail": detail, "chart": bar(title, series, "MAD")}
    return calculator


def _proches_peremption(df):
    current = latest(df).dropna(subset=["date_peremption"])
    if "quantite_stock" in current:
        current = current[current["quantite_stock"].fillna(1) > 0]
    limit = today() + timedelta(days=PEREMPTION_DAYS)
    expired = current["date_peremption"] < today()
    soon = (current["date_peremption"] >= today()) & (current["date_peremption"] <= limit)
    return float(soon.sum()), {"detail": f"{int(expired.sum())} articles déjà périmés"}


CALCULATORS: dict[str, Calculator] = {
    "valeur_stock": _valeur_stock,
    "nb_articles": _nb_articles,
    "articles_sous_seuil": _articles_sous_seuil,
    "taux_rupture": _taux_rupture,
    "rotation_stock": _rotation_stock,
    "couverture_stock": _couverture_stock,
    "stock_dormant": _stock_dormant,
    "valeur_par_categorie": _repartition("categorie", "Valeur du stock par famille", "Première famille"),
    "valeur_par_entrepot": _repartition("entrepot", "Valeur du stock par entrepôt", "Premier entrepôt"),
    "proches_peremption": _proches_peremption,
}
