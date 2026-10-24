"""Rédaction gratuite du rapport, sans IA, à partir de règles d'expert.

Chaque indicateur calculé est interprété selon son statut (seuils de référence), sa tendance et
le détail de son graphique ; des recommandations types sont déclenchées par les indicateurs en
alerte. Le résultat a exactement la même structure que le rapport rédigé par Claude, ce qui permet
de réutiliser l'affichage et les exports PDF / Word.
"""
from ..schemas import DashboardDataOut, KpiValueOut
from .context import _threshold
from .formatting import fmt_value

ENGINE_NAME = "Vision Board — analyse automatique"

# Formulations par domaine : titre du rapport et complément « en matière de … ».
TITLES = {
    "commercial": ("Analyse commerciale", "d'activité commerciale"),
    "production": ("Analyse de la production", "de production"),
    "stock": ("Analyse des stocks", "de gestion des stocks"),
    "rh": ("Analyse des ressources humaines", "de ressources humaines"),
    "tresorerie": ("Analyse de la trésorerie", "de trésorerie"),
    "comptabilite": ("Analyse financière", "financiers"),
}


def _de(name: str) -> str:
    """« de Société » ou « d'Atlas » selon la première lettre."""
    return f"d'{name}" if name[:1].lower() in "aeiouyhéèêàâîôû" else f"de {name}"


def _sentence(text: str) -> str:
    text = text.strip()
    return (text[:1].upper() + text[1:]).rstrip(".") + "." if text else ""

# Regroupement des indicateurs en thèmes d'analyse, par domaine.
THEMES: dict[str, list[tuple[str, list[str]]]] = {
    "commercial": [
        ("Activité et croissance", ["ca_total", "ca_evolution", "nb_ventes", "panier_moyen", "quantite_vendue",
                                    "realisation_objectif"]),
        ("Clientèle et risque client", ["nb_clients_actifs", "nouveaux_clients", "concentration_clients",
                                        "taux_impayes", "creances_echues"]),
        ("Rentabilité commerciale", ["marge_brute"]),
        ("Organisation commerciale et offre", ["ca_par_commercial", "nb_commerciaux", "ca_par_region", "ca_par_canal",
                                               "top_produits"]),
    ],
    "production": [
        ("Volumes et respect du plan", ["volume_produit", "evolution_production", "realisation_production",
                                        "production_par_ligne", "production_par_produit"]),
        ("Performance des équipements", ["trs", "taux_disponibilite", "temps_arret_total"]),
        ("Qualité et coûts", ["taux_rebut", "cout_unitaire_production"]),
    ],
    "stock": [
        ("Niveau et valeur du stock", ["valeur_stock", "nb_articles", "valeur_par_categorie", "valeur_par_entrepot"]),
        ("Disponibilité des articles", ["articles_sous_seuil", "taux_rupture", "couverture_stock"]),
        ("Rotation, stock dormant et péremption", ["rotation_stock", "stock_dormant", "proches_peremption"]),
    ],
    "rh": [
        ("Effectif et structure", ["effectif_total", "repartition_contrats", "nb_stagiaires", "effectif_par_departement",
                                   "parite", "age_moyen", "anciennete_moyenne"]),
        ("Mouvements du personnel", ["recrutements", "turnover"]),
        ("Rémunérations", ["masse_salariale", "salaire_moyen"]),
        ("Absences, congés et formation", ["taux_absenteisme", "solde_conges", "formation_par_salarie"]),
    ],
    "tresorerie": [
        ("Niveau de trésorerie", ["solde_tresorerie", "solde_par_banque", "autonomie_tresorerie"]),
        ("Flux de trésorerie", ["flux_net", "total_encaissements", "total_decaissements", "evolution_tresorerie",
                                "decaissements_mensuels_moyens", "decaissements_par_categorie"]),
    ],
    "comptabilite": [
        ("Activité et rentabilité", ["ca_comptable", "valeur_ajoutee", "ebe", "taux_ebe", "resultat_net",
                                     "marge_nette", "poids_charges_personnel", "capacite_autofinancement"]),
        ("Équilibre financier", ["fonds_roulement", "bfr", "tresorerie_nette", "liquidite_generale"]),
        ("Structure financière et délais de paiement", ["endettement", "autonomie_financiere",
                                                         "rentabilite_financiere", "delai_clients",
                                                         "delai_fournisseurs"]),
    ],
}

# Recommandations types déclenchées par un indicateur en alerte : (action, justification, horizon).
ADVICE: dict[str, tuple[str, str, str]] = {
    "concentration_clients": ("Diversifier le portefeuille clients",
                              "Une forte dépendance à quelques clients expose l'entreprise à la perte d'un compte majeur ; "
                              "prospecter de nouveaux clients et développer les clients secondaires.", "3 à 12 mois"),
    "taux_impayes": ("Renforcer le recouvrement des créances",
                     "Mettre en place des relances systématiques (J+7, J+30), exiger des acomptes pour les clients à risque "
                     "et suivre chaque semaine la liste des factures non réglées.", "immédiat"),
    "creances_echues": ("Relancer en priorité les factures échues",
                        "Les créances échues pèsent directement sur la trésorerie ; traiter d'abord les montants les plus "
                        "élevés et les plus anciens.", "immédiat"),
    "marge_brute": ("Restaurer la marge brute",
                    "Renégocier les prix d'achat, revoir la politique tarifaire et concentrer l'effort commercial sur les "
                    "produits les plus rentables.", "moins de 3 mois"),
    "realisation_objectif": ("Analyser l'écart aux objectifs de vente",
                             "Identifier les commerciaux, régions ou produits en retard et ajuster le plan d'action ou les "
                             "objectifs.", "moins de 3 mois"),
    "realisation_production": ("Fiabiliser la planification de la production",
                               "Analyser les causes de l'écart au plan (pannes, approvisionnements, effectifs) ligne par "
                               "ligne.", "moins de 3 mois"),
    "taux_rebut": ("Lancer un plan d'amélioration de la qualité",
                   "Identifier les lignes et produits les plus concernés, analyser les causes (matières, réglages, "
                   "formation) et suivre le taux de rebut chaque semaine.", "moins de 3 mois"),
    "taux_disponibilite": ("Réduire les arrêts des équipements",
                           "Mettre en place une maintenance préventive et analyser les pannes récurrentes.",
                           "moins de 3 mois"),
    "trs": ("Améliorer le rendement des lignes (TRS)",
            "Agir sur les trois leviers : disponibilité (pannes), performance (cadences) et qualité (rebuts).",
            "3 à 12 mois"),
    "taux_rupture": ("Prévenir les ruptures de stock",
                     "Revoir les seuils de réapprovisionnement et le suivi des articles les plus vendus.", "immédiat"),
    "articles_sous_seuil": ("Réapprovisionner les articles sous le seuil d'alerte",
                            "Passer les commandes nécessaires pour éviter les ruptures et les ventes perdues.", "immédiat"),
    "stock_dormant": ("Écouler le stock dormant",
                      "Promotions, retours fournisseurs ou déstockage pour libérer de la trésorerie et de la place.",
                      "moins de 3 mois"),
    "proches_peremption": ("Écouler en priorité les articles proches de la péremption",
                           "Appliquer le « premier périmé, premier sorti » et des promotions ciblées pour limiter les "
                           "pertes.", "immédiat"),
    "turnover": ("Fidéliser les collaborateurs",
                 "Analyser les départs (entretiens de sortie), revoir les conditions de travail, la rémunération et les "
                 "perspectives d'évolution.", "3 à 12 mois"),
    "taux_absenteisme": ("Analyser et réduire l'absentéisme",
                         "Identifier les services concernés, les causes (santé, organisation, climat social) et mettre en "
                         "place un suivi mensuel.", "moins de 3 mois"),
    "solde_tresorerie": ("Rétablir un solde de trésorerie positif",
                         "Accélérer les encaissements, différer les dépenses non essentielles et négocier une ligne de "
                         "crédit de trésorerie avec la banque.", "immédiat"),
    "autonomie_tresorerie": ("Construire une prévision de trésorerie à 3 mois",
                             "La trésorerie couvre peu de mois de dépenses : anticiper les échéances, sécuriser les "
                             "financements et suivre la position chaque semaine.", "immédiat"),
    "resultat_net": ("Mettre en place un plan de retour à la rentabilité",
                     "Analyser les postes de charges les plus lourds et les marges par activité pour identifier les "
                     "économies et les hausses de prix possibles.", "moins de 3 mois"),
    "marge_nette": ("Améliorer la rentabilité des ventes",
                    "Agir sur les prix de vente, les coûts d'achat et les charges de structure.", "3 à 12 mois"),
    "taux_ebe": ("Améliorer la performance d'exploitation",
                 "L'excédent brut d'exploitation est faible au regard du chiffre d'affaires : revoir les charges externes "
                 "et la productivité.", "3 à 12 mois"),
    "capacite_autofinancement": ("Restaurer la capacité d'autofinancement",
                                 "Sans autofinancement, les investissements et remboursements dépendent de financements "
                                 "externes.", "3 à 12 mois"),
    "fonds_roulement": ("Renforcer les ressources stables",
                        "Un fonds de roulement négatif signifie que des immobilisations sont financées à court terme : "
                        "envisager un apport en capital ou un emprunt à moyen terme.", "3 à 12 mois"),
    "tresorerie_nette": ("Réduire le besoin en fonds de roulement",
                         "Raccourcir les délais clients, optimiser les stocks et négocier les délais fournisseurs.",
                         "moins de 3 mois"),
    "liquidite_generale": ("Sécuriser la liquidité à court terme",
                           "Les actifs à court terme couvrent difficilement les dettes à court terme : surveiller les "
                           "échéances et la trésorerie.", "immédiat"),
    "endettement": ("Maîtriser l'endettement",
                    "Limiter les nouveaux emprunts et privilégier l'autofinancement ou le renforcement des fonds propres.",
                    "3 à 12 mois"),
    "autonomie_financiere": ("Renforcer les capitaux propres",
                             "Mise en réserve des bénéfices ou augmentation de capital pour améliorer la solidité "
                             "financière.", "3 à 12 mois"),
    "rentabilite_financiere": ("Améliorer la rentabilité des capitaux investis",
                               "La rentabilité des fonds propres est faible : agir sur les marges et l'utilisation des "
                               "actifs.", "3 à 12 mois"),
    "delai_clients": ("Réduire le délai de paiement des clients",
                      "Le délai dépasse la référence légale de 60 jours : facturer plus tôt, relancer systématiquement et "
                      "appliquer les pénalités de retard prévues par la loi.", "moins de 3 mois"),
    "delai_fournisseurs": ("Respecter les délais de paiement fournisseurs",
                           "Des délais trop longs exposent aux pénalités prévues par la loi et dégradent la relation "
                           "fournisseurs : planifier les règlements.", "moins de 3 mois"),
}

# Indicateurs de comptage sans seuil, en alerte dès qu'ils sont positifs.
COUNT_ALERTS = {"articles_sous_seuil", "stock_dormant", "proches_peremption", "creances_echues"}

STATUS_PHRASE = {
    "ok": "Le niveau est satisfaisant au regard de la référence ({seuil}).",
    "warning": "Ce niveau appelle une vigilance ({seuil}).",
    "critical": "Ce niveau est critique ({seuil}).",
}


def _alert_level(k: KpiValueOut) -> str | None:
    if k.status in ("warning", "critical"):
        return k.status
    if k.code in COUNT_ALERTS and (k.value or 0) > 0:
        return "warning"
    return None


def _trend_sentence(k: KpiValueOut) -> str | None:
    if k.delta is None or k.higher_is_better is None or abs(k.delta) < 0.5:
        return None
    good = (k.delta > 0) == k.higher_is_better
    sens = "hausse" if k.delta > 0 else "baisse"
    return (f"Sur le dernier mois, l'indicateur est en {sens} de {abs(k.delta):.1f} %".replace(".", ",")
            + (", une évolution favorable." if good else ", une évolution défavorable à surveiller."))


def _chart_sentence(k: KpiValueOut) -> str | None:
    chart = k.chart
    if not chart or len(chart.values) < 2:
        return None
    values, labels = chart.values, chart.labels
    if chart.type == "line":
        first, last = values[0], values[-1]
        i_max = max(range(len(values)), key=values.__getitem__)
        i_min = min(range(len(values)), key=values.__getitem__)
        text = (f"{chart.title} : de {fmt_value(first, chart.unit)} ({labels[0]}) à {fmt_value(last, chart.unit)} "
                f"({labels[-1]})")
        if first:
            change = 100 * (last - first) / abs(first)
            text += f", soit {'+' if change > 0 else ''}{change:.1f} % sur la période".replace(".", ",")
        return text + (f" ; point haut en {labels[i_max]} ({fmt_value(values[i_max], chart.unit)}), "
                       f"point bas en {labels[i_min]} ({fmt_value(values[i_min], chart.unit)}).")
    # Certains graphiques gardent un ordre logique (non trié) : on classe avant de commenter.
    ranked = sorted(zip(labels, values), key=lambda lv: lv[1], reverse=True)
    total = sum(v for v in values if v > 0)
    (top, top_value), (low, low_value) = ranked[0], ranked[-1]
    if chart.unit != "%" and total and all(v >= 0 for v in values):
        share = 100 * top_value / total
        second = f", devant {ranked[1][0]} ({fmt_value(ranked[1][1], chart.unit)})" if len(ranked) > 1 else ""
        return (f"{chart.title} : {top} arrive en tête avec {fmt_value(top_value, chart.unit)}, soit "
                f"{share:.0f} % du total{second}.")
    return (f"{chart.title} : le niveau le plus élevé concerne {top} ({fmt_value(top_value, chart.unit)}), "
            f"le plus faible {low} ({fmt_value(low_value, chart.unit)}).")


def _kpi_paragraph(k: KpiValueOut) -> str:
    parts = [f"{k.name} : {fmt_value(k.value, k.unit)}."]
    if k.detail:
        parts.append(_sentence(k.detail))
    if k.status:
        parts.append(STATUS_PHRASE[k.status].format(seuil=_threshold(k.code) or "seuil de référence"))
    elif k.code in COUNT_ALERTS and (k.value or 0) > 0:
        parts.append("Ce point mérite une action rapide.")
    for sentence in (_trend_sentence(k), _chart_sentence(k)):
        if sentence:
            parts.append(sentence)
    return " ".join(parts)


def _comment(k: KpiValueOut) -> str:
    level = _alert_level(k)
    if level == "critical":
        return "Niveau critique : action prioritaire."
    if level == "warning":
        return "À surveiller de près."
    if k.status == "ok":
        return "Niveau satisfaisant."
    trend = _trend_sentence(k)
    return trend if trend else (k.detail or k.description)


def write_rules_report(company_name: str, data: DashboardDataOut, period_text: str) -> dict:
    computed = [k for k in data.kpis if not k.error]
    missing = [k for k in data.kpis if k.error]
    by_code = {k.code: k for k in computed}
    critical = [k for k in computed if _alert_level(k) == "critical"]
    warning = [k for k in computed if _alert_level(k) == "warning"]
    good = [k for k in computed if k.status == "ok"]

    if len(critical) >= 2:
        assessment = "préoccupante"
    elif critical or len(warning) >= 2 or warning:
        assessment = "à surveiller"
    else:
        assessment = "favorable"

    title, about = TITLES[data.domain]
    headline = computed[0]
    of_company = _de(company_name)
    synthese = [
        f"Ce rapport analyse le tableau de bord « {data.title} » {of_company}, {period_text}. "
        f"{len(computed)} indicateurs ont pu être calculés à partir des données importées.",
        f"Indicateur principal : {headline.name} de {fmt_value(headline.value, headline.unit)}.",
    ]
    if good:
        synthese.append("Points satisfaisants : " + ", ".join(f"{k.name} ({fmt_value(k.value, k.unit)})"
                                                               for k in good[:4]) + ".")
    if critical:
        synthese.append("Situations critiques : " + ", ".join(f"{k.name} ({fmt_value(k.value, k.unit)})"
                                                               for k in critical) + ".")
    if warning:
        synthese.append("À surveiller : " + ", ".join(f"{k.name} ({fmt_value(k.value, k.unit)})"
                                                       for k in warning[:5]) + ".")
    synthese.append({"favorable": "Dans l'ensemble, la situation est saine sur ce périmètre.",
                     "à surveiller": "Dans l'ensemble, la situation est correcte mais plusieurs points demandent une "
                                     "attention particulière.",
                     "préoccupante": "Dans l'ensemble, la situation est préoccupante et appelle des actions rapides."}[
                        assessment])

    # Chiffres clés : les alertes d'abord, puis les premiers indicateurs du tableau.
    key = (critical + warning + [k for k in computed if k not in critical and k not in warning])[:6]
    chiffres = [{"indicateur": k.name, "valeur": fmt_value(k.value, k.unit), "commentaire": _comment(k)} for k in key]

    sections = []
    placed = set()
    for theme, codes in THEMES.get(data.domain, []):
        paragraphs = [_kpi_paragraph(by_code[c]) for c in codes if c in by_code]
        placed.update(c for c in codes if c in by_code)
        if paragraphs:
            sections.append({"titre": theme, "paragraphes": paragraphs})
    others = [k for k in computed if k.code not in placed]
    if others:
        sections.append({"titre": "Autres indicateurs", "paragraphes": [_kpi_paragraph(k) for k in others]})

    points_forts = [f"{k.name} : {fmt_value(k.value, k.unit)}, niveau satisfaisant." for k in good]
    points_forts += [f"{k.name} : {_trend_sentence(k)}" for k in computed
                     if k not in good and k.delta is not None and k.higher_is_better is not None
                     and (k.delta > 0) == k.higher_is_better and _trend_sentence(k)]
    vigilance = [f"{k.name} : {fmt_value(k.value, k.unit)}" + (" (critique)." if _alert_level(k) == "critical" else ".")
                 for k in critical + warning]
    vigilance += [f"{k.name} : {_trend_sentence(k)}" for k in computed
                  if k not in critical and k not in warning and k.delta is not None and k.higher_is_better is not None
                  and (k.delta > 0) != k.higher_is_better and _trend_sentence(k)]

    recommendations = []
    for k in critical + warning:
        if k.code in ADVICE:
            action, why, horizon = ADVICE[k.code]
            recommendations.append({"priorite": "haute" if _alert_level(k) == "critical" else "moyenne",
                                    "action": action, "justification": f"{k.name} : {fmt_value(k.value, k.unit)}. {why}",
                                    "horizon": horizon})
    if missing:
        recommendations.append({
            "priorite": "basse", "action": "Compléter les données importées",
            "justification": f"{len(missing)} indicateur(s) n'ont pas pu être calculés faute de données : "
                             + ", ".join(k.name for k in missing[:6]) + ".",
            "horizon": "moins de 3 mois"})
    recommendations.append({
        "priorite": "basse", "action": "Suivre ce tableau de bord chaque mois",
        "justification": "Mettre à jour les fichiers chaque mois permet de repérer les dérives tôt et de mesurer "
                         "l'effet des actions engagées.", "horizon": "immédiat"})

    limits = [f"{k.name} : {k.error.lower()}." for k in missing]
    limits.append("Analyse produite automatiquement à partir de règles et de seuils de référence génériques ; elle ne "
                  "remplace pas l'avis d'un expert sur le contexte propre à l'entreprise.")

    conclusion = {
        "favorable": f"Les indicateurs {about} {of_company} sont globalement bien orientés. L'enjeu est de maintenir "
                     "ces niveaux et de poursuivre le suivi mensuel.",
        "à surveiller": f"Les indicateurs {about} {of_company} sont globalement corrects, mais plusieurs s'écartent "
                        "des références : les recommandations prioritaires ci-dessus permettent de les corriger.",
        "préoccupante": f"Plusieurs indicateurs {about} {of_company} sont à un niveau critique. Les actions de "
                        "priorité haute doivent être engagées sans attendre et suivies de près.",
    }[assessment]

    return {
        "titre": f"{title} — {company_name}",
        "appreciation_globale": assessment,
        "synthese": " ".join(synthese),
        "chiffres_cles": chiffres,
        "sections": sections,
        "points_forts": points_forts or ["Aucun indicateur n'atteint encore le niveau de référence."],
        "points_de_vigilance": vigilance or ["Aucun indicateur en alerte sur la période."],
        "recommandations": recommendations,
        "limites_des_donnees": limits,
        "conclusion": conclusion,
    }
