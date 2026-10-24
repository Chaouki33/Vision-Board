"""Projet Power BI (.pbip) d'un tableau de bord, aux couleurs de l'application.

Le projet est livré en archive ZIP : un fichier .pbip à ouvrir dans Power BI Desktop, son modèle
sémantique (model.bim) et son rapport (report.json) avec le thème Vision Board. Les données sont
intégrées au modèle (requêtes Power Query autonomes, sans connexion à un fichier ni à un serveur) :
indicateurs calculés, séries des graphiques et lignes de chaque fichier source sur la période.
L'archive contient aussi le classeur Excel du tableau de bord et le thème seul (.json).
"""
import base64
import io
import json
import re
import unicodedata
import uuid
import zipfile
import zlib

from ..reports.formatting import fmt_delta, fmt_value
from .data import PALETTE, STATUS_LABELS, ExportData
from .excel import to_xlsx

PAGE_WIDTH = 1280
MARGIN = 24
GAP = 16
HEADER_H = 140  # en-tête : trois lignes de texte, sans rognage
STATUS_COLORS = {"ok": PALETTE["ok"], "warning": PALETTE["warn"], "critical": PALETTE["danger"]}
STATUS_ICONS = {"ok": "✓", "warning": "!", "critical": "✕"}


# ---------------------------------------------------------------- Outils
def _id() -> str:
    return uuid.uuid4().hex[:20]


def clean_name(name: str) -> str:
    """Nom de table, de colonne ou de mesure accepté par Power BI."""
    name = re.sub(r"[\[\]{}\"\t\r\n.]", " ", str(name))
    return re.sub(r"\s+", " ", name).strip() or "Colonne"


def unique_names(names: list[str], taken: set[str] | None = None) -> list[str]:
    """Noms nettoyés et uniques (Power BI ne distingue pas les majuscules)."""
    taken = set() if taken is None else taken
    result = []
    for name in names:
        base = clean_name(name)
        candidate, n = base, 1
        while candidate.lower() in taken:
            n += 1
            candidate = f"{base} ({n})"
        taken.add(candidate.lower())
        result.append(candidate)
    return result


def format_string(unit: str) -> str:
    # L'espace est dans les guillemets : Power BI insère k ou M juste après le nombre (« 12,2 M MAD »).
    if unit == "MAD":
        return '#,0" MAD"'
    if unit == "%":
        return '0.0" %"'
    if unit == "ratio":
        return "0.00"
    if unit in ("jours", "mois", "heures", "ans"):
        return f'0.0" {unit}"'
    return "#,0.##"


def label_precision(unit: str) -> int:
    """Décimales des cartes : aucune pour les nombres de clients, de ventes, etc."""
    if unit == "ratio":
        return 2
    return 1 if unit in ("MAD", "%", "jours", "mois", "heures", "ans") else 0


def _m_text(text: str) -> str:
    return '"' + text.replace('"', '""') + '"'


def _dax_table(name: str) -> str:
    return "'" + name.replace("'", "''") + "'"


def _serialize(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float):
        return repr(int(value)) if value.is_integer() and abs(value) < 1e15 else repr(value)
    return str(value)


M_TYPES = {"int": "Int64.Type", "number": "type number", "date": "type date", "text": "type text"}
MODEL_TYPES = {"int": "int64", "number": "double", "date": "dateTime", "text": "string"}


def m_expression(columns: list[tuple[str, str]], rows: list[list]) -> list[str]:
    """Requête Power Query qui reconstitue la table à partir de données compressées intégrées."""
    payload = json.dumps([[_serialize(v) for v in row] for row in rows], ensure_ascii=False, separators=(",", ":"))
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)  # Compression.Deflate = deflate brut
    packed = base64.b64encode(compressor.compress(payload.encode("utf-8")) + compressor.flush()).decode()
    text_type = ", ".join(f"#{_m_text(name)} = _t" for name, _ in columns)
    types = ", ".join(f"{{{_m_text(name)}, {M_TYPES[t]}}}" for name, t in columns)
    return [
        "let",
        f'    Source = Table.FromRows(Json.Document(Binary.Decompress(Binary.FromText("{packed}", '
        f'BinaryEncoding.Base64), Compression.Deflate)), let _t = ((type nullable text) meta [Serialized.Text = true]) '
        f"in type table [{text_type}]),",
        f'    Typed = Table.TransformColumnTypes(Source, {{{types}}}, "en-US")',
        "in",
        "    Typed",
    ]


def model_table(name: str, columns: list[tuple[str, str]], rows: list[list], formats: dict[str, str] | None = None,
                sort_by: dict[str, str] | None = None, hidden: set[str] | None = None, measures: list | None = None):
    formats, sort_by, hidden = formats or {}, sort_by or {}, hidden or set()
    table_columns = []
    for col, type_ in columns:
        column = {"name": col, "dataType": MODEL_TYPES[type_], "sourceColumn": col, "summarizeBy": "none",
                  "annotations": [{"name": "SummarizationSetBy", "value": "User"}]}
        if col in formats:
            column["formatString"] = formats[col]
        elif type_ == "date":
            column["formatString"] = "dd/mm/yyyy"
        elif type_ == "number":
            column["formatString"] = "#,0.##"
        elif type_ == "int":
            column["formatString"] = "0"
        if col in sort_by:
            column["sortByColumn"] = sort_by[col]
        if col in hidden:
            column["isHidden"] = True
        table_columns.append(column)
    table = {
        "name": name, "columns": table_columns,
        "partitions": [{"name": name, "mode": "import", "source": {"type": "m", "expression": m_expression(columns, rows)}}],
        "annotations": [{"name": "PBI_ResultType", "value": "Table"}],
    }
    if measures:
        table["measures"] = measures
    return table


# ---------------------------------------------------------------- Modèle sémantique
def build_model(data: ExportData) -> tuple[dict, dict]:
    """Renvoie le modèle (model.bim) et les noms utiles au rapport (mesures, tables sources)."""
    taken: set[str] = set()
    for reserved in ("Indicateurs", "Graphiques"):
        taken.add(reserved.lower())

    # Indicateurs + une mesure par indicateur calculé
    ind_columns = [("Ordre", "int"), ("Code", "text"), ("Indicateur", "text"), ("Valeur", "number"), ("Unité", "text"),
                   ("Valeur affichée", "text"), ("Statut", "text"), ("Détail", "text"),
                   ("Variation vs mois précédent (%)", "number"), ("Formule", "text"), ("Description", "text"),
                   ("Remarque", "text")]
    ind_names = unique_names([k.name for k in data.kpis], {c.lower() for c, _ in ind_columns})
    ind_rows = [[i + 1, k.code, ind_names[i], k.value, k.unit, fmt_value(k.value, k.unit),
                 STATUS_LABELS.get(k.status or ""), k.detail, k.delta, k.formula, k.description, k.error]
                for i, k in enumerate(data.kpis)]
    measure_taken = {c.lower() for c, _ in ind_columns} | {"graphiques", "indicateurs", "code", "graphique",
                                                          "ordre", "libellé", "valeur", "unité"}
    measure_names = unique_names([k.name for k in data.kpis], measure_taken)
    measures, kpi_measures = [], {}
    for k, measure in zip(data.kpis, measure_names):
        if k.value is None:
            continue
        kpi_measures[k.code] = measure
        measures.append({
            "name": measure, "formatString": format_string(k.unit),
            "expression": f'CALCULATE(MAX({_dax_table("Indicateurs")}[Valeur]), '
                          f'{_dax_table("Indicateurs")}[Code] = "{k.code}")',
            "description": k.formula,
        })
    indicators = model_table("Indicateurs", ind_columns, ind_rows, sort_by={"Indicateur": "Ordre"},
                             hidden={"Ordre", "Code"}, measures=measures)

    # Séries des graphiques. Le libellé est trié selon l'ordre du graphique ; un caractère invisible
    # par graphique distingue les libellés communs à plusieurs graphiques (ex. « janv. 2025 »).
    chart_rows, order = [], 0
    for n, k in enumerate(data.charts):
        for label, value in zip(k.chart.labels, k.chart.values):
            order += 1
            chart_rows.append([k.code, k.chart.title, order, f"{label}{chr(0x200B) * n}", value, k.chart.unit])
    # Une mesure par graphique : elle ne renvoie que les valeurs de ce graphique, et Power BI masque
    # les libellés des autres (valeur vide). Plus fiable qu'un filtre de visuel.
    chart_measures, series_measures = {}, []
    series_names = unique_names([f"Série - {k.chart.title}" for k in data.charts], measure_taken)
    for k, measure in zip(data.charts, series_names):
        chart_measures[k.code] = measure
        series_measures.append({
            "name": measure, "formatString": format_string(k.chart.unit),
            "expression": f'CALCULATE(SUM({_dax_table("Graphiques")}[Valeur]), '
                          f'{_dax_table("Graphiques")}[Code] = "{k.code}")',
        })
    charts = model_table("Graphiques", [("Code", "text"), ("Graphique", "text"), ("Ordre", "int"), ("Libellé", "text"),
                                        ("Valeur", "number"), ("Unité", "text")], chart_rows,
                         sort_by={"Libellé": "Ordre"}, hidden={"Ordre", "Code"}, measures=series_measures)

    # Fichiers sources
    sources = []
    table_names = unique_names([f"Données - {t.name}" for t in data.tables], taken)
    for table, table_name in zip(data.tables, table_names):
        col_names = unique_names(["N° ligne"] + [c for c, _ in table.columns])
        columns = [(col_names[0], "int")] + [(name, t) for name, (_, t) in zip(col_names[1:], table.columns)]
        rows = [[i + 1, *row] for i, row in enumerate(table.rows)]
        sources.append(model_table(table_name, columns, rows))

    tables = [indicators, charts, *sources]
    model = {
        "compatibilityLevel": 1550,
        "model": {
            "culture": "fr-FR",
            "sourceQueryCulture": "fr-FR",
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "dataAccessOptions": {"legacyRedirects": True, "returnErrorValuesAsNull": True},
            "tables": tables,
            "annotations": [
                {"name": "PBI_QueryOrder", "value": json.dumps([t["name"] for t in tables], ensure_ascii=False)},
                {"name": "__PBI_TimeIntelligenceEnabled", "value": "0"},
            ],
        },
    }
    names = {
        "measures": kpi_measures,
        "chart_measures": chart_measures,
        "sources": [(t["name"], [c["name"] for c in t["columns"]]) for t in sources],
    }
    return model, names


# ---------------------------------------------------------------- Rapport
def lit(value: str) -> dict:
    return {"expr": {"Literal": {"Value": value}}}


def text(value: str) -> dict:
    return lit("'" + value.replace("'", "''") + "'")


def color(hex_color: str) -> dict:
    return {"solid": {"color": text(hex_color)}}


def _column(source: str, prop: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Source": source}}, "Property": prop}}


def _container(x: int, y: int, w: int, h: int, z: int, visual: dict, filters: list | None = None) -> dict:
    name = _id()
    config = {"name": name, "layouts": [{"id": 0, "position": {"x": x, "y": y, "z": z, "width": w, "height": h,
                                                               "tabOrder": z}}],
              "singleVisual": visual}
    return {"x": x, "y": y, "z": z, "width": w, "height": h, "config": json.dumps(config, ensure_ascii=False),
            "filters": json.dumps(filters or [], ensure_ascii=False)}


def textbox(paragraphs: list[list[tuple[str, dict]]], background: str | None = None) -> dict:
    visual = {
        "visualType": "textbox", "drillFilterOtherVisuals": True,
        "objects": {"general": [{"properties": {"paragraphs": [
            {"textRuns": [{"value": value, "textStyle": style} for value, style in runs]} for runs in paragraphs]}}]},
        "vcObjects": {"border": [{"properties": {"show": lit("false")}}],
                      "dropShadow": [{"properties": {"show": lit("false")}}]},
    }
    if background:
        visual["vcObjects"]["background"] = [{"properties": {"show": lit("true"), "color": color(background),
                                                              "transparency": lit("0D")}}]
    return visual


def card(measure: str, title: str, subtitle: str, subtitle_color: str, unit: str = "") -> dict:
    ref = f"Indicateurs.{measure}"
    return {
        "visualType": "card",
        "projections": {"Values": [{"queryRef": ref}]},
        "prototypeQuery": {"Version": 2, "From": [{"Name": "i", "Entity": "Indicateurs", "Type": 0}],
                           "Select": [{"Measure": {"Expression": {"SourceRef": {"Source": "i"}}, "Property": measure},
                                       "Name": ref, "NativeReferenceName": measure}]},
        "drillFilterOtherVisuals": True,
        # Unités automatiques (k, M) avec une décimale, comme « 12,2 M MAD » dans l'application
        "objects": {"labels": [{"properties": {"color": color(PALETTE["primary"]), "fontSize": lit("22D"),
                                               "labelDisplayUnits": lit("0D"),
                                               "labelPrecision": lit(f"{label_precision(unit)}L")}}],
                    "categoryLabels": [{"properties": {"show": lit("false")}}]},
        "vcObjects": {
            "title": [{"properties": {"show": lit("true"), "text": text(title), "fontColor": color(PALETTE["muted"]),
                                      "fontSize": lit("10D")}}],
            "subTitle": [{"properties": {"show": lit("true" if subtitle else "false"), "text": text(subtitle),
                                         "fontColor": color(subtitle_color), "fontSize": lit("9D")}}],
        },
    }


def chart_visual(kpi, measure: str) -> dict:
    chart = kpi.chart
    visual_type = "lineChart" if chart.type == "line" else "clusteredBarChart"
    label = _column("g", "Libellé")
    ref = f"Graphiques.{measure}"
    title = f"{chart.title} ({chart.unit})" if chart.unit else chart.title
    visual = {
        "visualType": visual_type,
        "projections": {"Category": [{"queryRef": "Graphiques.Libellé", "active": True}],
                        "Y": [{"queryRef": ref}]},
        "prototypeQuery": {
            "Version": 2, "From": [{"Name": "g", "Entity": "Graphiques", "Type": 0}],
            "Select": [{**label, "Name": "Graphiques.Libellé", "NativeReferenceName": "Libellé"},
                       {"Measure": {"Expression": {"SourceRef": {"Source": "g"}}, "Property": measure},
                        "Name": ref, "NativeReferenceName": measure}],
            "OrderBy": [{"Direction": 1, "Expression": label}],
        },
        "drillFilterOtherVisuals": True,
        "objects": {
            "dataPoint": [{"properties": {"fill": color(PALETTE["series"])}}],
            "labels": [{"properties": {"show": lit("true"), "color": color(PALETTE["muted"])}}],
            "legend": [{"properties": {"show": lit("false")}}],
            "categoryAxis": [{"properties": {"showAxisTitle": lit("false")}}],
            "valueAxis": [{"properties": {"showAxisTitle": lit("false")}}],
        },
        "vcObjects": {"title": [{"properties": {"show": lit("true"), "text": text(title)}}]},
    }
    if chart.type != "line":  # valeur au bout de la barre, lisible même sur la plus longue
        visual["objects"]["labels"][0]["properties"]["labelPosition"] = text("OutsideEnd")
    if chart.type == "line":
        visual["objects"]["lineStyles"] = [{"properties": {"showMarker": lit("true"), "strokeWidth": lit("2L")}}]
    return visual


def table_visual(entity: str, columns: list[str], title: str) -> dict:
    refs = [f"{entity}.{c}" for c in columns]
    return {
        "visualType": "tableEx",
        "projections": {"Values": [{"queryRef": r} for r in refs]},
        "prototypeQuery": {"Version": 2, "From": [{"Name": "t", "Entity": entity, "Type": 0}],
                           "Select": [{**_column("t", c), "Name": r, "NativeReferenceName": c}
                                      for c, r in zip(columns, refs)]},
        "drillFilterOtherVisuals": True,
        "vcObjects": {"title": [{"properties": {"show": lit("true"), "text": text(title)}}]},
    }


def _header_box(data: ExportData, title: str, subtitle: str) -> dict:
    white = {"color": "#ffffff", "fontFamily": "Segoe UI"}
    return textbox([
        [(f"VISION BOARD  ·  {data.company.upper()}", {**white, "fontSize": "9pt", "fontWeight": "bold"})],
        [(title, {**white, "fontSize": "20pt", "fontWeight": "bold"})],
        [(subtitle, {**white, "fontSize": "10pt"})],
    ], background=data.colors[0])


def _section(name: str, ordinal: int, height: int, containers: list[dict]) -> dict:
    return {"name": f"ReportSection{_id()}", "displayName": name, "displayOption": 2, "ordinal": ordinal,
            "width": PAGE_WIDTH, "height": height, "filters": "[]", "config": "{}",
            "visualContainers": containers}


def build_report(data: ExportData, names: dict) -> dict:
    inner = PAGE_WIDTH - 2 * MARGIN
    containers: list[dict] = []
    z = 0

    def add(x, y, w, h, visual, filters=None):
        nonlocal z
        containers.append(_container(x, y, w, h, z, visual, filters))
        z += 1000

    computed = sum(1 for k in data.kpis if k.error is None)
    tags = "  ·  ".join(t for t in (data.sector_label, data.size_label, data.city) if t)
    add(MARGIN, MARGIN, inner, HEADER_H, _header_box(
        data, data.title,
        f"{data.domain_label}  ·  {computed} indicateurs calculés sur {len(data.kpis)}  ·  {data.period_text}"
        f"  ·  {tags}"))
    y = MARGIN + HEADER_H + GAP

    # Tuiles des indicateurs, quatre par ligne
    per_row, tile_h = 4, 120
    tile_w = (inner - (per_row - 1) * GAP) // per_row
    for i, k in enumerate(data.kpis):
        x = MARGIN + (i % per_row) * (tile_w + GAP)
        ty = y + (i // per_row) * (tile_h + GAP)
        status = STATUS_LABELS.get(k.status or "")
        sub = "  ·  ".join(t for t in (f"{STATUS_ICONS[k.status]} {status}" if status else None,
                                        k.detail, fmt_delta(k.delta)) if t)
        measure = names["measures"].get(k.code)
        if measure:
            add(x, ty, tile_w, tile_h, card(measure, k.name, sub, STATUS_COLORS.get(k.status or "", PALETTE["muted"]), k.unit))
        else:
            add(x, ty, tile_w, tile_h, textbox([
                [(k.name, {"fontSize": "10pt", "color": PALETTE["muted"], "fontWeight": "bold"})],
                [("—", {"fontSize": "20pt", "color": PALETTE["primary"], "fontWeight": "bold"})],
                [(k.error or "", {"fontSize": "9pt", "color": PALETTE["muted"]})],
            ], background=PALETTE["surface"]))
    if data.kpis:
        y += -(-len(data.kpis) // per_row) * (tile_h + GAP)

    # Graphiques, deux par ligne
    chart_w, chart_h = (inner - GAP) // 2, 320
    for i, k in enumerate(data.charts):
        add(MARGIN + (i % 2) * (chart_w + GAP), y + (i // 2) * (chart_h + GAP), chart_w, chart_h,
            chart_visual(k, names["chart_measures"][k.code]))
    if data.charts:
        y += -(-len(data.charts) // 2) * (chart_h + GAP)

    # Synthèse des indicateurs
    summary_h = 60 + 28 * max(len(data.kpis), 1)
    add(MARGIN, y, inner, summary_h, table_visual(
        "Indicateurs", ["Indicateur", "Valeur affichée", "Statut", "Détail", "Formule"], "Synthèse des indicateurs"))
    y += summary_h + MARGIN

    sections = [_section("Tableau de bord", 0, max(y, 720), containers)]

    # Une page par fichier source
    for n, (entity, columns) in enumerate(names["sources"], start=1):
        table = data.tables[n - 1]
        containers, z = [], 0
        add(MARGIN, MARGIN, inner, HEADER_H, _header_box(
            data, entity, f"Fichier source : {table.source_filename}  ·  {len(table.rows)} lignes  ·  {data.period_text}"))
        add(MARGIN, MARGIN + HEADER_H + GAP, inner, 720 - 2 * MARGIN - HEADER_H - GAP, table_visual(entity, columns, entity))
        sections.append(_section(entity[:100], n, 720, containers))

    config = {
        "version": "5.43",
        "themeCollection": {"customTheme": {"name": THEME_FILE, "version": "5.43", "type": 1}},
        "activeSectionIndex": 0,
        "defaultDrillFilterOtherVisuals": True,
        "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": 1,
                     "useNewFilterPaneExperience": True, "allowChangeFilterTypes": True,
                     "useDefaultAggregateDisplayName": True},
    }
    return {
        "config": json.dumps(config),
        "layoutOptimization": 0,
        "publicCustomVisuals": [],
        "resourcePackages": [{"resourcePackage": {
            "name": "RegisteredResources", "type": 1, "disabled": False,
            "items": [{"name": THEME_FILE, "path": THEME_FILE, "type": 202}]}}],
        "sections": sections,
    }


THEME_FILE = "VisionBoard.json"


def build_theme(data: ExportData) -> dict:
    s1, s2 = data.colors
    border = {"show": True, "color": {"solid": {"color": PALETTE["border"]}}, "radius": 12}
    return {
        "name": "Vision Board",
        "dataColors": [PALETTE["series"], PALETTE["accent"], s1, PALETTE["primary"], s2, PALETTE["ok"],
                       PALETTE["warn"], PALETTE["danger"], PALETTE["other"]],
        "foreground": PALETTE["text"], "foregroundNeutralSecondary": PALETTE["muted"],
        "background": PALETTE["surface"], "backgroundLight": PALETTE["surface_2"],
        "backgroundNeutral": PALETTE["border"], "tableAccent": PALETTE["accent"],
        "good": PALETTE["ok"], "neutral": PALETTE["warn"], "bad": PALETTE["danger"],
        "textClasses": {
            "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 22, "color": PALETTE["primary"]},
            "title": {"fontFace": "Segoe UI Semibold", "fontSize": 11, "color": PALETTE["text"]},
            "header": {"fontFace": "Segoe UI Semibold", "fontSize": 11, "color": PALETTE["text"]},
            "label": {"fontFace": "Segoe UI", "fontSize": 9, "color": PALETTE["muted"]},
        },
        "visualStyles": {
            "*": {"*": {
                "background": [{"show": True, "color": {"solid": {"color": PALETTE["surface"]}}, "transparency": 0}],
                "border": [border],
                "dropShadow": [{"show": True, "color": {"solid": {"color": "#1B3A6B"}}, "transparency": 88,
                                "position": "Outer", "preset": "Bottom"}],
                "visualHeader": [{"show": False}],
                "padding": [{"top": 12, "bottom": 12, "left": 14, "right": 14}],
            }},
            "page": {"*": {
                "background": [{"color": {"solid": {"color": PALETTE["bg"]}}, "transparency": 0}],
                "outspace": [{"color": {"solid": {"color": PALETTE["bg"]}}, "transparency": 0}],
            }},
            "tableEx": {"*": {
                "columnHeaders": [{"fontColor": {"solid": {"color": "#FFFFFF"}},
                                   "backColor": {"solid": {"color": PALETTE["primary"]}}}],
                "values": [{"backColorSecondary": {"solid": {"color": PALETTE["surface_2"]}}}],
            }},
        },
    }


def _platform(kind: str, name: str) -> str:
    return json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": kind, "displayName": name},
        "config": {"version": "2.0", "logicalId": str(uuid.uuid4())},
    }, indent=2)


README = """Vision Board - projet Power BI
==============================

Contenu
-------
- {name}.pbip : le projet à ouvrir dans Power BI Desktop.
- {name}.Report et {name}.SemanticModel : le rapport et son modèle (ne pas les séparer du fichier .pbip).
- {name}.xlsx : le même tableau de bord en classeur Excel, avec les données sources.
- Theme_VisionBoard.json : le thème Vision Board seul, à appliquer à un autre rapport.

Ouvrir le projet
----------------
1. Décompressez toute l'archive dans un dossier (clic droit > Extraire tout).
2. Double-cliquez sur {name}.pbip (Power BI Desktop, version récente, gratuit sur le Microsoft Store).
   Si Power BI Desktop ne reconnaît pas ce format : Fichier > Options et paramètres > Options >
   Fonctionnalités en préversion > cochez « Enregistrement de projet Power BI (.pbip) », puis redémarrez-le.
3. Cliquez sur « Actualiser » (onglet Accueil) pour charger les données dans les visuels.

Les données (indicateurs, graphiques et lignes des fichiers sources) sont intégrées au projet :
aucune connexion à un fichier ou à un serveur n'est nécessaire. Le tableau de bord a été exporté
le {date}, sur la période {period}.

Solution de secours
-------------------
Si le projet ne s'ouvre pas : dans Power BI Desktop, Obtenir les données > Excel, choisissez
{name}.xlsx, puis Affichage > Thèmes > Parcourir les thèmes > Theme_VisionBoard.json.
"""


def to_powerbi(data: ExportData) -> bytes:
    base = re.sub(r"[^A-Za-z0-9]+", "_", unicodedata.normalize("NFKD", clean_name(f"{data.company} {data.title}")).encode("ascii", "ignore").decode())
    name = base.strip("_")[:40].strip("_") or "VisionBoard"  # chemins courts une fois extraits
    model, names = build_model(data)
    report = build_report(data, names)
    theme = json.dumps(build_theme(data), indent=2, ensure_ascii=False)

    files = {
        f"{name}.pbip": json.dumps({"version": "1.0", "artifacts": [{"report": {"path": f"{name}.Report"}}],
                                    "settings": {"enableAutoRecovery": True}}, indent=2),
        f"{name}.Report/definition.pbir": json.dumps({"version": "1.0", "datasetReference": {
            "byPath": {"path": f"../{name}.SemanticModel"}, "byConnection": None}}, indent=2),
        f"{name}.Report/report.json": json.dumps(report, indent=2, ensure_ascii=False),
        f"{name}.Report/StaticResources/RegisteredResources/{THEME_FILE}": theme,
        f"{name}.Report/.platform": _platform("Report", name),
        f"{name}.SemanticModel/definition.pbism": json.dumps({"version": "1.0", "settings": {}}, indent=2),
        f"{name}.SemanticModel/model.bim": json.dumps(model, indent=2, ensure_ascii=False),
        f"{name}.SemanticModel/.platform": _platform("SemanticModel", name),
        "Theme_VisionBoard.json": theme,
        "LISEZMOI.txt": README.format(name=name, date=f"{data.generated_at:%d/%m/%Y à %H:%M}",
                                      period=data.period_text).replace("\n", "\r\n"),
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path, content in files.items():
            archive.writestr(f"{name}/{path}", content.encode("utf-8"))
        archive.writestr(f"{name}/{name}.xlsx", to_xlsx(data))
    return buffer.getvalue()
