"""Calculs des modules Production, Stock, RH et Trésorerie."""
from pathlib import Path

import pandas as pd
import pytest

from app.importers.mapping import suggest_mapping
from app.importers.tabular import parse_file
from app.kpi.calc import commercial, rh, stock
from app.kpi.catalog import KPIS
from app.kpi.compute import CALCULATORS, build_frame, compute_kpi

EXEMPLES = Path(__file__).resolve().parents[2] / "exemples"
REFERENCE_DAY = pd.Timestamp("2026-10-01")


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    for module in (commercial, rh, stock):
        monkeypatch.setattr(module, "today", lambda: REFERENCE_DAY)


def frame(domain, rows):
    return build_frame(domain, rows, {k: k for k in rows[0]})


def test_all_operational_kpis_are_computable():
    domains = {"commercial", "production", "stock", "rh", "tresorerie"}
    assert {k.code for k in KPIS if k.domain in domains} <= set(CALCULATORS)


from app.demo import COMPANIES, company_files  # noqa: E402

# Tous les fichiers d'exemple des 12 sociétés (une par secteur).
SAMPLES = [(domain, f"{folder}/{path.name}") for folder, *_ in COMPANIES for domain, path in company_files(folder)]


@pytest.mark.parametrize("domain,filename", SAMPLES)
def test_sample_files_end_to_end(domain, filename):
    table = parse_file(filename.rsplit("/", 1)[-1], (EXEMPLES / filename).read_bytes())
    mapping = suggest_mapping(domain, table.columns, table.rows)
    # Toutes les colonnes utiles sont reconnues ; seul le n° de facture n'alimente aucun KPI.
    unmapped = set(table.columns) - set(mapping.values())
    assert unmapped <= {"N° facture"}, f"colonnes non reconnues : {unmapped}"
    df = build_frame(domain, table.rows, mapping)
    for kpi in (k for k in KPIS if k.domain == domain):
        result = compute_kpi(kpi.code, df)
        if set(kpi.required) <= set(df.columns):
            assert result.error is None, f"{kpi.code} : {result.error}"
            assert result.value is not None, kpi.code


# ---------------------------------------------------------------- Production
def test_production_rates():
    df = frame("production", [
        {"ligne": "A", "quantite_produite": 900, "quantite_rebut": 100, "objectif": 1000,
         "temps_planifie": 10, "temps_arret": 2, "cadence_theorique": 150},
        {"ligne": "B", "quantite_produite": 500, "quantite_rebut": 0, "objectif": 500,
         "temps_planifie": 10, "temps_arret": 0, "cadence_theorique": 100},
    ])
    assert compute_kpi("taux_rebut", df).value == pytest.approx(100 / 1500 * 100, abs=0.01)
    assert compute_kpi("realisation_production", df).value == pytest.approx(93.33, abs=0.01)
    assert compute_kpi("taux_disponibilite", df).value == 90
    # Disponibilité 18/20 × performance 1500/(150×8 + 100×10) × qualité 1400/1500
    trs = compute_kpi("trs", df)
    assert trs.value == pytest.approx(100 * 0.9 * (1500 / 2200) * (1400 / 1500), abs=0.01)
    assert trs.chart.labels == ["A", "B"]


# ---------------------------------------------------------------- Stock
def test_stock_uses_latest_inventory():
    df = frame("stock", [
        {"date": "2026-08-31", "article": "X", "quantite_stock": 100, "cout_unitaire": 10, "stock_minimum": 20, "sorties": 50},
        {"date": "2026-09-30", "article": "X", "quantite_stock": 10, "cout_unitaire": 10, "stock_minimum": 20, "sorties": 90},
        {"date": "2026-09-30", "article": "Y", "quantite_stock": 0, "cout_unitaire": 5, "stock_minimum": 1, "sorties": 0},
    ])
    assert compute_kpi("valeur_stock", df).value == 100  # 10 × 10 au dernier inventaire
    assert compute_kpi("articles_sous_seuil", df).value == 2
    assert compute_kpi("taux_rupture", df).value == 50
    assert compute_kpi("stock_dormant", df).value == 0  # Y n'a pas de stock


def test_peremption():
    df = frame("stock", [
        {"article": "A", "date_peremption": "2026-10-15"},
        {"article": "B", "date_peremption": "2026-09-20"},
        {"article": "C", "date_peremption": "2027-03-01"},
    ])
    result = compute_kpi("proches_peremption", df)
    assert result.value == 1 and result.detail == "1 articles déjà périmés"


# ---------------------------------------------------------------- RH
def test_rh_headcount_interns_and_turnover():
    df = frame("rh", [
        {"nom": "A", "type_contrat": "CDI", "date_embauche": "2020-01-01", "date_sortie": None, "salaire_brut": 10000},
        {"nom": "B", "type_contrat": "Stagiaire PFE", "date_embauche": "2026-07-01", "date_sortie": None, "salaire_brut": 2000},
        {"nom": "C", "type_contrat": "CDD", "date_embauche": "2019-05-01", "date_sortie": "2026-03-31", "salaire_brut": 8000},
        {"nom": "D", "type_contrat": "CDI", "date_embauche": "2018-05-01", "date_sortie": None, "salaire_brut": 12000},
    ])
    assert compute_kpi("effectif_total", df).value == 3
    assert compute_kpi("nb_stagiaires", df).value == 1
    assert compute_kpi("masse_salariale", df).value == 24000
    assert compute_kpi("recrutements", df).value == 1
    # 1 entrée + 1 sortie sur 12 mois ; effectif 3 au début et 3 à la fin.
    assert compute_kpi("turnover", df).value == pytest.approx(33.33, abs=0.01)


# ---------------------------------------------------------------- Trésorerie
def test_treasury_balances_and_negative_debits():
    df = frame("tresorerie", [
        {"date": "2026-01-10", "banque": "A", "encaissement": 1000, "decaissement": None, "solde": 5000},
        {"date": "2026-01-20", "banque": "B", "encaissement": None, "decaissement": -400, "solde": 2000},
        {"date": "2026-02-05", "banque": "A", "encaissement": None, "decaissement": -600, "solde": 4400},
    ])
    assert compute_kpi("solde_tresorerie", df).value == 6400  # 4400 (A) + 2000 (B)
    assert compute_kpi("flux_net", df).value == 0
    assert compute_kpi("decaissements_mensuels_moyens", df).value == 500
    assert compute_kpi("autonomie_tresorerie", df).value == pytest.approx(12.8)


@pytest.mark.parametrize("domain,filename", SAMPLES)
def test_free_report_on_every_sample(domain, filename):
    """Le moteur gratuit produit un rapport complet et cohérent pour chaque fichier d'exemple."""
    from app.kpi.catalog import KPI_BY_CODE
    from app.reports.rules import write_rules_report
    from app.reports.writer import ASSESSMENTS, REPORT_SCHEMA
    from app.schemas import DashboardDataOut, KpiValueOut, ChartOut
    from dataclasses import asdict

    table = parse_file(filename.rsplit("/", 1)[-1], (EXEMPLES / filename).read_bytes())
    df = build_frame(domain, table.rows, suggest_mapping(domain, table.columns, table.rows))
    kpis = []
    for kpi in (k for k in KPIS if k.domain == domain):
        r = compute_kpi(kpi.code, df)
        kpis.append(KpiValueOut(code=kpi.code, name=kpi.name, description=kpi.description, formula=kpi.formula,
                                unit=kpi.unit, higher_is_better=kpi.higher_is_better, value=r.value, status=r.status,
                                detail=r.detail, delta=r.delta, error=r.error, rows=r.rows,
                                chart=ChartOut(**asdict(r.chart)) if r.chart else None))
    data = DashboardDataOut(id=1, title="Test", domain=domain, start=None, end=None, data_start=None, data_end=None,
                            kpis=kpis)
    content = write_rules_report("Société test", data, "sur l'ensemble des données disponibles")
    assert set(content) == set(REPORT_SCHEMA["required"])
    assert content["appreciation_globale"] in ASSESSMENTS
    assert content["sections"] and all(s["paragraphes"] for s in content["sections"])
    assert content["recommandations"]
    assert content["titre"].endswith("— Société test") and not content["titre"].startswith(("Activité", "Équilibre"))
    text = " ".join(p for s in content["sections"] for p in s["paragraphes"])
    assert "None" not in text and "nan" not in text.lower().split()
