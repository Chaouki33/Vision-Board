"""Rôle administrateur, comptes créés par l'admin et mot de passe provisoire."""
from app.config import settings
from app.routers.admin import temporary_password

from .conftest import register


def login(client, email, password):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_admin_sees_all_companies(client):
    headers, _ = register(client)
    company = client.post("/api/companies", headers=headers, json={"name": "Privée", "sector": "tic", "employees": 3}).json()
    admin = client.admin_headers
    assert any(c["id"] == company["id"] for c in client.get("/api/companies", headers=admin).json())
    r = client.get(f"/api/companies/{company['id']}", headers=admin)
    assert r.status_code == 200 and r.json()["role"] == "owner"
    # L'accès administrateur ne crée pas d'adhésion en base.
    members = client.get(f"/api/companies/{company['id']}/members", headers=admin).json()
    assert [m["email"] for m in members] != [] and all(m["email"] != "admin@example.com" for m in members)


def test_non_admin_cannot_use_admin_api(client):
    headers, _ = register(client)
    assert client.get("/api/admin/users", headers=headers).status_code == 403


def test_admin_creates_user_with_temporary_password(client):
    admin = client.admin_headers
    company = client.post("/api/companies", headers=admin, json={"name": "Cliente", "sector": "commerce", "employees": 12}).json()
    r = client.post("/api/admin/users", headers=admin, json={
        "email": "Comptable@Example.com", "full_name": "Sara Comptable",
        "companies": [{"company_id": company["id"], "role": "editor"}]})
    assert r.status_code == 201, r.text
    body = r.json()
    password = body["temporary_password"]
    assert len(password) == 19 and body["user"]["must_change_password"]
    assert body["user"]["companies"] == [{"company_id": company["id"], "name": "Cliente", "role": "editor"}]

    # Première connexion : changement de mot de passe obligatoire.
    token = login(client, "comptable@example.com", password).json()
    assert token["user"]["must_change_password"] is True
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    assert client.post("/api/auth/password", headers=headers,
                       json={"current_password": "faux", "new_password": "nouveau-mdp-2026"}).status_code == 400
    r = client.post("/api/auth/password", headers=headers,
                    json={"current_password": password, "new_password": "nouveau-mdp-2026"})
    assert r.status_code == 200 and r.json()["must_change_password"] is False
    assert login(client, "comptable@example.com", "nouveau-mdp-2026").status_code == 200

    # L'utilisateur ne voit que la société attribuée.
    assert [c["name"] for c in client.get("/api/companies", headers=headers).json()] == ["Cliente"]


def test_deactivate_and_reset(client):
    admin = client.admin_headers
    created = client.post("/api/admin/users", headers=admin, json={
        "email": "stagiaire@example.com", "full_name": "Stagiaire", "password": "provisoire-123"}).json()
    user_id = created["user"]["id"]
    token = login(client, "stagiaire@example.com", "provisoire-123").json()["access_token"]

    client.patch(f"/api/admin/users/{user_id}", headers=admin, json={"is_active": False})
    assert login(client, "stagiaire@example.com", "provisoire-123").status_code == 403
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401

    client.patch(f"/api/admin/users/{user_id}", headers=admin, json={"is_active": True})
    new_password = client.post(f"/api/admin/users/{user_id}/reset-password", headers=admin).json()["temporary_password"]
    assert login(client, "stagiaire@example.com", "provisoire-123").status_code == 401
    assert login(client, "stagiaire@example.com", new_password).json()["user"]["must_change_password"] is True

    assert client.delete(f"/api/admin/users/{user_id}", headers=admin).status_code == 204


def test_last_admin_is_protected(client):
    admin = client.admin_headers
    me = client.get("/api/auth/me", headers=admin).json()
    others = [u for u in client.get("/api/admin/users", headers=admin).json() if u["is_admin"] and u["id"] != me["id"]]
    if not others:
        r = client.patch(f"/api/admin/users/{me['id']}", headers=admin, json={"is_admin": False})
        assert r.status_code == 400
    assert client.delete(f"/api/admin/users/{me['id']}", headers=admin).status_code == 400


def test_registration_can_be_closed(client, monkeypatch):
    monkeypatch.setattr(settings, "allow_registration", False)
    assert client.get("/api/auth/config").json() == {"registration_open": False, "first_install": False}
    r = client.post("/api/auth/register", json={"email": "x@example.com", "full_name": "X Y", "password": "motdepasse123"})
    assert r.status_code == 403


def test_temporary_password_format():
    password = temporary_password()
    assert len(password.split("-")) == 4 and not set(password) & set("0O1lI")


def test_login_tolerates_pasted_whitespace(client):
    admin = client.admin_headers
    client.post("/api/admin/users", headers=admin, json={
        "email": "colle@example.com", "full_name": "Copier Coller", "password": "Abcd-Efgh-Jkmn-Pqrs"})
    assert login(client, "colle@example.com", "Abcd-Efgh-Jkmn-Pqrs " + chr(10)).status_code == 200
    assert login(client, "colle@example.com", "Abcd-Efgh-Jkmn").status_code == 401


def test_self_registered_user_is_not_admin(client, monkeypatch):
    monkeypatch.setattr(settings, "allow_registration", True)
    assert client.get("/api/auth/config").json()["registration_open"] is True
    _, user = register(client)
    assert user["is_admin"] is False


def test_admin_lists_and_deletes_companies(client):
    admin = client.admin_headers
    headers, _ = register(client)
    a = client.post("/api/companies", headers=headers, json={"name": "À supprimer 1", "sector": "commerce",
                                                             "domains": ["commercial"]}).json()
    b = client.post("/api/companies", headers=headers, json={"name": "À supprimer 2", "sector": "tic"}).json()
    listing = {c["id"]: c for c in client.get("/api/admin/companies", headers=admin).json()}
    assert listing[a["id"]]["dashboards"] == 1 and listing[a["id"]]["members"] == 1

    # Un utilisateur simple ne peut pas utiliser cette fonction.
    assert client.post("/api/admin/companies/delete", headers=headers, json={"ids": [a["id"]]}).status_code == 403

    r = client.post("/api/admin/companies/delete", headers=admin, json={"ids": [a["id"], b["id"]]})
    assert r.status_code == 200 and r.json()["deleted"] == 2
    assert client.get(f"/api/companies/{a['id']}", headers=headers).status_code == 404
    assert client.get("/api/companies", headers=headers).json() == []
    assert client.post("/api/admin/companies/delete", headers=admin, json={"ids": [a["id"]]}).status_code == 404


def test_admin_can_delete_any_company_directly(client):
    headers, _ = register(client)
    company = client.post("/api/companies", headers=headers, json={"name": "Privée", "sector": "btp"}).json()
    assert client.delete(f"/api/companies/{company['id']}", headers=client.admin_headers).status_code == 204
