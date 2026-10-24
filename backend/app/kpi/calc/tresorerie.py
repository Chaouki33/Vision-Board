"""KPI du tableau de bord trésorerie (relevés bancaires ou journal de caisse).

Les décaissements sont pris en valeur absolue : certains relevés les notent en négatif.
"""
import pandas as pd

from .common import Calculator, bar, has_dates, line, month_label, monthly, share_of_top


def _out(df: pd.DataFrame) -> pd.Series:
    return df["decaissement"].fillna(0).abs()


def _in(df: pd.DataFrame) -> pd.Series:
    return df["encaissement"].fillna(0).abs()


def _last_balances(df: pd.DataFrame) -> pd.Series:
    """Dernier solde connu de chaque compte (un seul compte si la banque n'est pas indiquée)."""
    data = df.dropna(subset=["solde"])
    data = data.sort_values("date", na_position="first", kind="stable") if "date" in data else data
    if "banque" in data and data["banque"].notna().any():
        return data.groupby("banque")["solde"].last()
    return data["solde"].tail(1)


def _monthly_balance(df: pd.DataFrame) -> pd.Series:
    """Solde de fin de mois, tous comptes confondus."""
    data = df.dropna(subset=["solde", "date"]).sort_values("date", kind="stable")
    month = data["date"].dt.to_period("M")
    if "banque" in data and data["banque"].notna().any():
        per_bank = data.groupby([month, data["banque"]])["solde"].last().unstack().ffill()
        return per_bank.sum(axis=1)
    return data.groupby(month)["solde"].last()


def _monthly_outflow(df: pd.DataFrame) -> pd.Series:
    return monthly(df.assign(sortie=_out(df)), "sortie")


def _solde_tresorerie(df):
    balances = _last_balances(df)
    if balances.empty:
        return None, {}
    series = _monthly_balance(df)
    extras = {"chart": line("Solde de trésorerie en fin de mois", series, "MAD")} if len(series) > 1 else {}
    if len(series) > 1 and series.iloc[-2]:
        extras["delta"] = round(100 * (series.iloc[-1] - series.iloc[-2]) / abs(series.iloc[-2]), 2)
    return float(balances.sum()), extras


def _flux_net(df):
    return float(_in(df).sum() - _out(df).sum()), {}


def _total_encaissements(df):
    extras = {"chart": line("Encaissements par mois", monthly(df.assign(entree=_in(df)), "entree"), "MAD")} if has_dates(df) else {}
    return float(_in(df).sum()), extras


def _total_decaissements(df):
    extras = {"chart": line("Décaissements par mois", _monthly_outflow(df), "MAD")} if has_dates(df) else {}
    return float(_out(df).sum()), extras


def _evolution_tresorerie(df):
    flows = df.assign(net=_in(df) - _out(df))
    series = monthly(flows, "net")
    if series.empty:
        return None, {}
    return float(series.iloc[-1]), {
        "detail": f"Flux net de {month_label(series.index[-1])}",
        "chart": line("Flux net mensuel (encaissements − décaissements)", series, "MAD"),
    }


def _decaissements_mensuels_moyens(df):
    series = _monthly_outflow(df)
    return (float(series.mean()) if len(series) else None), {"detail": f"Moyenne sur {len(series)} mois"}


def _autonomie_tresorerie(df):
    balance = _last_balances(df).sum()
    burn = _monthly_outflow(df).mean()
    if not burn or pd.isna(burn):
        return None, {"detail": "Aucun décaissement enregistré"}
    return round(float(balance / burn), 1), {"detail": f"Décaissements moyens : {burn:,.0f} MAD par mois".replace(",", " ")}


def _solde_par_banque(df):
    balances = _last_balances(df)
    if balances.empty:
        return None, {}
    return float(balances.sum()), {"detail": f"{len(balances)} comptes", "chart": bar("Solde par banque", balances, "MAD", fold=False)}


def _decaissements_par_categorie(df):
    series = _out(df).groupby(df["categorie"]).sum()
    value, detail = share_of_top(series, "Premier poste de dépenses")
    return value, {"detail": detail, "chart": bar("Décaissements par catégorie", series, "MAD")}


CALCULATORS: dict[str, Calculator] = {
    "solde_tresorerie": _solde_tresorerie,
    "flux_net": _flux_net,
    "total_encaissements": _total_encaissements,
    "total_decaissements": _total_decaissements,
    "evolution_tresorerie": _evolution_tresorerie,
    "decaissements_mensuels_moyens": _decaissements_mensuels_moyens,
    "autonomie_tresorerie": _autonomie_tresorerie,
    "solde_par_banque": _solde_par_banque,
    "decaissements_par_categorie": _decaissements_par_categorie,
}
