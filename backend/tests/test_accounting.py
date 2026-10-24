"""États financiers CGNC : balance, CPC, soldes de gestion, bilan et ratios."""
import io

import pytest
from openpyxl import Workbook

from app.kpi.accounting import account_number, analyse, build_ledger, statements
from app.kpi.catalog import KPIS
from app.kpi.compute import build_frame, compute_kpi

from .conftest import register

# Petite balance équilibrée, avant clôture (le résultat est encore en classes 6 et 7).
BALANCE = [
    ("1111", "Capital social", 0, 95_000),
    ("1481", "Emprunts", 0, 40_000),
    ("2332", "Matériel et outillage", 120_000, 0),
    ("2833", "Amortissements du matériel", 0, 30_000),
    ("3111", "Marchandises", 20_000, 0),
    ("3421", "Clients", 36_000, 0),
    ("4411", "Fournisseurs", 0, 24_000),
    ("5141", "Banque", 18_000, 0),
    ("5520", "Crédits de trésorerie", 0, 5_000),
    ("6111", "Achats de marchandises", 100_000, 0),
    ("6171", "Rémunérations du personnel", 30_000, 0),
    ("6193", "Dotations aux amortissements", 10_000, 0),
    ("6311", "Intérêts", 5_000, 0),
    ("6701", "Impôts sur les résultats", 5_000, 0),
    ("7111", "Ventes de marchandises", 0, 150_000),
]


def ledger_frame(rows=BALANCE):
    data = [{"compte": c, "libelle_compte": l, "debit": d, "credit": cr} for c, l, d, cr in rows]
    return build_frame("comptabilite", data, {k: k for k in data[0]})


def test_account_number_normalisation():
    assert account_number("6111.0") == "6111"
    assert account_number(61110000.0) == "61110000"
    assert account_number("6111 000") == "6111000"
    assert account_number("4411 - Fournisseurs") == "4411"
    assert account_number("Total classe 6") is None
    assert account_number("9999") is None


def test_cpc_and_esg():
    a = analyse(ledger_frame())
    assert a.cpc["I"] == 150_000
    assert a.cpc["II"] == 140_000
    assert a.cpc["III"] == 10_000
    assert a.cpc["VI"] == -5_000
    assert a.cpc["XIII"] == 0  # 10 000 − 5 000 − 5 000
    assert a.esg["marge_brute"] == 50_000
    assert a.esg["valeur_ajoutee"] == 50_000
    assert a.esg["ebe"] == 20_000
    assert a.esg["caf"] == 10_000  # résultat 0 + dotations 10 000


def test_bilan_is_balanced_and_financial_equilibrium():
    a = analyse(ledger_frame())
    t = a.bilan["totals"]
    assert t["immo"] == 90_000
    assert t["actif"] == t["passif"] == 164_000
    i = a.indicators
    assert i["fonds_roulement"] == 45_000  # 135 000 − 90 000
    assert i["bfr"] == 32_000  # 56 000 − 24 000
    assert i["tresorerie_nette"] == 13_000
    assert i["fonds_roulement"] - i["bfr"] == i["tresorerie_nette"]
    assert i["endettement"] == 0.42


def test_subtotal_lines_are_not_double_counted():
    rows = BALANCE + [("6", "Total classe 6", 150_000, 0), ("61", "Charges d'exploitation", 140_000, 0)]
    ledger = build_ledger(ledger_frame(rows))
    assert "61" not in ledger.accounts.index and "6" not in ledger.accounts.index
    assert ledger.sp(["6"]) == 150_000
    assert any("sous-total" in n for n in ledger.notes)


def test_unbalanced_balance_is_reported():
    s = statements(analyse(ledger_frame(BALANCE + [("5161", "Caisse", 1_000, 0)])))
    assert any("pas équilibrée" in c for c in s["checks"])


def test_every_accounting_kpi_is_computed():
    df = ledger_frame()
    for kpi in (k for k in KPIS if k.domain == "comptabilite"):
        result = compute_kpi(kpi.code, df)
        assert result.error is None, f"{kpi.code} : {result.error}"
    assert compute_kpi("resultat_net", df).chart.labels[0] == "Chiffre d'affaires"


def test_accounting_endpoint(client):
    headers, _ = register(client)
    company = client.post("/api/companies", headers=headers, json={"name": "Compta", "sector": "commerce", "employees": 12}).json()
    base = f"/api/companies/{company['id']}"
    assert client.get(f"{base}/accounting", headers=headers).status_code == 404

    wb = Workbook()
    ws = wb.active
    ws.append(["Balance générale 2025"])
    ws.append(["Compte", "Intitulé", "Débit", "Crédit"])
    for c, l, d, cr in BALANCE:
        ws.append([int(c), l, d or None, cr or None])
    ws.append(["Total général", None, 344_000, 344_000])
    buffer = io.BytesIO()
    wb.save(buffer)
    r = client.post(f"{base}/datasets", headers=headers, data={"domain": "comptabilite"},
                    files={"file": ("balance.xlsx", buffer.getvalue(), "application/octet-stream")})
    assert r.status_code == 201, r.text

    body = client.get(f"{base}/accounting", headers=headers).json()
    assert body["checks"] == []
    assert body["balance"]["totals"]["debit"] == body["balance"]["totals"]["credit"] == 344_000
    assert body["cpc"][-1]["label"].startswith("XIII") and body["cpc"][-1]["value"] == 0
    assert body["bilan"]["actif"][-1]["net"] == body["bilan"]["passif"][-1]["value"] == 164_000
    assert {r["key"]: r["value"] for r in body["ratios"]}["fonds_roulement"] == 45_000
