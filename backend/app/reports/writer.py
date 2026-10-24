"""Rédaction du rapport d'analyse par Claude.

Le modèle reçoit les indicateurs déjà calculés et renvoie un rapport structuré (JSON validé
par un schéma), ce qui garantit un rendu identique à l'écran, en PDF et en Word.
"""
import json
import os
from dataclasses import dataclass

import anthropic

from ..config import settings

SYSTEM_PROMPT = """Tu es un analyste financier et contrôleur de gestion senior, spécialiste des PME et grandes entreprises marocaines. Tu rédiges, en français professionnel, des rapports d'analyse destinés aux dirigeants pour éclairer leurs décisions.

Règles de rédaction :
- Appuie-toi exclusivement sur les données fournies. N'invente aucun chiffre et n'en recalcule pas d'autres que de simples écarts ou rapports évidents ; cite les valeurs telles qu'elles sont données.
- Interprète : explique ce que signifient les chiffres pour l'entreprise, compte tenu de son secteur et de sa taille, et relie les indicateurs entre eux (causes probables, effets).
- Signale clairement les indicateurs en alerte et les données manquantes, et dis quand une conclusion reste incertaine faute de données.
- Formule des recommandations concrètes, priorisées et réalistes pour une entreprise de cette taille au Maroc (montants en MAD).
- Style sobre et direct, sans jargon inutile ni formules creuses. Pas de Markdown dans les textes : uniquement des phrases et paragraphes.
- Si l'utilisateur précise des points à approfondir, traite-les en priorité."""

PRIORITIES = ["haute", "moyenne", "basse"]
HORIZONS = ["immédiat", "moins de 3 mois", "3 à 12 mois"]
ASSESSMENTS = ["favorable", "à surveiller", "préoccupante"]

REPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "titre": {"type": "string", "description": "Titre du rapport"},
        "appreciation_globale": {"type": "string", "enum": ASSESSMENTS},
        "synthese": {"type": "string", "description": "Synthèse pour le dirigeant, 5 à 8 phrases"},
        "chiffres_cles": {
            "type": "array",
            "description": "3 à 6 indicateurs les plus parlants",
            "items": {
                "type": "object",
                "properties": {
                    "indicateur": {"type": "string"},
                    "valeur": {"type": "string", "description": "Valeur exactement comme fournie"},
                    "commentaire": {"type": "string", "description": "Une phrase d'interprétation"},
                },
                "required": ["indicateur", "valeur", "commentaire"],
                "additionalProperties": False,
            },
        },
        "sections": {
            "type": "array",
            "description": "Analyse détaillée par thème, 3 à 6 sections",
            "items": {
                "type": "object",
                "properties": {
                    "titre": {"type": "string"},
                    "paragraphes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["titre", "paragraphes"],
                "additionalProperties": False,
            },
        },
        "points_forts": {"type": "array", "items": {"type": "string"}},
        "points_de_vigilance": {"type": "array", "items": {"type": "string"}},
        "recommandations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "priorite": {"type": "string", "enum": PRIORITIES},
                    "action": {"type": "string"},
                    "justification": {"type": "string"},
                    "horizon": {"type": "string", "enum": HORIZONS},
                },
                "required": ["priorite", "action", "justification", "horizon"],
                "additionalProperties": False,
            },
        },
        "limites_des_donnees": {"type": "array", "items": {"type": "string"}},
        "conclusion": {"type": "string"},
    },
    "required": ["titre", "appreciation_globale", "synthese", "chiffres_cles", "sections", "points_forts",
                 "points_de_vigilance", "recommandations", "limites_des_donnees", "conclusion"],
    "additionalProperties": False,
}


MISSING_KEY = ("Clé API Claude absente ou invalide : renseignez VISIONBOARD_ANTHROPIC_API_KEY dans le fichier "
               "backend/.env, puis redémarrez le serveur")


class ReportError(Exception):
    """Erreur présentée telle quelle à l'utilisateur."""


@dataclass
class WrittenReport:
    content: dict
    model: str
    input_tokens: int
    output_tokens: int


def build_prompt(context: dict, instructions: str | None) -> str:
    text = (
        "Rédige le rapport d'analyse du tableau de bord ci-dessous.\n\n"
        f"<donnees>\n{json.dumps(context, ensure_ascii=False, indent=1)}\n</donnees>"
    )
    if instructions:
        text += f"\n\nPoints que le dirigeant souhaite voir approfondis :\n<demande>\n{instructions}\n</demande>"
    return text


def claude_available() -> bool:
    return bool((settings.anthropic_api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY"))


def report_engine() -> str:
    """« claude » ou « regles » selon la configuration et la présence d'une clé API."""
    if settings.report_engine in ("claude", "regles"):
        return settings.report_engine
    return "claude" if claude_available() else "regles"


def _client() -> anthropic.Anthropic:
    if settings.anthropic_api_key:
        return anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return anthropic.Anthropic()


def call_claude(context: dict, instructions: str | None) -> WrittenReport:
    try:
        client = _client()
        response = client.beta.messages.create(
            model=settings.report_model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_prompt(context, instructions)}],
            output_config={"effort": settings.report_effort, "format": {"type": "json_schema", "schema": REPORT_SCHEMA}},
            # En cas de refus par les filtres de sécurité, l'API relance la demande sur le modèle recommandé.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except (anthropic.AuthenticationError, anthropic.CredentialsError) as exc:
        raise ReportError(MISSING_KEY) from exc
    except anthropic.PermissionDeniedError as exc:
        raise ReportError("La clé API Claude n'a pas accès à ce modèle") from exc
    except anthropic.RateLimitError as exc:
        raise ReportError("Limite d'utilisation de l'API Claude atteinte : réessayez dans quelques minutes") from exc
    except anthropic.APIStatusError as exc:
        raise ReportError(f"Erreur du service Claude ({exc.status_code}) : réessayez plus tard") from exc
    except anthropic.APIConnectionError as exc:
        raise ReportError("Impossible de joindre l'API Claude : vérifiez la connexion internet du serveur") from exc
    except anthropic.AnthropicError as exc:
        raise ReportError(f"Appel à l'API Claude impossible : {exc}") from exc
    except TypeError as exc:
        # Le SDK lève une TypeError quand aucune clé ni aucun profil n'est configuré.
        if "authentication" in str(exc):
            raise ReportError(MISSING_KEY) from exc
        raise

    if response.stop_reason == "refusal":
        raise ReportError("L'IA a refusé de rédiger ce rapport. Reformulez les points à approfondir et réessayez.")
    if response.stop_reason == "max_tokens":
        raise ReportError("Le rapport a dépassé la longueur maximale : réduisez le nombre d'indicateurs et réessayez")
    text = next((b.text for b in response.content if b.type == "text"), None)
    if not text:
        raise ReportError("Réponse vide de l'IA : réessayez")
    try:
        content = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ReportError("Réponse de l'IA illisible : réessayez") from exc
    return WrittenReport(content, response.model, response.usage.input_tokens, response.usage.output_tokens)
