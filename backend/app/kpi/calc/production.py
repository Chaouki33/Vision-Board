"""KPI du tableau de bord production (rapports de production par jour, ligne ou ordre)."""
import pandas as pd

from .common import Calculator, bar, evolution, has_dates, line, month_label, monthly, pct


def _by_line_or_month(df: pd.DataFrame, compute, title: str, unit: str):
    """Graphique par ligne de production si elle est connue, sinon par mois."""
    if "ligne" in df and df["ligne"].notna().any():
        return bar(f"{title} par ligne", df.groupby("ligne").apply(compute, include_groups=False), unit, fold=False)
    if has_dates(df):
        return line(f"{title} par mois", df.groupby(df["date"].dt.to_period("M")).apply(compute, include_groups=False), unit)
    return None


def _volume_produit(df):
    total = df["quantite_produite"].sum()
    if not has_dates(df):
        return float(total), {}
    series = monthly(df, "quantite_produite")
    return float(total), {"chart": line("Production mensuelle", series, "nombre"), "delta": evolution(series)}


def _evolution_production(df):
    series = monthly(df, "quantite_produite")
    if len(series) < 2:
        raise ValueError("Il faut au moins deux mois de production")
    return evolution(series), {"detail": f"{month_label(series.index[-1])} comparé à {month_label(series.index[-2])}"}


def _rate(numerator: str, denominator: str):
    return lambda g: pct(g[numerator].sum(), g[denominator].sum()) or 0


def _realisation_production(df):
    data = df.dropna(subset=["quantite_produite", "objectif"])
    value = pct(data["quantite_produite"].sum(), data["objectif"].sum())
    return value, {"chart": _by_line_or_month(data, _rate("quantite_produite", "objectif"), "Réalisation du plan", "%")}


def _scrap_rate(g):
    produced, scrap = g["quantite_produite"].sum(), g["quantite_rebut"].sum()
    return pct(scrap, produced + scrap) or 0


def _taux_rebut(df):
    data = df.dropna(subset=["quantite_produite", "quantite_rebut"], how="all").fillna(
        {"quantite_produite": 0, "quantite_rebut": 0})
    return _scrap_rate(data), {
        "detail": f"{int(data['quantite_rebut'].sum()):,} unités rebutées".replace(",", " "),
        "chart": _by_line_or_month(data, _scrap_rate, "Taux de rebut", "%"),
    }


def _availability(g):
    planned = g["temps_planifie"].sum()
    return pct(planned - g["temps_arret"].fillna(0).sum(), planned) or 0


def _taux_disponibilite(df):
    data = df.dropna(subset=["temps_planifie"])
    return _availability(data), {"chart": _by_line_or_month(data, _availability, "Disponibilité", "%")}


def _oee(g):
    """TRS = disponibilité × performance × qualité."""
    planned = g["temps_planifie"].sum()
    run_time = g["temps_planifie"] - g["temps_arret"].fillna(0)
    theoretical = (g["cadence_theorique"] * run_time).sum()
    good = g["quantite_produite"].sum()
    output = good + g["quantite_rebut"].fillna(0).sum()
    if not planned or not theoretical or not output:
        return 0
    availability = run_time.sum() / planned
    performance = min(output / theoretical, 1)
    quality = good / output
    return round(100 * availability * performance * quality, 2)


def _trs(df):
    data = df.dropna(subset=["temps_planifie", "cadence_theorique", "quantite_produite"])
    if data.empty:
        return None, {}
    return _oee(data), {"chart": _by_line_or_month(data, _oee, "TRS", "%")}


def _temps_arret_total(df):
    total = df["temps_arret"].sum()
    chart = None
    if "ligne" in df and df["ligne"].notna().any():
        chart = bar("Temps d'arrêt par ligne", df.groupby("ligne")["temps_arret"].sum(), "heures")
    elif has_dates(df):
        chart = line("Temps d'arrêt par mois", monthly(df, "temps_arret"), "heures")
    return float(total), {"chart": chart}


def _cout_unitaire_production(df):
    data = df.dropna(subset=["cout_production", "quantite_produite"])
    produced = data["quantite_produite"].sum()
    if not produced:
        return None, {}
    chart = None
    if has_dates(data):
        cost, qty = monthly(data, "cout_production"), monthly(data, "quantite_produite")
        chart = line("Coût unitaire par mois", (cost / qty.where(qty != 0)).fillna(0), "MAD")
    return float(data["cout_production"].sum() / produced), {"chart": chart}


def _repartition(column: str, title: str, label: str):
    def calculator(df):
        series = df.groupby(column)["quantite_produite"].sum()
        if series.empty:
            return None, {}
        return float(series.max()), {"detail": f"{label} : {series.idxmax()}", "chart": bar(title, series, "nombre")}
    return calculator


CALCULATORS: dict[str, Calculator] = {
    "volume_produit": _volume_produit,
    "evolution_production": _evolution_production,
    "realisation_production": _realisation_production,
    "taux_rebut": _taux_rebut,
    "taux_disponibilite": _taux_disponibilite,
    "trs": _trs,
    "temps_arret_total": _temps_arret_total,
    "cout_unitaire_production": _cout_unitaire_production,
    "production_par_ligne": _repartition("ligne", "Production par ligne", "Ligne la plus productive"),
    "production_par_produit": _repartition("produit", "Production par produit", "Produit le plus fabriqué"),
}
