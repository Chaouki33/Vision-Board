import os
import tempfile

import pytest

# Base de test isolée, définie avant l'import de l'application.
_tmp = tempfile.mkdtemp()
os.environ["VISIONBOARD_DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
# Les tests créent librement leurs comptes ; la fermeture des inscriptions est testée à part.
os.environ["VISIONBOARD_ALLOW_REGISTRATION"] = "true"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    test_client = TestClient(app)
    # Le premier compte devient administrateur : on le crée d'emblée pour que les comptes
    # des autres tests soient de simples utilisateurs.
    r = test_client.post("/api/auth/register", json={
        "email": "admin@example.com", "full_name": "Admin Test", "password": "motdepasse123"})
    assert r.status_code == 201 and r.json()["user"]["is_admin"], r.text
    test_client.admin_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    return test_client


_counter = 0


def register(client, name="Test"):
    global _counter
    _counter += 1
    r = client.post("/api/auth/register", json={
        "email": f"user{_counter}@example.com", "full_name": f"{name} {_counter}", "password": "motdepasse123",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, r.json()["user"]


@pytest.fixture
def auth(client):
    headers, _ = register(client)
    return headers


@pytest.fixture
def company(client, auth):
    r = client.post("/api/companies", headers=auth, json={"name": "Atlas Distribution", "sector": "commerce", "employees": 45})
    assert r.status_code == 201, r.text
    return r.json()
