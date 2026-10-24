"""KPI du tableau de bord RH (fichier du personnel : une ligne par salarié).

Les salariés « présents » sont ceux sans date de sortie, ou dont la sortie est future.
"""
import pandas as pd

from ...importers.mapping import normalize
from .common import Calculator, bar, line, pct, today

# Jours ouvrables par an retenus pour l'absentéisme (5 jours × 52 semaines).
WORKING_DAYS_PER_YEAR = 260
_INTERN = ("stage", "stagiaire", "pfe", "intern", "apprenti")


def present(df: pd.DataFrame) -> pd.DataFrame:
    if "date_sortie" not in df:
        return df
    return df[df["date_sortie"].isna() | (df["date_sortie"] > today())]


def _headcount(df: pd.DataFrame) -> int:
    return len(present(df))


def _by_department(df: pd.DataFrame, values: pd.Series, title: str, unit: str, how: str = "sum", fold: bool = True):
    if "departement" not in df or df["departement"].isna().all():
        return None
    grouped = values.groupby(df["departement"])
    return bar(title, grouped.sum() if how == "sum" else grouped.mean(), unit, fold=fold)


def _effectif_total(df):
    staff = present(df)
    return float(len(staff)), {"chart": _by_department(staff, pd.Series(1, index=staff.index), "Effectif par département", "nombre")}


def _contract_counts(df: pd.DataFrame) -> pd.Series:
    return present(df)["type_contrat"].dropna().map(lambda v: str(v).strip().upper()).value_counts()


def _repartition_contrats(df):
    counts = _contract_counts(df)
    if counts.empty:
        return None, {}
    permanent = counts[[c for c in counts.index if "CDI" in c]].sum()
    if permanent:
        value, detail = pct(permanent, counts.sum()), f"{int(permanent)} CDI sur {int(counts.sum())} salariés"
    else:
        value, detail = pct(counts.max(), counts.sum()), f"Contrat le plus fréquent : {counts.idxmax()}"
    return value, {"detail": detail, "chart": bar("Salariés par type de contrat", counts, "nombre")}


def is_intern(value) -> bool:
    return value is not None and any(word in normalize(value) for word in _INTERN)


def _nb_stagiaires(df):
    staff = present(df)
    interns = staff["type_contrat"].map(is_intern)
    return float(interns.sum()), {"detail": f"{pct(interns.sum(), len(staff)) or 0:.0f} % de l'effectif".replace(".", ",")}


def _recrutements(df):
    end = today().to_period("M")
    months = pd.period_range(end - 11, end, freq="M")
    hires = df["date_embauche"].dropna()
    hires = hires[hires.dt.to_period("M").isin(months)]
    counts = hires.dt.to_period("M").value_counts().reindex(months, fill_value=0)
    return float(counts.sum()), {"detail": "Embauches des 12 derniers mois", "chart": line("Embauches par mois", counts, "nombre")}


def _staff_at(df: pd.DataFrame, moment: pd.Timestamp) -> int:
    hired = df["date_embauche"].isna() | (df["date_embauche"] <= moment)
    still = df["date_sortie"].isna() | (df["date_sortie"] > moment)
    return int((hired & still).sum())


def _turnover(df):
    end = today()
    start = end - pd.DateOffset(years=1)
    entries = df["date_embauche"].between(start, end).sum()
    exits = df["date_sortie"].between(start, end).sum()
    average = (_staff_at(df, start) + _staff_at(df, end)) / 2
    if not average:
        return None, {}
    return round(100 * ((entries + exits) / 2) / average, 2), {
        "detail": f"{int(entries)} entrées et {int(exits)} sorties sur 12 mois",
    }


def _masse_salariale(df):
    staff = present(df)
    return float(staff["salaire_brut"].sum()), {
        "detail": f"Soit {staff['salaire_brut'].sum() * 12:,.0f} MAD par an".replace(",", " "),
        "chart": _by_department(staff, staff["salaire_brut"], "Masse salariale par département", "MAD"),
    }


def _salaire_moyen(df):
    staff = present(df).dropna(subset=["salaire_brut"])
    if staff.empty:
        return None, {}
    return float(staff["salaire_brut"].mean()), {
        "detail": f"Salaire médian : {staff['salaire_brut'].median():,.0f} MAD".replace(",", " "),
        "chart": _by_department(staff, staff["salaire_brut"], "Salaire moyen par département", "MAD", how="mean", fold=False),
    }


def _taux_absenteisme(df):
    staff = present(df)
    if staff.empty:
        return None, {}
    absences = staff["jours_absence"].fillna(0)
    return pct(absences.sum(), len(staff) * WORKING_DAYS_PER_YEAR), {
        "detail": f"{absences.sum():.0f} jours d'absence · base {WORKING_DAYS_PER_YEAR} jours ouvrables par an",
        "chart": _by_department(staff, absences, "Jours d'absence par département", "jours"),
    }


def _solde_conges(df):
    staff = present(df)
    balance = staff["jours_conges_acquis"].fillna(0) - staff["jours_conges_pris"].fillna(0)
    return float(balance.sum()), {"detail": f"{int((balance > 20).sum())} salariés avec plus de 20 jours restants"}


def _effectif_par_departement(df):
    counts = present(df)["departement"].dropna().value_counts()
    if counts.empty:
        return None, {}
    return float(len(counts)), {
        "detail": f"Département le plus important : {counts.idxmax()}",
        "chart": bar("Effectif par département", counts, "nombre"),
    }


def _gender(value) -> str | None:
    if value is None:
        return None
    text = normalize(value)
    if text.startswith(("f", "w")):
        return "Femmes"
    if text.startswith(("h", "m")):
        return "Hommes"
    return None


def _parite(df):
    genders = present(df)["sexe"].map(_gender).dropna()
    counts = genders.value_counts()
    return pct(counts.get("Femmes", 0), counts.sum()), {"chart": bar("Effectif par sexe", counts, "nombre") if len(counts) else None}


def _anciennete_moyenne(df):
    hires = present(df)["date_embauche"].dropna()
    if hires.empty:
        return None, {}
    months = (today() - hires).dt.days / 30.44
    return round(float(months.mean()), 1), {"detail": f"Soit {months.mean() / 12:.1f} ans".replace(".", ",")}


def _age_moyen(df):
    births = present(df)["date_naissance"].dropna()
    if births.empty:
        return None, {}
    return round(float(((today() - births).dt.days / 365.25).mean()), 1), {}


def _formation_par_salarie(df):
    staff = present(df)
    return (round(float(staff["heures_formation"].fillna(0).sum() / len(staff)), 1) if len(staff) else None), {}


CALCULATORS: dict[str, Calculator] = {
    "effectif_total": _effectif_total,
    "repartition_contrats": _repartition_contrats,
    "nb_stagiaires": _nb_stagiaires,
    "recrutements": _recrutements,
    "turnover": _turnover,
    "masse_salariale": _masse_salariale,
    "salaire_moyen": _salaire_moyen,
    "taux_absenteisme": _taux_absenteisme,
    "solde_conges": _solde_conges,
    "effectif_par_departement": _effectif_par_departement,
    "parite": _parite,
    "anciennete_moyenne": _anciennete_moyenne,
    "age_moyen": _age_moyen,
    "formation_par_salarie": _formation_par_salarie,
}
