"""Rapprochement automatique des colonnes d'un fichier avec les champs standard d'un domaine."""
import re
import unicodedata
from difflib import SequenceMatcher

import pandas as pd

from ..kpi.fields import Field, fields_for


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(text.split())


def _name_score(column: str, field: Field) -> float:
    col = normalize(column)
    if not col:
        return 0.0
    best = 0.0
    col_tokens = set(col.split())
    for synonym in field.synonyms:
        syn = normalize(synonym)
        if not syn:
            continue
        if col == syn:
            return 1.0
        syn_tokens = set(syn.split())
        if syn_tokens <= col_tokens:
            # Tous les mots du synonyme sont présents dans l'en-tête (ex. « Montant HT (MAD) »).
            best = max(best, 0.75 + 0.15 * len(syn_tokens) / len(col_tokens))
        else:
            best = max(best, SequenceMatcher(None, col, syn).ratio() * 0.9)
    return best


def _type_score(values: list, field_type: str) -> float:
    """Part des valeurs compatibles avec le type attendu (1 si aucune valeur)."""
    sample = [v for v in values if v is not None][:200]
    if not sample:
        return 1.0
    if field_type == "number":
        return sum(isinstance(v, (int, float)) for v in sample) / len(sample)
    if field_type == "date":
        parsed = pd.to_datetime(pd.Series([str(v) for v in sample]), errors="coerce", dayfirst=True, format="mixed")
        return float(parsed.notna().mean())
    # Texte : tout convient, mais une colonne purement numérique est moins probable.
    return 0.6 if all(isinstance(v, (int, float)) for v in sample) else 1.0


def suggest_mapping(domain: str, columns: list[str], rows: list[dict]) -> dict[str, str]:
    """Retourne {code du champ standard: nom de la colonne source}."""
    candidates = []
    for field in fields_for(domain):
        for column in columns:
            name = _name_score(column, field)
            if name < 0.7:
                continue
            values = [row.get(column) for row in rows[:200]]
            score = name * (0.4 + 0.6 * _type_score(values, field.type))
            if score >= 0.6:
                candidates.append((score, field.code, column))

    mapping: dict[str, str] = {}
    used: set[str] = set()
    for _, code, column in sorted(candidates, reverse=True):
        if code not in mapping and column not in used:
            mapping[code] = column
            used.add(column)
    return mapping


def validate_mapping(domain: str, columns: list[str], mapping: dict[str, str]) -> dict[str, str]:
    valid_fields = {f.code for f in fields_for(domain)}
    clean = {}
    for code, column in mapping.items():
        if not column:
            continue
        if code not in valid_fields:
            raise ValueError(f"Champ inconnu pour ce domaine : {code}")
        if column not in columns:
            raise ValueError(f"Colonne absente du fichier : {column}")
        clean[code] = column
    if len(set(clean.values())) != len(clean):
        raise ValueError("Une même colonne ne peut pas être associée à deux champs.")
    return clean
