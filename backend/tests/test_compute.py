import pytest

from app.kpi.compute import Period, build_frame, compute_kpi, filter_period
from app.kpi.catalog import KPIS

from .conftest import register

ROWS = [
    {"Date": "15/01/2025", "Client": "A", "Produit": "P1", "Vendeur": "Karim", "Ville": "Rabat", "Montant": 1000.0, "Cout": 700.0, "Statut": "Réglé"},
    {"Date": "20/01/2025", "Client": "B", "Produit": "P2", "Vendeur": "Salma", "Ville": "Fès", "Montant": 500.0, "Cout": 300.0, "Statut": "Non réglé"},
    {"Date": "05/02/2025", "Client": "A", "Produit": "P1", "Vendeur": "Karim", "Ville": "Rabat", "Montant": 1500.0, "Cout": 1000.0, "Statut": "Payé"},
    {"Date": "10/03/2025", "Client": "C", "Produit": "P3", "Vendeur": "Salma", "Ville": "Rabat", "Montant": 2000.0, "Cout": 1500.0, "Statut": "Impayé"},
]
MAPPING = {"date": "Date", "client": "Client", "produit": "Produit", "commercial": "Vendeur", "region": "Ville",
           "montant_ht": "Montant", "cout_achat": "Cout", "statut_paiement": "Statut"}


@pytest.fixture
def df():
    return build_frame("commercial", ROWS, MAPPING)


def test_build_frame_types(df):
    assert str(df["date"].dtype).startswith("datetime64")
    assert df["date"].iloc[0].month == 1 and df["date"].iloc[0].day == 15
    assert df["montant_ht"].sum() == 5000


def test_sales_kpis(df):
    ca = compute_kpi("ca_total", df)
    assert ca.value == 5000
    assert ca.chart.labels == ["janv. 2025", "févr. 2025", "mars 2025"]
    assert ca.chart.values == [1500, 1500, 2000]
    assert ca.delta == pytest.approx(33.33)

    assert compute_kpi("ca_evolution", df).value == pytest.approx(33.33)
    assert compute_kpi("panier_moyen", df).value == 1250
    assert compute_kpi("nb_clients_actifs", df).value == 3
    assert compute_kpi("marge_brute", df).value == 30  # (5000 - 3500) / 5000

    impayes = compute_kpi("taux_impayes", df)
    assert impayes.value == 50  # 500 + 2000 sur 5000
    assert impayes.status == "critical"

    nouveaux = compute_kpi("nouveaux_clients", df)
    assert nouveaux.value == 1  # C, premier achat en mars
    assert nouveaux.chart.values == [2, 0, 1]

    produits = compute_kpi("top_produits", df)
    assert produits.chart.labels[0] == "P1" and produits.chart.values[0] == 2500


def test_period_filter(df):
    january = filter_period(df, Period(start=None, end=__import__("datetime").date(2025, 1, 31)))
    assert compute_kpi("ca_total", january).value == 1500


def test_missing_data_and_unsupported(df):
    assert compute_kpi("realisation_objectif", df).error == "Données manquantes"
    # Tous les KPI du catalogue ont désormais un calcul.
    from app.kpi.catalog import KPI_BY_CODE
    from app.kpi.compute import CALCULATORS
    assert set(KPI_BY_CODE) <= set(CALCULATORS)


def test_every_commercial_kpi_is_computable():
    from app.kpi.compute import CALCULATORS
    assert {k.code for k in KPIS if k.domain == "commercial"} <= set(CALCULATORS)


def test_dashboard_data_endpoint(client):
    headers, _ = register(client)
    company = client.post("/api/companies", headers=headers, json={"name": "X", "sector": "commerce", "employees": 20}).json()
    base = f"/api/companies/{company['id']}"
    csv = "Date;Client;Montant HT;Statut paiement\n15/01/2025;A;1 000,00;Réglé\n10/02/2025;B;500,00;Non réglé\n"
    client.post(f"{base}/datasets", headers=headers, data={"domain": "commercial"},
                files={"file": ("v.csv", csv.encode("utf-8"), "text/csv")})
    dash = client.post(f"{base}/dashboards", headers=headers, json={
        "domain": "commercial", "title": "Ventes", "kpi_codes": ["ca_total", "taux_impayes", "marge_brute"]}).json()

    body = client.get(f"{base}/dashboards/{dash['id']}/data", headers=headers).json()
    kpis = {k["code"]: k for k in body["kpis"]}
    assert body["data_start"] == "2025-01-15" and body["data_end"] == "2025-02-10"
    assert kpis["ca_total"]["value"] == 1500
    assert kpis["ca_total"]["chart"]["type"] == "line"
    assert kpis["taux_impayes"]["value"] == pytest.approx(33.33)
    assert kpis["marge_brute"]["error"] == "Données manquantes"

    feb = client.get(f"{base}/dashboards/{dash['id']}/data", headers=headers, params={"start": "2025-02-01"}).json()
    assert {k["code"]: k for k in feb["kpis"]}["ca_total"]["value"] == 500


def test_objective_repeated_each_month_is_cumulated():
    rows = [{"date": f"{d:02d}/{m:02d}/2026", "montant_ht": 1000, "objectif": 2000} for m in (1, 2, 3) for d in (5, 20)]
    df = build_frame("commercial", rows, {"date": "date", "montant_ht": "montant_ht", "objectif": "objectif"})
    # 6 000 de CA pour 3 mois × 2 000 d'objectif = 100 %
    assert compute_kpi("realisation_objectif", df).value == 100
