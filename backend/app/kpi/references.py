"""Référentiels : secteurs d'activité, tailles d'entreprise et domaines de tableau de bord."""

SECTORS: dict[str, str] = {
    "industrie": "Industrie manufacturière",
    "agroalimentaire": "Agroalimentaire",
    "textile": "Textile et habillement",
    "btp": "BTP et construction",
    "commerce": "Commerce et distribution",
    "services": "Services aux entreprises / conseil",
    "tic": "Informatique et télécoms",
    "transport": "Transport et logistique",
    "hotellerie_restauration": "Hôtellerie et restauration",
    "sante": "Santé et pharmacie",
    "agriculture": "Agriculture",
    "immobilier": "Immobilier",
}

# Classification inspirée des critères marocains (effectif / chiffre d'affaires en MAD).
SIZES: dict[str, str] = {
    "tpe": "TPE (moins de 10 salariés)",
    "pme": "PME (10 à 200 salariés)",
    "ge": "Grande entreprise (plus de 200 salariés)",
}

DOMAINS: dict[str, str] = {
    "commercial": "Commercial et ventes",
    "production": "Production",
    "stock": "Gestion des stocks",
    "rh": "Ressources humaines",
    "tresorerie": "Trésorerie",
    "comptabilite": "Comptabilité et finance",
}

# Domaines pertinents par secteur (les autres restent accessibles, mais ne sont pas suggérés).
_ALL_DOMAINS = list(DOMAINS)
_NO_PRODUCTION = [d for d in _ALL_DOMAINS if d != "production"]
_NO_PRODUCTION_STOCK = [d for d in _NO_PRODUCTION if d != "stock"]

SECTOR_DOMAINS: dict[str, list[str]] = {
    "industrie": _ALL_DOMAINS,
    "agroalimentaire": _ALL_DOMAINS,
    "textile": _ALL_DOMAINS,
    "btp": _ALL_DOMAINS,
    "agriculture": _ALL_DOMAINS,
    "commerce": _NO_PRODUCTION,
    "hotellerie_restauration": _NO_PRODUCTION,
    "sante": _NO_PRODUCTION,
    "transport": _NO_PRODUCTION_STOCK,
    "services": _NO_PRODUCTION_STOCK,
    "tic": _NO_PRODUCTION_STOCK,
    "immobilier": _NO_PRODUCTION_STOCK,
}


def size_from_profile(employees: int | None, annual_revenue: float | None) -> str:
    """Déduit la taille à partir de l'effectif, ou à défaut du chiffre d'affaires (MAD)."""
    if employees is not None:
        if employees < 10:
            return "tpe"
        return "pme" if employees <= 200 else "ge"
    if annual_revenue is not None:
        if annual_revenue < 3_000_000:
            return "tpe"
        return "pme" if annual_revenue <= 175_000_000 else "ge"
    return "pme"
