"""États financiers selon le Code général de normalisation comptable (CGNC) marocain.

À partir d'une balance générale (ou d'un grand livre / journal, agrégé par compte) :
- balance par compte avec soldes débiteurs et créditeurs ;
- CPC (compte de produits et charges) ;
- ESG / tableau de formation des résultats (soldes intermédiaires de gestion) ;
- bilan (actif / passif) ;
- ratios d'analyse financière.

Convention : solde = débit − crédit. Un produit ou une dette a donc un solde négatif.
La logique du CPC et du bilan reprend celle de l'application Daftar Compta.
"""
import re
from dataclasses import dataclass, field

import pandas as pd

from .pcm import CLASSES, account_label

# Hypothèse pour les délais de paiement : créances et dettes sont TTC, au taux normal de TVA.
VAT_RATE = 0.20


def account_number(value) -> str | None:
    """Numéro de compte normalisé : « 6111.0 », « 6111 000 » ou « 6111 - Achats » → chiffres seuls."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = re.sub(r"\.0+$", "", str(value).strip()).replace(" ", "").replace(" ", "")
    match = re.match(r"\d+", text)
    return match.group(0) if match and match.group(0)[0] in "1234567" else None


@dataclass
class Ledger:
    """Balance agrégée par compte."""

    accounts: pd.DataFrame  # index : compte ; colonnes : libelle, debit, credit, solde
    notes: list[str] = field(default_factory=list)

    def sp(self, prefixes: list[str], exclude: tuple[str, ...] = ()) -> float:
        """Somme des soldes (débit − crédit) des comptes commençant par un préfixe, hors exclusions."""
        index = self.accounts.index
        mask = index.str.startswith(tuple(prefixes))
        if exclude:
            mask &= ~index.str.startswith(tuple(exclude))
        return round(float(self.accounts.loc[mask, "solde"].sum()), 2)

    def produce(self, prefixes: list[str], exclude: tuple[str, ...] = ()) -> float:
        return -self.sp(prefixes, exclude)


def build_ledger(df: pd.DataFrame) -> Ledger:
    data = df.copy()
    data["compte"] = data["compte"].map(account_number)
    dropped_text = int(data["compte"].isna().sum())
    data = data.dropna(subset=["compte"])
    data["debit"] = data["debit"].fillna(0)
    data["credit"] = data["credit"].fillna(0)
    labels = data["libelle_compte"] if "libelle_compte" in data else pd.Series(None, index=data.index)
    grouped = data.groupby("compte").agg(debit=("debit", "sum"), credit=("credit", "sum"))
    grouped["libelle"] = labels.groupby(data["compte"]).first()

    # Les lignes de sous-total (compte « 61 » au-dessus de « 6111 »...) feraient double emploi :
    # on ne garde que les comptes de détail.
    numbers = sorted(grouped.index)
    subtotals = {n for n in numbers if len(n) == 1 or any(o != n and o.startswith(n) for o in numbers)}
    grouped = grouped.drop(index=list(subtotals))

    grouped["libelle"] = [lbl if isinstance(lbl, str) and lbl.strip() else (account_label(n) or f"Compte {n}")
                          for n, lbl in zip(grouped.index, grouped["libelle"])]
    grouped["solde"] = (grouped["debit"] - grouped["credit"]).round(2)
    notes = []
    if dropped_text:
        notes.append(f"{dropped_text} lignes sans numéro de compte ignorées (titres, totaux)")
    if subtotals:
        notes.append(f"{len(subtotals)} lignes de sous-total ignorées pour éviter les doublons")
    return Ledger(grouped.sort_index(), notes)


# ---------------------------------------------------------------- CPC
def cpc(ledger: Ledger) -> dict:
    P, C = ledger.produce, ledger.sp
    pe = [
        ("Ventes de marchandises (en l'état)", P(["711"])),
        ("Ventes de biens et services produits", P(["712"])),
        ("Variation de stocks de produits (±)", P(["713"])),
        ("Immobilisations produites par l'entreprise pour elle-même", P(["714"])),
        ("Subventions d'exploitation", P(["716"])),
        ("Autres produits d'exploitation", P(["71"], ("711", "712", "713", "714", "716", "719"))),
        ("Reprises d'exploitation ; transferts de charges", P(["719"])),
    ]
    ce = [
        ("Achats revendus de marchandises", C(["611"])),
        ("Achats consommés de matières et fournitures", C(["612"])),
        ("Autres charges externes", C(["613", "614"])),
        ("Impôts et taxes", C(["616"])),
        ("Charges de personnel", C(["617"])),
        ("Autres charges d'exploitation", C(["61"], ("611", "612", "613", "614", "616", "617", "619"))),
        ("Dotations d'exploitation", C(["619"])),
    ]
    r = {"pe": pe, "ce": ce}
    r["I"] = round(sum(v for _, v in pe), 2)
    r["II"] = round(sum(v for _, v in ce), 2)
    r["III"] = round(r["I"] - r["II"], 2)
    r["IV"], r["V"] = P(["73"]), C(["63"])
    r["VI"] = round(r["IV"] - r["V"], 2)
    r["VII"] = round(r["III"] + r["VI"], 2)
    r["VIII"], r["IX"] = P(["75"]), C(["65"])
    r["X"] = round(r["VIII"] - r["IX"], 2)
    r["XI"] = round(r["VII"] + r["X"], 2)
    r["XII"] = C(["67"])
    r["XIII"] = round(r["XI"] - r["XII"], 2)
    r["ca"] = round(pe[0][1] + pe[1][1], 2)
    return r


def cpc_rows(r: dict) -> list[dict]:
    rows = [{"label": "EXPLOITATION", "type": "header"}, {"label": "Produits d'exploitation", "type": "subheader"}]
    rows += [{"label": l, "value": v, "type": "row"} for l, v in r["pe"]]
    rows.append({"label": "I. Total des produits d'exploitation", "value": r["I"], "type": "total"})
    rows.append({"label": "Charges d'exploitation", "type": "subheader"})
    rows += [{"label": l, "value": v, "type": "row"} for l, v in r["ce"]]
    rows += [
        {"label": "II. Total des charges d'exploitation", "value": r["II"], "type": "total"},
        {"label": "III. Résultat d'exploitation (I − II)", "value": r["III"], "type": "result"},
        {"label": "FINANCIER", "type": "header"},
        {"label": "IV. Produits financiers", "value": r["IV"], "type": "row"},
        {"label": "V. Charges financières", "value": r["V"], "type": "row"},
        {"label": "VI. Résultat financier (IV − V)", "value": r["VI"], "type": "result"},
        {"label": "VII. Résultat courant (III + VI)", "value": r["VII"], "type": "result"},
        {"label": "NON COURANT", "type": "header"},
        {"label": "VIII. Produits non courants", "value": r["VIII"], "type": "row"},
        {"label": "IX. Charges non courantes", "value": r["IX"], "type": "row"},
        {"label": "X. Résultat non courant (VIII − IX)", "value": r["X"], "type": "result"},
        {"label": "XI. Résultat avant impôts (VII + X)", "value": r["XI"], "type": "result"},
        {"label": "XII. Impôts sur les résultats", "value": r["XII"], "type": "row"},
        {"label": "XIII. Résultat net (XI − XII)", "value": r["XIII"], "type": "final"},
    ]
    return rows


# ---------------------------------------------------------------- Soldes intermédiaires de gestion
def esg(ledger: Ledger, r: dict) -> dict:
    P, C = ledger.produce, ledger.sp
    s = {}
    s["ventes_marchandises"] = P(["711"])
    s["achats_revendus"] = C(["611"])
    s["marge_brute"] = round(s["ventes_marchandises"] - s["achats_revendus"], 2)
    s["production"] = P(["712", "713", "714"])
    s["consommation"] = C(["612", "613", "614"])
    s["valeur_ajoutee"] = round(s["marge_brute"] + s["production"] - s["consommation"], 2)
    s["subventions"] = P(["716"])
    s["impots_taxes"] = C(["616"])
    s["personnel"] = C(["617"])
    s["ebe"] = round(s["valeur_ajoutee"] + s["subventions"] - s["impots_taxes"] - s["personnel"], 2)
    s["resultat_exploitation"] = r["III"]
    s["resultat_financier"] = r["VI"]
    s["resultat_courant"] = r["VII"]
    s["resultat_non_courant"] = r["X"]
    s["impots_resultats"] = r["XII"]
    s["resultat_net"] = r["XIII"]
    # CAF simplifiée (méthode additive) : résultat net + dotations − reprises.
    s["caf"] = round(r["XIII"] + C(["619", "639", "659"]) - P(["719", "739", "759"]), 2)
    return s


def esg_rows(s: dict) -> list[dict]:
    def row(label, key, type_="row"):
        return {"label": label, "value": s[key], "type": type_}
    return [
        row("Ventes de marchandises (en l'état)", "ventes_marchandises"),
        row("− Achats revendus de marchandises", "achats_revendus"),
        row("I. Marge brute sur ventes en l'état", "marge_brute", "result"),
        row("II. Production de l'exercice", "production"),
        row("III. Consommation de l'exercice", "consommation"),
        row("IV. Valeur ajoutée (I + II − III)", "valeur_ajoutee", "result"),
        row("+ Subventions d'exploitation", "subventions"),
        row("− Impôts et taxes", "impots_taxes"),
        row("− Charges de personnel", "personnel"),
        row("V. Excédent brut d'exploitation (EBE)" if s["ebe"] >= 0 else "V. Insuffisance brute d'exploitation (IBE)", "ebe", "result"),
        row("VI. Résultat d'exploitation", "resultat_exploitation", "result"),
        row("VII. Résultat financier", "resultat_financier"),
        row("VIII. Résultat courant", "resultat_courant", "result"),
        row("IX. Résultat non courant", "resultat_non_courant"),
        row("− Impôts sur les résultats", "impots_resultats"),
        row("X. Résultat net de l'exercice", "resultat_net", "final"),
        row("Capacité d'autofinancement (simplifiée)", "caf", "total"),
    ]


# ---------------------------------------------------------------- Bilan
def bilan(ledger: Ledger, net_result: float) -> dict:
    sp, P = ledger.sp, ledger.produce

    def asset(label, gross, depreciation):
        return {"label": label, "brut": round(gross, 2), "amort": round(depreciation, 2), "net": round(gross - depreciation, 2)}

    treasury = ledger.accounts.loc[ledger.accounts.index.str.startswith("5"), "solde"]
    treso_a, treso_p = float(treasury[treasury > 0].sum()), float(-treasury[treasury < 0].sum())

    actif = {
        "immo": [
            asset("Immobilisations en non-valeurs", sp(["21"]), -sp(["281"])),
            asset("Immobilisations incorporelles", sp(["22"]), -sp(["282"])),
            asset("Immobilisations corporelles", sp(["23"]), -sp(["283"])),
            asset("Immobilisations financières", sp(["2"], ("21", "22", "23", "28", "29")), -sp(["29"])),
        ],
        "circ": [
            asset("Stocks", sp(["31"]), -sp(["391"])),
            asset("Créances de l'actif circulant", sp(["3"], ("31", "35", "39")), -sp(["39"], ("391", "395"))),
            asset("Titres et valeurs de placement", sp(["35"]), -sp(["395"])),
        ],
        "treso": [asset("Trésorerie – actif", treso_a, 0)],
    }
    passif = {
        "cp": [
            ("Capital social ou personnel", P(["111"])),
            ("Réserves", P(["114", "115"])),
            ("Report à nouveau", P(["116"])),
            ("Résultats nets en instance d'affectation", P(["118"])),
            # Avant clôture, le résultat est encore dans les classes 6 et 7.
            ("Résultat net de l'exercice", round(P(["119"]) + net_result, 2)),
            ("Autres capitaux propres", P(["11"], ("111", "114", "115", "116", "118", "119"))),
        ],
        "fin": [
            ("Capitaux propres assimilés", P(["13"])),
            ("Dettes de financement", P(["14"])),
            ("Provisions durables pour risques et charges", P(["15"])),
            ("Autres financements permanents", P(["1"], ("11", "13", "14", "15"))),
        ],
        "circ": [
            ("Dettes du passif circulant", P(["4"], ("45",))),
            ("Autres provisions pour risques et charges", P(["45"])),
        ],
        "treso": [("Trésorerie – passif", round(treso_p, 2))],
    }
    net = lambda rows: round(sum(x["net"] for x in rows), 2)  # noqa: E731
    total = lambda rows: round(sum(v for _, v in rows), 2)  # noqa: E731
    t = {
        "immo": net(actif["immo"]), "circ": net(actif["circ"]), "treso_a": net(actif["treso"]),
        "cp": total(passif["cp"]), "fin": total(passif["fin"]), "circ_p": total(passif["circ"]),
        "treso_p": total(passif["treso"]),
        "stocks": actif["circ"][0]["net"],
        "dettes_financement": passif["fin"][1][1],
    }
    t["actif"] = round(t["immo"] + t["circ"] + t["treso_a"], 2)
    t["passif"] = round(t["cp"] + t["fin"] + t["circ_p"] + t["treso_p"], 2)
    return {"actif": actif, "passif": passif, "totals": t}


def bilan_rows(b: dict) -> dict:
    a, p, t = b["actif"], b["passif"], b["totals"]

    def total_asset(label, key, rows):
        return {"label": label, "brut": round(sum(x["brut"] for x in rows), 2),
                "amort": round(sum(x["amort"] for x in rows), 2), "net": t[key], "type": "total"}

    actif = (
        [{**x, "type": "row"} for x in a["immo"]] + [total_asset("Total actif immobilisé (I)", "immo", a["immo"])]
        + [{**x, "type": "row"} for x in a["circ"]] + [total_asset("Total actif circulant (II)", "circ", a["circ"])]
        + [{**x, "type": "row"} for x in a["treso"]] + [total_asset("Total trésorerie – actif (III)", "treso_a", a["treso"])]
        + [{"label": "TOTAL ACTIF", "brut": None, "amort": None, "net": t["actif"], "type": "final"}]
    )

    def rows(items):
        return [{"label": l, "value": v, "type": "row"} for l, v in items]

    passif = (
        rows(p["cp"]) + [{"label": "Capitaux propres", "value": t["cp"], "type": "total"}]
        + rows(p["fin"]) + [{"label": "Total financement permanent (I)", "value": round(t["cp"] + t["fin"], 2), "type": "total"}]
        + rows(p["circ"]) + [{"label": "Total passif circulant (II)", "value": t["circ_p"], "type": "total"}]
        + rows(p["treso"]) + [{"label": "Total trésorerie – passif (III)", "value": t["treso_p"], "type": "total"}]
        + [{"label": "TOTAL PASSIF", "value": t["passif"], "type": "final"}]
    )
    return {"actif": actif, "passif": passif}


# ---------------------------------------------------------------- Analyse complète
@dataclass
class Analysis:
    ledger: Ledger
    cpc: dict
    esg: dict
    bilan: dict
    indicators: dict


def _ratio(num: float, den: float, factor: float = 1) -> float | None:
    return round(num / den * factor, 2) if den else None


def analyse(df: pd.DataFrame) -> Analysis:
    ledger = build_ledger(df)
    r = cpc(ledger)
    s = esg(ledger, r)
    b = bilan(ledger, r["XIII"])
    t = b["totals"]
    ca = r["ca"]
    purchases = ledger.sp(["611", "612", "613", "614"])
    i = {
        "ca": ca,
        "resultat_net": r["XIII"],
        "valeur_ajoutee": s["valeur_ajoutee"],
        "ebe": s["ebe"],
        "caf": s["caf"],
        "charges_personnel": s["personnel"],
        "financement_permanent": round(t["cp"] + t["fin"], 2),
        "fonds_roulement": round(t["cp"] + t["fin"] - t["immo"], 2),
        "bfr": round(t["circ"] - t["circ_p"], 2),
        "tresorerie_nette": round(t["treso_a"] - t["treso_p"], 2),
        "marge_nette": _ratio(r["XIII"], ca, 100),
        "taux_valeur_ajoutee": _ratio(s["valeur_ajoutee"], ca, 100),
        "taux_ebe": _ratio(s["ebe"], ca, 100),
        "poids_charges_personnel": _ratio(s["personnel"], ca, 100),
        "liquidite_generale": _ratio(t["circ"] + t["treso_a"], t["circ_p"] + t["treso_p"]),
        "liquidite_reduite": _ratio(t["circ"] - t["stocks"] + t["treso_a"], t["circ_p"] + t["treso_p"]),
        "autonomie_financiere": _ratio(t["cp"], t["passif"], 100),
        "endettement": _ratio(t["dettes_financement"], t["cp"]),
        "rentabilite_financiere": _ratio(r["XIII"], t["cp"], 100),
        "delai_clients": _ratio(ledger.sp(["342"]), ca * (1 + VAT_RATE), 360),
        "delai_fournisseurs": _ratio(-ledger.sp(["441"]), purchases * (1 + VAT_RATE), 360),
        "ecart_bilan": round(t["actif"] - t["passif"], 2),
        "ecart_balance": round(float(ledger.accounts["debit"].sum() - ledger.accounts["credit"].sum()), 2),
    }
    return Analysis(ledger, r, s, b, i)


RATIOS = [
    # (clé, libellé, unité, explication)
    ("marge_nette", "Marge nette", "%", "Résultat net / chiffre d'affaires"),
    ("taux_valeur_ajoutee", "Taux de valeur ajoutée", "%", "Valeur ajoutée / chiffre d'affaires"),
    ("taux_ebe", "Taux d'EBE", "%", "EBE / chiffre d'affaires"),
    ("poids_charges_personnel", "Poids des charges de personnel", "%", "Charges de personnel / chiffre d'affaires"),
    ("rentabilite_financiere", "Rentabilité financière (ROE)", "%", "Résultat net / capitaux propres"),
    ("autonomie_financiere", "Autonomie financière", "%", "Capitaux propres / total du bilan"),
    ("endettement", "Ratio d'endettement", "ratio", "Dettes de financement / capitaux propres"),
    ("liquidite_generale", "Liquidité générale", "ratio", "(Actif circulant + trésorerie actif) / (passif circulant + trésorerie passif)"),
    ("liquidite_reduite", "Liquidité réduite", "ratio", "Idem, hors stocks"),
    ("delai_clients", "Délai moyen de paiement clients", "jours", "Clients (342) / CA TTC × 360"),
    ("delai_fournisseurs", "Délai moyen de paiement fournisseurs", "jours", "Fournisseurs (441) / achats TTC × 360"),
    ("fonds_roulement", "Fonds de roulement", "MAD", "Financement permanent − actif immobilisé"),
    ("bfr", "Besoin en fonds de roulement", "MAD", "Actif circulant − passif circulant"),
    ("tresorerie_nette", "Trésorerie nette", "MAD", "Trésorerie actif − trésorerie passif (= FR − BFR)"),
    ("caf", "Capacité d'autofinancement", "MAD", "Résultat net + dotations − reprises"),
]


def statements(a: Analysis) -> dict:
    """Représentation prête à afficher : balance, CPC, ESG, bilan et ratios."""
    acc = a.ledger.accounts
    balance_rows = [
        {"compte": n, "libelle": row.libelle, "classe": CLASSES.get(n[0], ""), "debit": round(row.debit, 2),
         "credit": round(row.credit, 2), "solde_debiteur": round(max(row.solde, 0), 2),
         "solde_crediteur": round(max(-row.solde, 0), 2)}
        for n, row in acc.iterrows()
    ]
    totals = {k: round(sum(r[k] for r in balance_rows), 2) for k in ("debit", "credit", "solde_debiteur", "solde_crediteur")}
    checks = []
    if abs(a.indicators["ecart_balance"]) > 1:
        checks.append(f"La balance n'est pas équilibrée : écart de {a.indicators['ecart_balance']:,.2f} MAD entre débits et crédits".replace(",", " "))
    if abs(a.indicators["ecart_bilan"]) > 1:
        checks.append(f"Le bilan présente un écart de {a.indicators['ecart_bilan']:,.2f} MAD entre actif et passif".replace(",", " "))
    return {
        "balance": {"rows": balance_rows, "totals": totals},
        "cpc": cpc_rows(a.cpc),
        "esg": esg_rows(a.esg),
        "bilan": bilan_rows(a.bilan),
        "ratios": [{"key": k, "label": l, "unit": u, "formula": f, "value": a.indicators.get(k)} for k, l, u, f in RATIOS],
        "notes": a.ledger.notes,
        "checks": checks,
    }
