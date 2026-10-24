"""KPI du tableau de bord commercial (fichier de ventes)."""
import pandas as pd

from ...importers.mapping import normalize
from .common import Calculator, bar, evolution, has_dates, line, month_label, monthly, pct, share_of_top, today

_PAID = ("regle", "paye", "paid", "oui", "yes", "solde", "encaisse", "ok")
_UNPAID = ("non", "impaye", "pas", "attente", "partiel", "unpaid", "no", "retard", "en cours", "du")


def is_unpaid(value: str | None) -> bool:
    if not value:
        return False
    text = normalize(value)
    words = set(text.split())
    if any(w in words for w in _UNPAID) or any(u in text for u in ("impaye", "attente", "partiel", "unpaid")):
        return True
    return not any(p in text for p in _PAID)


def _ca_total(df):
    total = df["montant_ht"].sum()
    if "date" not in df:
        return float(total), {}
    series = monthly(df, "montant_ht")
    return float(total), {"chart": line("Chiffre d'affaires mensuel", series, "MAD"), "delta": evolution(series)}


def _ca_evolution(df):
    series = monthly(df, "montant_ht")
    if len(series) < 2:
        raise ValueError("Il faut au moins deux mois de ventes")
    return evolution(series), {"detail": f"{month_label(series.index[-1])} comparé à {month_label(series.index[-2])}"}


def _nb_ventes(df):
    return float(df["montant_ht"].notna().sum()), {}


def _panier_moyen(df):
    sales = df["montant_ht"].dropna()
    return (float(sales.mean()) if len(sales) else None), {}


def _nb_clients_actifs(df):
    return float(df["client"].nunique()), {}


def _nouveaux_clients(df):
    data = df.dropna(subset=["date", "client"])
    if data.empty:
        return None, {}
    first = data.groupby("client")["date"].min().dt.to_period("M")
    full = pd.period_range(data["date"].min().to_period("M"), data["date"].max().to_period("M"), freq="M")
    counts = first.value_counts().sort_index().reindex(full, fill_value=0)
    return float(counts.iloc[-1]), {
        "detail": f"Premier achat en {month_label(full[-1])}",
        "chart": line("Nouveaux clients par mois", counts, "nombre"),
    }


def _concentration_clients(df):
    by_client = df.groupby("client")["montant_ht"].sum().sort_values(ascending=False)
    return pct(by_client.head(5).sum(), by_client.sum()), {"chart": bar("CA des principaux clients", by_client, "MAD")}


def _top_produits(df):
    by_product = df.groupby("produit")["montant_ht"].sum()
    if by_product.empty:
        return None, {}
    return float(by_product.max()), {
        "detail": f"Meilleur produit : {by_product.idxmax()}",
        "chart": bar("CA par produit", by_product, "MAD"),
    }


def _quantite_vendue(df):
    return float(df["quantite"].sum()), {}


def _marge_brute(df):
    data = df.dropna(subset=["montant_ht", "cout_achat"])
    value = pct(data["montant_ht"].sum() - data["cout_achat"].sum(), data["montant_ht"].sum())
    chart = None
    if "date" in data:
        ca, cost = monthly(data, "montant_ht"), monthly(data, "cout_achat")
        chart = line("Taux de marge brute mensuel", ((ca - cost) / ca.where(ca != 0) * 100).fillna(0), "%")
    return value, {"chart": chart}


def _ca_par_commercial(df):
    by_rep = df.groupby("commercial")["montant_ht"].sum()
    if by_rep.empty:
        return None, {}
    return float(by_rep.mean()), {
        "detail": f"CA moyen par commercial · meilleur : {by_rep.idxmax()}",
        "chart": bar("CA par commercial", by_rep, "MAD"),
    }


def _nb_commerciaux(df):
    return float(df["commercial"].nunique()), {}


def _repartition(column: str, title: str, label: str):
    def calculator(df):
        series = df.groupby(column)["montant_ht"].sum()
        value, detail = share_of_top(series, label)
        return value, {"detail": detail, "chart": bar(title, series, "MAD")}
    return calculator


def _taux_impayes(df):
    unpaid = df["statut_paiement"].map(is_unpaid)
    return pct(df.loc[unpaid, "montant_ht"].sum(), df["montant_ht"].sum()), {
        "detail": f"{int(unpaid.sum())} ventes non réglées",
    }


def _creances_echues(df):
    overdue = df["statut_paiement"].map(is_unpaid) & (df["date_echeance"] < today())
    return float(df.loc[overdue, "montant_ht"].sum()), {"detail": f"{int(overdue.sum())} factures en retard"}


def _realisation_objectif(df):
    """CA réalisé / objectif. L'objectif est souvent répété sur chaque ligne d'un même mois :
    on retient un objectif par mois (le plus élevé indiqué), cumulé sur les mois couverts."""
    data = df.dropna(subset=["objectif"])
    if has_dates(data):
        months = data.dropna(subset=["date"])
        total_target = months.groupby(months["date"].dt.to_period("M"))["objectif"].max().sum()
    else:
        target = data["objectif"]
        total_target = target.drop_duplicates().sum() if target.nunique() < len(target) else target.sum()
    return pct(df["montant_ht"].sum(), total_target), {}


CALCULATORS: dict[str, Calculator] = {
    "ca_total": _ca_total,
    "ca_evolution": _ca_evolution,
    "nb_ventes": _nb_ventes,
    "panier_moyen": _panier_moyen,
    "nb_clients_actifs": _nb_clients_actifs,
    "nouveaux_clients": _nouveaux_clients,
    "concentration_clients": _concentration_clients,
    "top_produits": _top_produits,
    "quantite_vendue": _quantite_vendue,
    "marge_brute": _marge_brute,
    "ca_par_commercial": _ca_par_commercial,
    "nb_commerciaux": _nb_commerciaux,
    "ca_par_region": _repartition("region", "CA par région", "Part de la première région"),
    "ca_par_canal": _repartition("canal", "CA par canal", "Part du premier canal"),
    "taux_impayes": _taux_impayes,
    "creances_echues": _creances_echues,
    "realisation_objectif": _realisation_objectif,
}
