"""Champs standard attendus pour chaque domaine.

Chaque fichier importé est rapproché de ces champs (mapping) : les KPI s'appuient
uniquement sur les champs standard, jamais sur les noms de colonnes d'origine.
Les synonymes sont comparés après normalisation (minuscules, sans accents ni ponctuation).
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Field:
    code: str
    label: str
    type: str  # "date", "number" ou "text"
    synonyms: tuple[str, ...]


def _f(code: str, label: str, type_: str, *synonyms: str) -> Field:
    return Field(code, label, type_, (label, code.replace("_", " "), *synonyms))


DOMAIN_FIELDS: dict[str, list[Field]] = {
    "commercial": [
        _f("date", "Date de vente", "date", "date", "date facture", "date commande", "date vente", "jour", "invoice date", "order date"),
        _f("montant_ht", "Montant HT", "number", "montant", "montant ht", "ca", "ca ht", "chiffre d affaires", "total ht", "total", "prix total", "amount", "sales", "revenue", "net amount"),
        _f("quantite", "Quantité", "number", "qte", "qty", "quantity", "nombre", "unites"),
        _f("client", "Client", "text", "nom client", "raison sociale", "customer", "client name"),
        _f("produit", "Produit / article", "text", "article", "designation", "reference", "product", "item", "libelle article"),
        _f("commercial", "Commercial", "text", "vendeur", "representant", "agent commercial", "salesperson", "sales rep"),
        _f("region", "Région / ville", "text", "ville", "zone", "secteur geographique", "city", "region"),
        _f("cout_achat", "Coût d'achat / de revient", "number", "cout", "cout achat", "cout de revient", "prix de revient", "cost", "cogs"),
        _f("statut_paiement", "Statut de paiement", "text", "statut", "paiement", "regle", "etat paiement", "payment status", "paid"),
        _f("date_echeance", "Date d'échéance", "date", "echeance", "date echeance", "due date"),
        _f("canal", "Canal de vente", "text", "canal", "channel", "mode de vente"),
        _f("objectif", "Objectif de vente", "number", "objectif", "target", "budget", "objectif ca"),
    ],
    "production": [
        _f("date", "Date", "date", "date", "jour", "date production"),
        _f("ligne", "Ligne / machine / atelier", "text", "machine", "atelier", "ligne", "equipement", "line"),
        _f("produit", "Produit", "text", "article", "reference", "designation", "product"),
        _f("quantite_produite", "Quantité produite", "number", "quantite", "qte produite", "production", "volume", "output"),
        _f("quantite_rebut", "Quantité rebutée", "number", "rebut", "rebuts", "dechets", "non conformes", "defauts", "scrap"),
        _f("objectif", "Objectif de production", "number", "objectif", "prevision", "plan", "target"),
        _f("temps_planifie", "Temps planifié (h)", "number", "temps planifie", "heures planifiees", "temps d ouverture", "planned time"),
        _f("temps_arret", "Temps d'arrêt (h)", "number", "arret", "temps arret", "heures arret", "pannes", "downtime"),
        _f("cadence_theorique", "Cadence théorique (unités/h)", "number", "cadence", "cadence nominale", "vitesse", "rate"),
        _f("cout_production", "Coût de production", "number", "cout", "cout production", "cout total", "cost"),
    ],
    "stock": [
        _f("date", "Date d'inventaire", "date", "date", "date inventaire", "date stock"),
        _f("article", "Article", "text", "produit", "designation", "reference", "item", "sku", "libelle"),
        _f("categorie", "Catégorie / famille", "text", "famille", "categorie", "category", "type"),
        _f("quantite_stock", "Quantité en stock", "number", "stock", "quantite", "qte", "stock actuel", "qte stock", "on hand", "quantity"),
        _f("stock_minimum", "Stock minimum / seuil d'alerte", "number", "stock min", "seuil", "seuil alerte", "stock securite", "minimum", "reorder point"),
        _f("cout_unitaire", "Coût unitaire", "number", "prix unitaire", "cout", "pu", "pmp", "unit cost", "prix achat"),
        _f("entrees", "Entrées", "number", "entrees", "receptions", "achats", "in"),
        _f("sorties", "Sorties / consommation", "number", "sorties", "consommation", "ventes", "out", "quantite vendue"),
        _f("entrepot", "Entrepôt / dépôt", "text", "depot", "magasin", "site", "warehouse"),
        _f("date_peremption", "Date de péremption", "date", "peremption", "dlc", "dluo", "expiration", "date expiration"),
    ],
    "rh": [
        _f("matricule", "Matricule", "text", "id", "code salarie", "numero", "employee id"),
        _f("nom", "Nom du salarié", "text", "nom", "nom complet", "nom prenom", "salarie", "collaborateur", "employe", "name"),
        _f("sexe", "Sexe", "text", "genre", "h f", "gender", "sex"),
        _f("date_naissance", "Date de naissance", "date", "naissance", "date naissance", "birth date"),
        _f("date_embauche", "Date d'embauche", "date", "embauche", "date entree", "entree", "hire date", "date recrutement"),
        _f("date_sortie", "Date de sortie", "date", "sortie", "date depart", "depart", "date fin contrat", "end date"),
        _f("poste", "Poste / fonction", "text", "fonction", "intitule poste", "job title", "emploi"),
        _f("departement", "Département / service", "text", "service", "direction", "departement", "department"),
        _f("type_contrat", "Type de contrat", "text", "contrat", "type contrat", "nature contrat", "contract"),
        _f("salaire_brut", "Salaire brut mensuel", "number", "salaire", "salaire brut", "brut", "remuneration", "salary"),
        _f("jours_absence", "Jours d'absence", "number", "absences", "jours absence", "absence"),
        _f("jours_conges_pris", "Jours de congé pris", "number", "conges pris", "jours conges", "conges"),
        _f("jours_conges_acquis", "Jours de congé acquis", "number", "conges acquis", "droit conges", "solde conges initial"),
        _f("heures_formation", "Heures de formation", "number", "formation", "heures formation", "training hours"),
    ],
    "tresorerie": [
        _f("date", "Date d'opération", "date", "date", "date operation", "date valeur"),
        _f("libelle", "Libellé", "text", "libelle", "description", "operation", "motif"),
        _f("encaissement", "Encaissement", "number", "credit", "recette", "entree", "encaissements", "in"),
        _f("decaissement", "Décaissement", "number", "debit", "depense", "sortie", "decaissements", "out"),
        _f("solde", "Solde", "number", "solde", "balance", "solde fin"),
        _f("banque", "Banque / compte", "text", "banque", "compte", "compte bancaire", "bank", "caisse"),
        _f("categorie", "Catégorie", "text", "categorie", "nature", "rubrique", "type"),
    ],
    "comptabilite": [
        _f("compte", "N° de compte", "text", "compte", "numero compte", "n compte", "account", "code compte"),
        _f("libelle_compte", "Intitulé du compte", "text", "intitule", "libelle", "libelle compte", "designation"),
        _f("debit", "Débit", "number", "debit", "mouvement debit", "solde debit", "total debit"),
        _f("credit", "Crédit", "number", "credit", "mouvement credit", "solde credit", "total credit"),
        _f("date", "Date", "date", "date", "date ecriture"),
        _f("journal", "Journal", "text", "journal", "code journal"),
    ],
}


def fields_for(domain: str) -> list[Field]:
    return DOMAIN_FIELDS[domain]
