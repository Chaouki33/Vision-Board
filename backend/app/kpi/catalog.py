"""Catalogue des KPI.

Chaque KPI déclare :
- les champs standard nécessaires à son calcul (`required`) ;
- les secteurs (`sectors`, "*" = tous) et tailles d'entreprise (`sizes`) concernés ;
- une priorité (1 = essentiel, 2 = important, 3 = approfondissement) ;
- `boost` : secteurs pour lesquels le KPI devient essentiel (priorité 1) ;
- le sens d'évolution souhaité et des seuils d'alerte facultatifs.
"""
from dataclasses import dataclass

ALL = ("*",)
ALL_SIZES = ("tpe", "pme", "ge")
PME_GE = ("pme", "ge")
GE = ("ge",)

PRODUCING = ("industrie", "agroalimentaire", "textile", "btp", "agriculture")
WITH_STOCK = PRODUCING + ("commerce", "hotellerie_restauration", "sante")
PERISHABLE = ("agroalimentaire", "sante", "hotellerie_restauration", "commerce", "agriculture")


@dataclass(frozen=True)
class KPI:
    code: str
    domain: str
    name: str
    description: str
    formula: str
    unit: str  # "MAD", "%", "jours", "mois", "nombre", "ratio", "heures"
    required: tuple[str, ...]
    sectors: tuple[str, ...] = ALL
    sizes: tuple[str, ...] = ALL_SIZES
    priority: int = 2
    boost: tuple[str, ...] = ()
    higher_is_better: bool | None = True
    warning: float | None = None
    critical: float | None = None

    def applies_to(self, sector: str, size: str) -> bool:
        return ("*" in self.sectors or sector in self.sectors) and size in self.sizes

    def priority_for(self, sector: str) -> int:
        return 1 if sector in self.boost else self.priority


KPIS: list[KPI] = [
    # ---------------------------------------------------------------- Commercial
    KPI("ca_total", "commercial", "Chiffre d'affaires HT", "Total des ventes hors taxes sur la période.",
        "Somme(montant HT)", "MAD", ("montant_ht",), priority=1),
    KPI("ca_evolution", "commercial", "Évolution mensuelle du CA", "Variation du CA du dernier mois par rapport au mois précédent.",
        "(CA mois M − CA mois M−1) / CA mois M−1", "%", ("date", "montant_ht"), priority=1),
    KPI("nb_ventes", "commercial", "Nombre de ventes", "Nombre de transactions ou factures sur la période.",
        "Nombre de lignes de vente", "nombre", ("montant_ht",), priority=2),
    KPI("panier_moyen", "commercial", "Panier moyen", "Montant moyen par vente.",
        "CA HT / nombre de ventes", "MAD", ("montant_ht",), priority=2,
        boost=("commerce", "hotellerie_restauration", "sante")),
    KPI("nb_clients_actifs", "commercial", "Clients actifs", "Nombre de clients distincts ayant acheté sur la période.",
        "Nombre de clients distincts", "nombre", ("client",), priority=1),
    KPI("nouveaux_clients", "commercial", "Nouveaux clients", "Clients dont le premier achat a lieu dans le dernier mois.",
        "Clients dont la 1re vente est dans le mois M", "nombre", ("client", "date"), priority=2),
    KPI("concentration_clients", "commercial", "Dépendance aux 5 premiers clients", "Part du CA réalisée avec les 5 plus gros clients : un risque si elle est élevée.",
        "CA top 5 clients / CA total", "%", ("client", "montant_ht"), priority=1,
        higher_is_better=False, warning=50, critical=70),
    KPI("top_produits", "commercial", "CA par produit (top 10)", "Produits qui contribuent le plus au chiffre d'affaires.",
        "CA du meilleur produit (détail par produit)", "MAD", ("produit", "montant_ht"), priority=2,
        boost=("commerce", "industrie", "agroalimentaire", "textile")),
    KPI("quantite_vendue", "commercial", "Quantités vendues", "Volume total vendu.",
        "Somme(quantité)", "nombre", ("quantite",), sectors=WITH_STOCK, priority=2),
    KPI("marge_brute", "commercial", "Taux de marge brute", "Marge dégagée sur les ventes après coût d'achat ou de revient.",
        "(CA HT − coût d'achat) / CA HT", "%", ("montant_ht", "cout_achat"), priority=1, warning=20, critical=10),
    KPI("ca_par_commercial", "commercial", "CA par commercial", "Performance individuelle de la force de vente.",
        "CA moyen par commercial (détail par commercial)", "MAD", ("commercial", "montant_ht"), sizes=PME_GE, priority=1),
    KPI("nb_commerciaux", "commercial", "Nombre de commerciaux", "Taille de la force de vente active.",
        "Nombre de commerciaux distincts", "nombre", ("commercial",), sizes=PME_GE, priority=2),
    KPI("ca_par_region", "commercial", "CA par région", "Répartition géographique des ventes.",
        "Part du CA réalisée dans la première région (détail par région)", "%", ("region", "montant_ht"), sizes=PME_GE, priority=2),
    KPI("ca_par_canal", "commercial", "CA par canal de vente", "Répartition des ventes par canal (magasin, en ligne, grossistes...).",
        "Part du CA réalisée par le premier canal (détail par canal)", "%", ("canal", "montant_ht"), sectors=("commerce", "hotellerie_restauration", "agroalimentaire", "tic"), priority=3),
    KPI("taux_impayes", "commercial", "Taux d'impayés", "Part du CA non encore encaissée.",
        "CA non réglé / CA total", "%", ("montant_ht", "statut_paiement"), priority=1,
        higher_is_better=False, warning=15, critical=30),
    KPI("creances_echues", "commercial", "Créances échues", "Montant des ventes non réglées dont l'échéance est dépassée.",
        "Somme(montant HT non réglé dont échéance < aujourd'hui)", "MAD", ("montant_ht", "statut_paiement", "date_echeance"),
        priority=2, higher_is_better=False),
    KPI("realisation_objectif", "commercial", "Taux de réalisation des objectifs", "CA réalisé comparé à l'objectif fixé.",
        "CA HT / objectif", "%", ("montant_ht", "objectif"), sizes=PME_GE, priority=1, warning=90, critical=75),

    # ---------------------------------------------------------------- Production
    KPI("volume_produit", "production", "Volume produit", "Quantité totale produite sur la période.",
        "Somme(quantité produite)", "nombre", ("quantite_produite",), sectors=PRODUCING, priority=1),
    KPI("evolution_production", "production", "Évolution de la production", "Variation de la production du dernier mois.",
        "(Production M − Production M−1) / Production M−1", "%", ("date", "quantite_produite"), sectors=PRODUCING, priority=2),
    KPI("realisation_production", "production", "Taux de réalisation du plan", "Production réalisée comparée à l'objectif.",
        "Quantité produite / objectif", "%", ("quantite_produite", "objectif"), sectors=PRODUCING, priority=1, warning=90, critical=75),
    KPI("taux_rebut", "production", "Taux de rebut", "Part de la production non conforme.",
        "Rebuts / (quantité produite + rebuts)", "%", ("quantite_produite", "quantite_rebut"), sectors=PRODUCING, priority=1,
        higher_is_better=False, warning=3, critical=5),
    KPI("taux_disponibilite", "production", "Disponibilité des équipements", "Part du temps planifié où les machines ont réellement fonctionné.",
        "(Temps planifié − temps d'arrêt) / temps planifié", "%", ("temps_planifie", "temps_arret"), sectors=PRODUCING, priority=1,
        warning=85, critical=75),
    KPI("trs", "production", "TRS (OEE)", "Taux de rendement synthétique : disponibilité × performance × qualité.",
        "Disponibilité × (production réelle / production théorique) × taux de qualité", "%",
        ("temps_planifie", "temps_arret", "quantite_produite", "quantite_rebut", "cadence_theorique"),
        sectors=("industrie", "agroalimentaire", "textile"), sizes=PME_GE, priority=1, warning=65, critical=50),
    KPI("temps_arret_total", "production", "Temps d'arrêt total", "Heures perdues en pannes, réglages et arrêts.",
        "Somme(temps d'arrêt)", "heures", ("temps_arret",), sectors=PRODUCING, priority=2, higher_is_better=False),
    KPI("cout_unitaire_production", "production", "Coût de revient unitaire", "Coût moyen d'une unité produite.",
        "Coût de production / quantité produite", "MAD", ("cout_production", "quantite_produite"), sectors=PRODUCING, priority=1,
        higher_is_better=False),
    KPI("production_par_ligne", "production", "Production par ligne / machine", "Comparaison des volumes entre lignes ou ateliers.",
        "Production de la ligne la plus productive (détail par ligne)", "nombre", ("ligne", "quantite_produite"), sectors=PRODUCING, sizes=PME_GE, priority=2),
    KPI("production_par_produit", "production", "Production par produit", "Répartition des volumes par produit.",
        "Production du produit le plus fabriqué (détail par produit)", "nombre", ("produit", "quantite_produite"), sectors=PRODUCING, priority=3),

    # ---------------------------------------------------------------- Stock
    KPI("valeur_stock", "stock", "Valeur du stock", "Valeur totale du stock au coût unitaire.",
        "Somme(quantité × coût unitaire)", "MAD", ("quantite_stock", "cout_unitaire"), sectors=WITH_STOCK, priority=1),
    KPI("nb_articles", "stock", "Nombre d'articles", "Nombre de références distinctes en stock.",
        "Nombre d'articles distincts", "nombre", ("article",), sectors=WITH_STOCK, priority=2),
    KPI("articles_sous_seuil", "stock", "Articles sous le seuil d'alerte", "Références à réapprovisionner.",
        "Nombre d'articles où quantité ≤ stock minimum", "nombre", ("article", "quantite_stock", "stock_minimum"),
        sectors=WITH_STOCK, priority=1, higher_is_better=False),
    KPI("taux_rupture", "stock", "Taux de rupture", "Part des articles dont le stock est à zéro.",
        "Articles à stock nul / nombre d'articles", "%", ("article", "quantite_stock"), sectors=WITH_STOCK, priority=1,
        higher_is_better=False, warning=5, critical=10),
    KPI("rotation_stock", "stock", "Rotation du stock", "Nombre de fois où le stock est renouvelé sur la période.",
        "Sorties / stock moyen", "ratio", ("sorties", "quantite_stock"), sectors=WITH_STOCK, priority=1,
        boost=("commerce", "agroalimentaire")),
    KPI("couverture_stock", "stock", "Couverture du stock", "Nombre de jours de consommation couverts par le stock actuel.",
        "Stock / consommation moyenne journalière", "jours", ("date", "sorties", "quantite_stock"), sectors=WITH_STOCK,
        sizes=PME_GE, priority=2),
    KPI("stock_dormant", "stock", "Stock dormant", "Articles en stock sans aucune sortie sur la période.",
        "Nombre d'articles avec stock > 0 et sorties = 0", "nombre", ("article", "quantite_stock", "sorties"),
        sectors=WITH_STOCK, priority=2, higher_is_better=False),
    KPI("valeur_par_categorie", "stock", "Valeur du stock par famille", "Répartition de la valeur du stock par catégorie.",
        "Part de la valeur du stock dans la première famille (détail par famille)", "%", ("categorie", "quantite_stock", "cout_unitaire"),
        sectors=WITH_STOCK, sizes=PME_GE, priority=2),
    KPI("valeur_par_entrepot", "stock", "Valeur du stock par entrepôt", "Répartition de la valeur du stock entre les sites.",
        "Part de la valeur du stock dans le premier entrepôt (détail par entrepôt)", "%", ("entrepot", "quantite_stock", "cout_unitaire"),
        sectors=WITH_STOCK, sizes=GE, priority=3),
    KPI("proches_peremption", "stock", "Articles proches de la péremption", "Articles dont la date limite tombe dans les 30 prochains jours.",
        "Nombre d'articles avec péremption < aujourd'hui + 30 j", "nombre", ("article", "date_peremption"),
        sectors=PERISHABLE, priority=1, higher_is_better=False),

    # ---------------------------------------------------------------- RH
    KPI("effectif_total", "rh", "Effectif", "Nombre de salariés présents.",
        "Nombre de salariés sans date de sortie", "nombre", ("nom",), priority=1),
    KPI("repartition_contrats", "rh", "Répartition par type de contrat", "CDI, CDD, intérim, stagiaires, ANAPEC...",
        "Part des CDI dans l'effectif (détail par type de contrat)", "%", ("type_contrat",), priority=1,
        higher_is_better=None),
    KPI("nb_stagiaires", "rh", "Stagiaires", "Nombre de stagiaires présents.",
        "Nombre de salariés dont le contrat est un stage", "nombre", ("type_contrat",), priority=1),
    KPI("recrutements", "rh", "Recrutements (nouveaux postes)", "Nombre d'embauches sur les 12 derniers mois.",
        "Nombre de dates d'embauche dans les 12 derniers mois", "nombre", ("date_embauche",), priority=1),
    KPI("turnover", "rh", "Taux de rotation (turnover)", "Part des départs dans l'effectif sur 12 mois.",
        "((entrées + sorties) / 2) / effectif moyen", "%", ("date_embauche", "date_sortie"), sizes=PME_GE, priority=1,
        higher_is_better=False, warning=15, critical=25),
    KPI("masse_salariale", "rh", "Masse salariale mensuelle", "Total des salaires bruts mensuels.",
        "Somme(salaire brut)", "MAD", ("salaire_brut",), priority=1, higher_is_better=None),
    KPI("salaire_moyen", "rh", "Salaire moyen", "Salaire brut mensuel moyen.",
        "Masse salariale / effectif", "MAD", ("salaire_brut",), priority=2, higher_is_better=None),
    KPI("taux_absenteisme", "rh", "Taux d'absentéisme", "Part des jours travaillables perdus en absences.",
        "Jours d'absence / (effectif × jours ouvrables de la période)", "%", ("jours_absence",), priority=1,
        higher_is_better=False, warning=4, critical=7),
    KPI("solde_conges", "rh", "Solde de congés", "Jours de congé restant à prendre (risque de provision et d'organisation).",
        "Somme(congés acquis − congés pris)", "jours", ("jours_conges_acquis", "jours_conges_pris"), priority=2,
        higher_is_better=None),
    KPI("effectif_par_departement", "rh", "Effectif par département", "Répartition des salariés par service.",
        "Nombre de salariés par département", "nombre", ("departement",), sizes=PME_GE, priority=2),
    KPI("parite", "rh", "Parité femmes / hommes", "Part des femmes dans l'effectif.",
        "Effectif féminin / effectif total", "%", ("sexe",), sizes=PME_GE, priority=2, higher_is_better=None),
    KPI("anciennete_moyenne", "rh", "Ancienneté moyenne", "Ancienneté moyenne des salariés présents.",
        "Moyenne(aujourd'hui − date d'embauche)", "mois", ("date_embauche",), priority=2, higher_is_better=None),
    KPI("age_moyen", "rh", "Âge moyen", "Âge moyen des salariés présents.",
        "Moyenne(aujourd'hui − date de naissance)", "ans", ("date_naissance",), sizes=PME_GE, priority=3, higher_is_better=None),
    KPI("formation_par_salarie", "rh", "Heures de formation par salarié", "Effort de développement des compétences.",
        "Heures de formation / effectif", "heures", ("heures_formation",), sizes=PME_GE, priority=3),

    # ---------------------------------------------------------------- Trésorerie
    KPI("solde_tresorerie", "tresorerie", "Solde de trésorerie", "Dernier solde connu, tous comptes confondus.",
        "Dernier solde par compte, additionné", "MAD", ("date", "solde"), priority=1, warning=0, critical=0),
    KPI("flux_net", "tresorerie", "Flux de trésorerie net", "Différence entre encaissements et décaissements.",
        "Somme(encaissements) − somme(décaissements)", "MAD", ("encaissement", "decaissement"), priority=1),
    KPI("total_encaissements", "tresorerie", "Total des encaissements", "Entrées d'argent sur la période.",
        "Somme(encaissements)", "MAD", ("encaissement",), priority=1),
    KPI("total_decaissements", "tresorerie", "Total des décaissements", "Sorties d'argent sur la période.",
        "Somme(décaissements)", "MAD", ("decaissement",), priority=1, higher_is_better=False),
    KPI("evolution_tresorerie", "tresorerie", "Évolution mensuelle de la trésorerie", "Flux net mois par mois.",
        "Encaissements − décaissements par mois", "MAD", ("date", "encaissement", "decaissement"), priority=1),
    KPI("decaissements_mensuels_moyens", "tresorerie", "Décaissements mensuels moyens", "Besoin de trésorerie moyen par mois (burn rate).",
        "Moyenne mensuelle des décaissements", "MAD", ("date", "decaissement"), priority=2, higher_is_better=False),
    KPI("autonomie_tresorerie", "tresorerie", "Autonomie de trésorerie", "Nombre de mois couverts par la trésorerie disponible sans nouvel encaissement.",
        "Solde actuel / décaissements mensuels moyens", "mois", ("date", "solde", "decaissement"), priority=1,
        warning=3, critical=1),
    KPI("solde_par_banque", "tresorerie", "Solde par banque", "Répartition de la trésorerie entre les comptes.",
        "Dernier solde par banque", "MAD", ("banque", "date", "solde"), sizes=PME_GE, priority=2),
    KPI("decaissements_par_categorie", "tresorerie", "Décaissements par catégorie", "Principaux postes de dépenses.",
        "Part du premier poste dans les décaissements (détail par catégorie)", "%", ("categorie", "decaissement"), priority=2),

    # ---------------------------------------------------------------- Comptabilité (balance PCM)
    KPI("ca_comptable", "comptabilite", "Chiffre d'affaires (comptes 71)", "Ventes de marchandises, de biens et de services produits.",
        "Solde créditeur des comptes 711 + 712", "MAD", ("compte", "debit", "credit"), priority=1),
    KPI("resultat_net", "comptabilite", "Résultat net", "Bénéfice ou perte de l'exercice.",
        "Produits (classe 7) − charges (classe 6)", "MAD", ("compte", "debit", "credit"), priority=1, warning=0, critical=0),
    KPI("marge_nette", "comptabilite", "Marge nette", "Rentabilité finale des ventes.",
        "Résultat net / chiffre d'affaires", "%", ("compte", "debit", "credit"), priority=1, warning=3, critical=0),
    KPI("valeur_ajoutee", "comptabilite", "Valeur ajoutée", "Richesse créée par l'entreprise.",
        "Production de l'exercice − consommations de l'exercice (comptes 71 − 61)", "MAD", ("compte", "debit", "credit"), priority=2),
    KPI("ebe", "comptabilite", "Excédent brut d'exploitation (EBE)", "Performance économique avant amortissements et financement.",
        "Valeur ajoutée + subventions − impôts et taxes − charges de personnel", "MAD", ("compte", "debit", "credit"), priority=1),
    KPI("poids_charges_personnel", "comptabilite", "Poids des charges de personnel", "Part du CA consacrée aux salaires et charges sociales.",
        "Comptes 617 / chiffre d'affaires", "%", ("compte", "debit", "credit"), priority=2, higher_is_better=False,
        boost=("services", "tic", "hotellerie_restauration")),
    KPI("fonds_roulement", "comptabilite", "Fonds de roulement", "Ressources stables disponibles après financement de l'actif immobilisé.",
        "Financement permanent (classe 1) − actif immobilisé (classe 2)", "MAD", ("compte", "debit", "credit"), priority=1,
        warning=0, critical=0),
    KPI("bfr", "comptabilite", "Besoin en fonds de roulement", "Argent immobilisé par le cycle d'exploitation (stocks + créances − dettes).",
        "Actif circulant (classe 3) − passif circulant (classe 4)", "MAD", ("compte", "debit", "credit"), priority=1,
        higher_is_better=False),
    KPI("tresorerie_nette", "comptabilite", "Trésorerie nette", "Fonds de roulement − BFR.",
        "Trésorerie actif (classe 5 débitrice) − trésorerie passif (classe 5 créditrice)", "MAD", ("compte", "debit", "credit"),
        priority=1, warning=0, critical=0),
    KPI("liquidite_generale", "comptabilite", "Ratio de liquidité générale", "Capacité à payer les dettes à court terme avec l'actif circulant.",
        "(Classe 3 + trésorerie actif) / (classe 4 + trésorerie passif)", "ratio", ("compte", "debit", "credit"),
        sizes=PME_GE, priority=2, warning=1.2, critical=1),
    KPI("endettement", "comptabilite", "Ratio d'endettement", "Poids des dettes de financement par rapport aux capitaux propres.",
        "Dettes de financement (14) / capitaux propres", "ratio", ("compte", "debit", "credit"),
        sizes=PME_GE, priority=2, higher_is_better=False, warning=1, critical=2),
    KPI("taux_ebe", "comptabilite", "Taux d'EBE", "Part du chiffre d'affaires transformée en excédent brut d'exploitation.",
        "EBE / chiffre d'affaires", "%", ("compte", "debit", "credit"), priority=2, warning=8, critical=3),
    KPI("capacite_autofinancement", "comptabilite", "Capacité d'autofinancement (CAF)", "Ressources internes dégagées pour investir et rembourser.",
        "Résultat net + dotations − reprises", "MAD", ("compte", "debit", "credit"), sizes=PME_GE, priority=2,
        warning=0, critical=0),
    KPI("rentabilite_financiere", "comptabilite", "Rentabilité financière (ROE)", "Rendement des capitaux investis par les associés.",
        "Résultat net / capitaux propres", "%", ("compte", "debit", "credit"), sizes=PME_GE, priority=2, warning=5, critical=0),
    KPI("autonomie_financiere", "comptabilite", "Autonomie financière", "Part du bilan financée par les capitaux propres.",
        "Capitaux propres / total du bilan", "%", ("compte", "debit", "credit"), sizes=PME_GE, priority=3, warning=30, critical=20),
    KPI("delai_clients", "comptabilite", "Délai de paiement clients", "Nombre moyen de jours avant l'encaissement des clients (délai légal : 60 jours par défaut).",
        "Clients (342) / CA TTC × 360", "jours", ("compte", "debit", "credit"), priority=1, higher_is_better=False,
        warning=60, critical=90, boost=("commerce", "services")),
    KPI("delai_fournisseurs", "comptabilite", "Délai de paiement fournisseurs", "Nombre moyen de jours avant le paiement des fournisseurs (plafond légal : 120 jours).",
        "Fournisseurs (441) / achats TTC × 360", "jours", ("compte", "debit", "credit"), priority=2, higher_is_better=False,
        warning=60, critical=120),
]

KPI_BY_CODE: dict[str, KPI] = {k.code: k for k in KPIS}
