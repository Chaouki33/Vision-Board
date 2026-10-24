import io

from openpyxl import Workbook

from app.importers.tabular import parse_file
from app.kpi.recommender import recommend

from .conftest import register

SALES_CSV = """Rapport des ventes 2025;;;;;
;;;;;
Date facture;Client;Article;Commercial;Montant HT (MAD);Coût
15/01/2025;Marjane;Huile 5L;Karim;1 250,50;900
20/01/2025;Label'Vie;Sucre 2kg;Salma;3 400,00 DH;2 800
03/02/2025;Marjane;Thé 500g;Karim;780,25;500
""".encode("cp1252")


# ---------------------------------------------------------------- Authentification
def test_register_login_me(client):
    headers, user = register(client)
    assert client.get("/api/auth/me", headers=headers).json()["email"] == user["email"]
    r = client.post("/api/auth/login", json={"email": user["email"], "password": "motdepasse123"})
    assert r.status_code == 200
    assert client.post("/api/auth/login", json={"email": user["email"], "password": "faux"}).status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_duplicate_email(client):
    _, user = register(client)
    r = client.post("/api/auth/register", json={"email": user["email"], "full_name": "X Y", "password": "motdepasse123"})
    assert r.status_code == 409


# ---------------------------------------------------------------- Sociétés et droits
def test_company_size_is_derived(client, auth):
    r = client.post("/api/companies", headers=auth, json={"name": "Petite", "sector": "services", "employees": 4})
    assert r.json()["size"] == "tpe"
    r = client.post("/api/companies", headers=auth, json={"name": "Grande", "sector": "industrie", "employees": 900})
    assert r.json()["size"] == "ge"
    assert client.post("/api/companies", headers=auth, json={"name": "X", "sector": "inconnu"}).status_code == 422


def test_companies_are_isolated_between_users(client, company):
    other, _ = register(client)
    assert client.get(f"/api/companies/{company['id']}", headers=other).status_code == 404
    assert all(c["id"] != company["id"] for c in client.get("/api/companies", headers=other).json())


def test_members_and_roles(client, auth, company):
    viewer_headers, viewer = register(client)
    r = client.post(f"/api/companies/{company['id']}/members", headers=auth,
                    json={"email": viewer["email"], "role": "viewer"})
    assert r.status_code == 201
    cid = company["id"]
    assert client.get(f"/api/companies/{cid}", headers=viewer_headers).json()["role"] == "viewer"
    # Un lecteur ne peut ni modifier la société ni importer de fichier.
    assert client.put(f"/api/companies/{cid}", headers=viewer_headers,
                      json={"name": "Piratée", "sector": "commerce"}).status_code == 403
    r = client.post(f"/api/companies/{cid}/datasets", headers=viewer_headers, data={"domain": "commercial"},
                    files={"file": ("ventes.csv", SALES_CSV, "text/csv")})
    assert r.status_code == 403
    # Le dernier propriétaire ne peut pas être retiré.
    me = client.get("/api/auth/me", headers=auth).json()
    assert client.delete(f"/api/companies/{cid}/members/{me['id']}", headers=auth).status_code == 400


# ---------------------------------------------------------------- Import de fichiers
def test_parse_french_csv():
    table = parse_file("ventes.csv", SALES_CSV)
    assert table.columns == ["Date facture", "Client", "Article", "Commercial", "Montant HT (MAD)", "Coût"]
    assert len(table.rows) == 3
    assert table.rows[0]["Montant HT (MAD)"] == 1250.5
    assert table.rows[1]["Montant HT (MAD)"] == 3400.0
    assert table.rows[1]["Client"] == "Label'Vie"


def test_upload_csv_suggests_mapping(client, auth, company):
    r = client.post(f"/api/companies/{company['id']}/datasets", headers=auth, data={"domain": "commercial"},
                    files={"file": ("ventes.csv", SALES_CSV, "text/csv")})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["row_count"] == 3
    assert body["mapping"] == {
        "date": "Date facture", "client": "Client", "produit": "Article", "commercial": "Commercial",
        "montant_ht": "Montant HT (MAD)", "cout_achat": "Coût",
    }

    # Correction manuelle du mapping, avec validation.
    url = f"/api/companies/{company['id']}/datasets/{body['id']}"
    bad = client.patch(url, headers=auth, json={"mapping": {"date": "Colonne inexistante"}})
    assert bad.status_code == 422
    ok = client.patch(url, headers=auth, json={"mapping": {"date": "Date facture", "montant_ht": "Montant HT (MAD)"}})
    assert ok.json()["mapping"] == {"date": "Date facture", "montant_ht": "Montant HT (MAD)"}


def test_upload_excel_with_title_rows(client, auth, company):
    wb = Workbook()
    ws = wb.active
    ws.title = "Personnel"
    ws.append(["Liste du personnel au 30/09/2025"])
    ws.append([])
    ws.append(["Matricule", "Nom et prénom", "Service", "Type de contrat", "Date d'entrée", "Salaire brut"])
    ws.append(["M001", "Amina Alaoui", "Comptabilité", "CDI", "2019-03-01", 9500])
    ws.append(["M002", "Youssef Benali", "Commercial", "Stage", "2025-07-01", 2000])
    buffer = io.BytesIO()
    wb.save(buffer)

    r = client.post(f"/api/companies/{company['id']}/datasets", headers=auth, data={"domain": "rh"},
                    files={"file": ("personnel.xlsx", buffer.getvalue(), "application/octet-stream")})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["sheets"] == ["Personnel"]
    assert body["row_count"] == 2
    assert body["mapping"]["salaire_brut"] == "Salaire brut"
    assert body["mapping"]["type_contrat"] == "Type de contrat"
    assert body["mapping"]["departement"] == "Service"
    assert body["mapping"]["date_embauche"] == "Date d'entrée"


def test_upload_rejects_unknown_format(client, auth, company):
    r = client.post(f"/api/companies/{company['id']}/datasets", headers=auth, data={"domain": "commercial"},
                    files={"file": ("photo.png", b"xx", "image/png")})
    assert r.status_code == 422


# ---------------------------------------------------------------- Recommandation des KPI
def test_recommendations_depend_on_size_and_sector():
    tpe = recommend("commercial", "commerce", "tpe", {})
    ge = recommend("commercial", "commerce", "ge", {})
    assert sum(r.selected for r in tpe) <= 8
    assert sum(r.selected for r in ge) > sum(r.selected for r in tpe)
    assert "ca_par_commercial" not in {r.kpi.code for r in tpe}
    # Le panier moyen est essentiel pour le commerce, pas pour l'industrie.
    assert next(r for r in tpe if r.kpi.code == "panier_moyen").priority == 1
    assert next(r for r in recommend("commercial", "industrie", "tpe", {}) if r.kpi.code == "panier_moyen").priority == 2
    # Pas de KPI de production pour une société de services.
    assert recommend("production", "services", "pme", {}) == []


def test_recommendations_use_imported_data(client, auth, company):
    cid = company["id"]
    r = client.get(f"/api/companies/{cid}/recommendations", params={"domain": "commercial"}, headers=auth)
    assert all(not k["available"] for k in r.json()["kpis"])

    client.post(f"/api/companies/{cid}/datasets", headers=auth, data={"domain": "commercial"},
                files={"file": ("ventes.csv", SALES_CSV, "text/csv")})
    body = client.get(f"/api/companies/{cid}/recommendations", params={"domain": "commercial"}, headers=auth).json()
    kpis = {k["code"]: k for k in body["kpis"]}
    assert kpis["ca_total"]["available"] and kpis["marge_brute"]["available"]
    assert not kpis["taux_impayes"]["available"]
    assert kpis["taux_impayes"]["missing_fields"] == ["statut_paiement"]
    assert "production" not in body["suggested_domains"]


def test_save_dashboard(client, auth, company):
    url = f"/api/companies/{company['id']}/dashboards"
    r = client.post(url, headers=auth, json={"domain": "commercial", "title": "Ventes", "kpi_codes": ["ca_total", "marge_brute"]})
    assert r.status_code == 201
    bad = client.post(url, headers=auth, json={"domain": "commercial", "title": "X", "kpi_codes": ["taux_rebut"]})
    assert bad.status_code == 422
    assert [d["title"] for d in client.get(url, headers=auth).json()] == ["Ventes"]


# ---------------------------------------------------------------- Tableaux de bord choisis à la création
def test_company_created_with_several_dashboards(client, auth):
    r = client.post("/api/companies", headers=auth, json={
        "name": "Multi", "sector": "commerce", "employees": 30, "domains": ["commercial", "rh", "tresorerie"]})
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    dashboards = client.get(f"/api/companies/{cid}/dashboards", headers=auth).json()
    assert sorted(d["domain"] for d in dashboards) == ["commercial", "rh", "tresorerie"]
    assert all(d["kpi_codes"] for d in dashboards)
    # Un type inconnu est refusé.
    bad = client.post("/api/companies", headers=auth, json={"name": "X", "sector": "commerce", "domains": ["magie"]})
    assert bad.status_code == 422


def test_bulk_dashboards_skip_existing(client, auth, company):
    url = f"/api/companies/{company['id']}/dashboards/bulk"
    first = client.post(url, headers=auth, json={"domains": ["commercial", "stock"]}).json()
    assert [d["domain"] for d in first] == ["commercial", "stock"]
    again = client.post(url, headers=auth, json={"domains": ["commercial", "rh"]}).json()
    assert [d["domain"] for d in again] == ["rh"]
    meta = client.get("/api/meta").json()
    assert "production" not in meta["sector_domains"]["commerce"]
