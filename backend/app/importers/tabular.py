"""Lecture des fichiers CSV et Excel.

Gère les cas courants des fichiers d'entreprise marocains et français :
- encodages UTF-8 ou Windows-1252, séparateurs « ; », « , » ou tabulation ;
- lignes de titre au-dessus de l'en-tête ;
- nombres au format « 1 234,56 » ou suivis d'une devise (MAD, DH, €).
"""
import io
import json
import re
from dataclasses import dataclass

import pandas as pd


class ImportErrorFr(ValueError):
    """Erreur de lecture présentée telle quelle à l'utilisateur."""


@dataclass
class ParsedTable:
    columns: list[str]
    rows: list[dict]
    sheets: list[str]
    sheet: str | None


SUPPORTED = {".csv": "csv", ".txt": "csv", ".xlsx": "excel", ".xlsm": "excel", ".xls": "excel"}

_CURRENCY = re.compile(r"(mad|dhs?|dh|eur|€|\$|usd)", re.IGNORECASE)
_NUMBER_FR = re.compile(r"^-?\d{1,3}([ .]\d{3})*(,\d+)?$|^-?\d+(,\d+)?$")
_NUMBER_EN = re.compile(r"^-?\d{1,3}(,\d{3})*(\.\d+)?$|^-?\d+(\.\d+)?$")


def file_kind(filename: str) -> str:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED:
        raise ImportErrorFr("Format non pris en charge. Formats acceptés : CSV, XLSX, XLS.")
    return SUPPORTED[ext]


def _decode(content: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ImportErrorFr("Impossible de lire l'encodage du fichier.")


def _sniff_separator(text: str) -> str:
    sample = [line for line in text.splitlines()[:30] if line.strip()]
    best, best_score = ",", -1
    for sep in (";", ",", "\t", "|"):
        counts = [line.count(sep) for line in sample]
        if not counts or max(counts) == 0:
            continue
        # Séparateur présent de façon régulière sur les lignes de données.
        mode = max(set(counts), key=counts.count)
        score = counts.count(mode) * mode
        if score > best_score:
            best, best_score = sep, score
    return best


def _header_row(raw: pd.DataFrame) -> int:
    """Indice de la ligne d'en-tête : première ligne quasi complète composée de textes."""
    if raw.empty:
        return 0
    width = raw.notna().sum(axis=1).max()
    for idx in range(min(len(raw), 15)):
        row = raw.iloc[idx]
        filled = row.dropna()
        if len(filled) >= max(1, 0.6 * width):
            texts = sum(isinstance(v, str) and not _looks_numeric(v) for v in filled)
            if texts >= 0.6 * len(filled):
                return idx
    return 0


def _looks_numeric(value: str) -> bool:
    return _to_number(value) is not None


def _to_number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if pd.isna(value) else float(value)
    text = _CURRENCY.sub("", str(value)).replace(" ", " ").replace(" ", " ").strip()
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    text = text.strip("()").strip()
    if text.endswith("%"):
        text = text[:-1].strip()
    if _NUMBER_FR.match(text):
        number = float(text.replace(" ", "").replace(".", "").replace(",", "."))
    elif _NUMBER_EN.match(text):
        number = float(text.replace(",", ""))
    else:
        return None
    return -number if negative else number


def _unique_columns(values: list) -> list[str]:
    columns, seen = [], {}
    for i, value in enumerate(values):
        name = str(value).strip() if value is not None and not pd.isna(value) else ""
        name = name or f"Colonne {i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name} ({seen[name]})"
        else:
            seen[name] = 1
        columns.append(name)
    return columns


def _finalize(raw: pd.DataFrame) -> tuple[list[str], list[dict]]:
    raw = raw.dropna(how="all").dropna(axis=1, how="all")
    if raw.empty:
        raise ImportErrorFr("Le fichier ne contient aucune donnée.")
    header = _header_row(raw)
    columns = _unique_columns(list(raw.iloc[header]))
    df = raw.iloc[header + 1:].copy()
    df.columns = columns
    df = df.dropna(how="all")

    for col in df.columns:
        values = df[col].dropna()
        if values.empty:
            continue
        numbers = values.map(_to_number)
        # Colonne numérique si au moins 90 % des valeurs sont des nombres.
        if numbers.notna().mean() >= 0.9 and not values.map(lambda v: isinstance(v, pd.Timestamp)).any():
            df[col] = df[col].map(lambda v: _to_number(v) if v is not None and not pd.isna(v) else None)

    # Passage par JSON : dates en ISO, NaN en null.
    rows = json.loads(df.to_json(orient="records", date_format="iso", force_ascii=False))
    return columns, rows


def parse_file(filename: str, content: bytes, sheet: str | None = None) -> ParsedTable:
    kind = file_kind(filename)
    if not content:
        raise ImportErrorFr("Le fichier est vide.")

    if kind == "csv":
        text = _decode(content)
        try:
            raw = pd.read_csv(io.StringIO(text), sep=_sniff_separator(text), header=None, dtype=str,
                              skip_blank_lines=True, on_bad_lines="skip", engine="python")
        except Exception as exc:  # noqa: BLE001 - message transmis à l'utilisateur
            raise ImportErrorFr(f"Lecture du CSV impossible : {exc}") from exc
        raw = raw.map(lambda v: v.strip() if isinstance(v, str) else v).replace("", None)
        columns, rows = _finalize(raw)
        return ParsedTable(columns, rows, [], None)

    try:
        book = pd.read_excel(io.BytesIO(content), sheet_name=None, header=None)
    except Exception as exc:  # noqa: BLE001
        raise ImportErrorFr(f"Lecture du fichier Excel impossible : {exc}") from exc
    sheets = list(book)
    if sheet is not None and sheet not in book:
        raise ImportErrorFr(f"Feuille « {sheet} » introuvable.")
    chosen = sheet or next((name for name, df in book.items() if not df.dropna(how="all").empty), sheets[0])
    columns, rows = _finalize(book[chosen])
    return ParsedTable(columns, rows, sheets, chosen)
