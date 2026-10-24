"""Rapports d'analyse : appel à Claude (simulé), déroulé par l'API et exports."""
import io
import json
from types import SimpleNamespace

import anthropic
import pytest
from docx import Document

from app.config import settings
from app.reports import writer

from .conftest import register

SAMPLE_REPORT = {
    "titre": "Analyse commerciale — 1er trimestre 2025",
    "appreciation_globale": "à surveiller",
    "synthese": "Le chiffre d'affaires atteint 1 500 MAD. Le taux d'impayés de 33,3 % est critique.",
    "chiffres_cles": [{"indicateur": "Chiffre d'affaires HT", "valeur": "1 500 MAD", "commentaire": "Activité modeste."}],
    "sections": [{"titre": "Encaissements", "paragraphes": ["Un tiers des ventes n'est pas réglé − relance nécessaire."]}],
    "points_forts": ["Clientèle fidèle"],
    "points_de_vigilance": ["Impayés élevés"],
    "recommandations": [{"priorite": "haute", "action": "Relancer les clients débiteurs",
                         "justification": "Réduire le besoin de trésorerie.", "horizon": "immédiat"}],
    "limites_des_donnees": ["Pas de coût d'achat : marge non calculable"],
    "conclusion": "Priorité au recouvrement.",
}


def fake_response(stop_reason="end_turn", text=json.dumps(SAMPLE_REPORT)):
    return SimpleNamespace(
        stop_reason=stop_reason, model="claude-opus-5-5",
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
        usage=SimpleNamespace(input_tokens=1200, output_tokens=900),
    )


class FakeClient:
    def __init__(self, response=None, error=None):
        self.calls = []
        self._response, self._error = response, error
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self._error:
            raise self._error
        return self._response


# ---------------------------------------------------------------- Appel à Claude
def test_call_claude_request_and_parsing(monkeypatch):
    client = FakeClient(fake_response())
    monkeypatch.setattr(writer, "_client", lambda: client)
    result = writer.call_claude({"indicateurs": [{"indicateur": "CA", "valeur": "1 500 MAD"}]}, "Focus sur les impayés")

    assert result.content == SAMPLE_REPORT
    assert (result.input_tokens, result.output_tokens) == (1200, 900)
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default" and call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call["output_config"]["format"]["schema"] is writer.REPORT_SCHEMA
    prompt = call["messages"][0]["content"]
    assert "1 500 MAD" in prompt and "Focus sur les impayés" in prompt


@pytest.mark.parametrize("response,message", [
    (fake_response(stop_reason="refusal"), "refusé"),
    (fake_response(stop_reason="max_tokens"), "longueur maximale"),
    (fake_response(text="pas du json"), "illisible"),
])
def test_call_claude_bad_responses(monkeypatch, response, message):
    monkeypatch.setattr(writer, "_client", lambda: FakeClient(response))
    with pytest.raises(writer.ReportError, match=message):
        writer.call_claude({}, None)


def test_call_claude_connection_error(monkeypatch):
    error = anthropic.APIConnectionError(request=SimpleNamespace(method="POST", url="https://api.anthropic.com"))
    monkeypatch.setattr(writer, "_client", lambda: FakeClient(error=error))
    with pytest.raises(writer.ReportError, match="joindre l'API Claude"):
        writer.call_claude({}, None)


def test_call_claude_without_credentials(monkeypatch):
    error = TypeError("Could not resolve authentication method. Expected one of api_key, auth_token, or credentials")
    monkeypatch.setattr(writer, "_client", lambda: FakeClient(error=error))
    with pytest.raises(writer.ReportError, match="VISIONBOARD_ANTHROPIC_API_KEY"):
        writer.call_claude({}, None)


# ---------------------------------------------------------------- Déroulé complet
@pytest.fixture
def dashboard(client):
    headers, _ = register(client)
    company = client.post("/api/companies", headers=headers,
                          json={"name": "Atlas & Fils", "sector": "commerce", "employees": 20}).json()
    base = f"/api/companies/{company['id']}"
    csv = "Date;Client;Montant HT;Statut paiement\n15/01/2025;A;1 000,00;Réglé\n10/02/2025;B;500,00;Non réglé\n"
    client.post(f"{base}/datasets", headers=headers, data={"domain": "commercial"},
                files={"file": ("v.csv", csv.encode("utf-8"), "text/csv")})
    dash = client.post(f"{base}/dashboards", headers=headers, json={
        "domain": "commercial", "title": "Ventes", "kpi_codes": ["ca_total", "taux_impayes", "marge_brute"]}).json()
    return headers, base, dash


def test_report_lifecycle_and_exports(client, dashboard, monkeypatch):
    monkeypatch.setattr(settings, "report_engine", "claude")
    headers, base, dash = dashboard
    seen = {}

    def fake_call(context, instructions):
        seen["context"], seen["instructions"] = context, instructions
        return writer.WrittenReport(SAMPLE_REPORT, "claude-opus-5-5", 1200, 900)

    monkeypatch.setattr(writer, "call_claude", fake_call)
    r = client.post(f"{base}/dashboards/{dash['id']}/reports", headers=headers, json={"instructions": "Focus impayés"})
    assert r.status_code == 202, r.text
    report_id = r.json()["id"]

    # Le contexte contient les chiffres calculés et signale les données manquantes.
    indicators = {i["indicateur"]: i for i in seen["context"]["indicateurs"]}
    assert indicators["Chiffre d'affaires HT"]["valeur"] == "1 500 MAD"
    assert indicators["Taux d'impayés"]["statut"] == "Critique"
    assert seen["context"]["indicateurs_non_calcules"][0]["indicateur"] == "Taux de marge brute"
    assert seen["context"]["societe"]["nom"] == "Atlas & Fils"
    assert seen["instructions"] == "Focus impayés"

    report = client.get(f"{base}/reports/{report_id}", headers=headers).json()
    assert report["status"] == "done"
    assert report["title"] == SAMPLE_REPORT["titre"]
    assert [x["id"] for x in client.get(f"{base}/reports", headers=headers).json()] == [report_id]

    pdf = client.get(f"{base}/reports/{report_id}/export", headers=headers, params={"format": "pdf"})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert "attachment" in pdf.headers["content-disposition"]

    docx = client.get(f"{base}/reports/{report_id}/export", headers=headers, params={"format": "docx"})
    assert docx.status_code == 200
    text = "\n".join(p.text for p in Document(io.BytesIO(docx.content)).paragraphs)
    assert SAMPLE_REPORT["titre"] in text and "Relancer les clients débiteurs" in text

    assert client.delete(f"{base}/reports/{report_id}", headers=headers).status_code == 204


def test_report_error_is_stored(client, dashboard, monkeypatch):
    monkeypatch.setattr(settings, "report_engine", "claude")
    headers, base, dash = dashboard

    def failing(context, instructions):
        raise writer.ReportError("Clé API Claude absente ou invalide")

    monkeypatch.setattr(writer, "call_claude", failing)
    report_id = client.post(f"{base}/dashboards/{dash['id']}/reports", headers=headers, json={}).json()["id"]
    report = client.get(f"{base}/reports/{report_id}", headers=headers).json()
    assert report["status"] == "error" and "Clé API" in report["error"]
    assert client.get(f"{base}/reports/{report_id}/export", headers=headers).status_code == 409


def test_viewer_cannot_generate(client, dashboard):
    headers, base, dash = dashboard
    viewer_headers, viewer = register(client)
    client.post(f"{base}/members", headers=headers, json={"email": viewer["email"], "role": "viewer"})
    r = client.post(f"{base}/dashboards/{dash['id']}/reports", headers=viewer_headers, json={})
    assert r.status_code == 403


# ---------------------------------------------------------------- Mode gratuit (analyse par règles)
def test_engine_selection(monkeypatch):
    monkeypatch.setattr(settings, "report_engine", "auto")
    monkeypatch.setattr(settings, "anthropic_api_key", None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert writer.report_engine() == "regles"
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-test")
    assert writer.report_engine() == "claude"
    monkeypatch.setattr(settings, "report_engine", "regles")
    assert writer.report_engine() == "regles"


def test_free_report_is_immediate(client, dashboard, monkeypatch):
    monkeypatch.setattr(settings, "report_engine", "regles")
    headers, base, dash = dashboard
    assert client.get(f"{base}/reports-config", headers=headers).json()["engine"] == "regles"
    r = client.post(f"{base}/dashboards/{dash['id']}/reports", headers=headers, json={})
    assert r.status_code == 202
    report = r.json()
    assert report["status"] == "done" and report["model"].startswith("Vision Board")
    c = report["content"]
    assert set(c) == set(writer.REPORT_SCHEMA["required"])
    assert c["appreciation_globale"] in writer.ASSESSMENTS
    # Le taux d'impayés est critique : recommandation de recouvrement en priorité haute.
    assert any(rec["priorite"] == "haute" and "recouvrement" in rec["action"] for rec in c["recommandations"])
    # La marge ne peut pas être calculée : les limites le signalent.
    assert any("marge" in lim.lower() for lim in c["limites_des_donnees"])
    pdf = client.get(f"{base}/reports/{report['id']}/export", headers=headers, params={"format": "pdf"})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
