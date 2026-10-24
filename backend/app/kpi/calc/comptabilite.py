"""KPI du tableau de bord comptable, calculés à partir des états financiers (CGNC)."""
import pandas as pd

from ..accounting import Analysis, analyse
from .common import Calculator, bar, has_dates, line, monthly

_cache: tuple[tuple, Analysis] | None = None


def _analysis(df: pd.DataFrame) -> Analysis:
    """Les états financiers sont calculés une seule fois pour tous les KPI d'un même jeu de données."""
    global _cache
    key = (len(df), int(pd.util.hash_pandas_object(df, index=True).sum()))
    if _cache is None or _cache[0] != key:
        _cache = (key, analyse(df))
    return _cache[1]


def _require_activity(a: Analysis) -> None:
    if not a.indicators["ca"]:
        raise ValueError("Aucun chiffre d'affaires (comptes 711 / 712) dans la balance")


def _indicator(key: str, needs_sales: bool = False, chart=None, detail=None):
    def calculator(df):
        a = _analysis(df)
        if needs_sales:
            _require_activity(a)
        extras = {}
        if chart:
            extras["chart"] = chart(df, a)
        if detail:
            extras["detail"] = detail(a)
        return a.indicators[key], extras
    return calculator


def _sales_chart(df: pd.DataFrame, a: Analysis):
    """CA mensuel si les écritures sont datées (grand livre), sinon répartition des ventes."""
    if has_dates(df):
        sales = df[df["compte"].astype(str).str.match(r"^71[12]")]
        if not sales.empty:
            series = monthly(sales.assign(ca=sales["credit"].fillna(0) - sales["debit"].fillna(0)), "ca")
            return line("Chiffre d'affaires mensuel", series, "MAD")
    pe = dict(a.cpc["pe"])
    return bar("Composition du chiffre d'affaires", pd.Series({
        "Ventes de marchandises": pe["Ventes de marchandises (en l'état)"],
        "Ventes de biens et services": pe["Ventes de biens et services produits"],
    }), "MAD", sort=False)


def _results_chart(_df, a: Analysis):
    s = a.esg
    return bar("Formation du résultat", pd.Series({
        "Chiffre d'affaires": a.indicators["ca"],
        "Valeur ajoutée": s["valeur_ajoutee"],
        "EBE": s["ebe"],
        "Résultat d'exploitation": s["resultat_exploitation"],
        "Résultat courant": s["resultat_courant"],
        "Résultat net": s["resultat_net"],
    }), "MAD", sort=False)


def _charges_chart(_df, a: Analysis):
    charges = pd.Series(dict(a.cpc["ce"]))
    charges["Charges financières"] = a.cpc["V"]
    charges["Charges non courantes"] = a.cpc["IX"]
    charges["Impôts sur les résultats"] = a.cpc["XII"]
    return bar("Charges par nature", charges[charges != 0], "MAD")


def _balance_sheet_chart(_df, a: Analysis):
    i = a.indicators
    return bar("Équilibre financier", pd.Series({
        "Fonds de roulement": i["fonds_roulement"],
        "Besoin en fonds de roulement": i["bfr"],
        "Trésorerie nette": i["tresorerie_nette"],
    }), "MAD", sort=False)


def _bfr_chart(_df, a: Analysis):
    t = a.bilan["totals"]
    return bar("Composition du BFR", pd.Series({
        "Stocks": t["stocks"],
        "Créances et autres actifs circulants": round(t["circ"] - t["stocks"], 2),
        "Dettes du passif circulant": -t["circ_p"],
    }), "MAD", sort=False)


def _result_detail(a: Analysis) -> str:
    return f"Résultat avant impôts : {a.cpc['XI']:,.0f} MAD · impôts : {a.cpc['XII']:,.0f} MAD".replace(",", " ")


CALCULATORS: dict[str, Calculator] = {
    "ca_comptable": _indicator("ca", chart=_sales_chart),
    "resultat_net": _indicator("resultat_net", chart=_results_chart, detail=_result_detail),
    "marge_nette": _indicator("marge_nette", needs_sales=True),
    "valeur_ajoutee": _indicator("valeur_ajoutee", detail=lambda a: f"Soit {a.indicators['taux_valeur_ajoutee'] or 0:.1f} % du CA".replace(".", ",")),
    "ebe": _indicator("ebe"),
    "taux_ebe": _indicator("taux_ebe", needs_sales=True),
    "poids_charges_personnel": _indicator("poids_charges_personnel", needs_sales=True, chart=_charges_chart),
    "fonds_roulement": _indicator("fonds_roulement", chart=_balance_sheet_chart),
    "bfr": _indicator("bfr", chart=_bfr_chart),
    "tresorerie_nette": _indicator("tresorerie_nette"),
    "liquidite_generale": _indicator("liquidite_generale"),
    "endettement": _indicator("endettement"),
    "capacite_autofinancement": _indicator("caf"),
    "rentabilite_financiere": _indicator("rentabilite_financiere"),
    "autonomie_financiere": _indicator("autonomie_financiere"),
    "delai_clients": _indicator("delai_clients", needs_sales=True),
    "delai_fournisseurs": _indicator("delai_fournisseurs"),
}
