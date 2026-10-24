# Vision Board

Application web multi-utilisateurs de **tableaux de bord et d'aide à la décision**.
Elle choisit automatiquement les indicateurs (KPI) adaptés au **secteur d'activité**, à la **taille**
de l'entreprise et au **type de tableau de bord** demandé, à partir de fichiers importés (CSV, Excel, et PDF à venir).

## Architecture

```
backend/    API Python (FastAPI, SQLAlchemy, pandas)
  app/kpi/        référentiels, champs standard, catalogue de KPI, moteur de recommandation
  app/kpi/calc/   calcul des KPI, un fichier par domaine (commercial, production, stock, rh, tresorerie, comptabilite)
  app/kpi/accounting.py  états financiers CGNC (repris de Daftar Compta) ; app/kpi/pcm.py : plan comptable
  app/reports/    rapports IA : contexte transmis, rédaction par Claude, exports PDF et Word
  app/importers/  lecture CSV / Excel et reconnaissance automatique des colonnes
  app/routers/    authentification, sociétés et membres, fichiers importés, KPI et tableaux de bord
  tests/          tests automatisés (pytest)
frontend/   interface React + TypeScript (Vite)
exemples/   fichiers fictifs de démonstration, un dossier par société (atlas_distribution,
            atlas_biscuiterie) : ventes, production, stocks, personnel, trésorerie, balance
```

## Démarrer l'application

- **Double-clic sur `demarrer.bat`** (racine du projet) : ouvre une fenêtre « Vision Board » et le navigateur.
  Fermer cette fenêtre arrête l'application.
- Ou, dans un terminal à la racine du projet : `npm start` (Ctrl+C pour arrêter).

L'application est alors disponible sur http://localhost:5173. Si la page affiche « Le serveur de Vision Board
ne répond pas », c'est que l'application n'est pas démarrée.

## Lancer en local (détail)

Backend (port 8000) :

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000
```

Frontend (port 5173) :

```bash
cd frontend
npm install
npm run dev
```

Puis ouvrir http://localhost:5173. La documentation de l'API est disponible sur http://localhost:8000/docs.

Tests du backend :

```bash
cd backend
.venv/Scripts/python -m pytest
```

## Page d'accueil

Les visiteurs non connectés arrivent sur une page de présentation (`/bienvenue`) avec une vidéo explicative
animée en 4 étapes. Pour utiliser une vraie vidéo à la place, déposez un fichier `frontend/public/intro.mp4` :
elle est lue automatiquement (en boucle, sans le son).

## Ajouter des données

Pour chaque type de données (ventes, production, stocks, personnel, trésorerie, comptabilité), l'application
guide l'utilisateur :

- **Forme attendue** : colonnes essentielles et facultatives, format (date JJ/MM/AAAA, nombre…), exemple et
  indicateurs alimentés par chaque colonne, plus un aperçu d'un fichier type ;
- **Modèles** Excel (avec une feuille d'explications) et CSV à télécharger, prêts à remplir ;
- **Saisie dans l'application** : tableau éditable (copier-coller depuis Excel accepté), modifiable ensuite
  depuis « Données importées ».

## Comptes et accès

- **Administrateur** : accès à toutes les sociétés et à la page « Administration », où il gère les sociétés
  (suppression unitaire ou multiple) et crée les comptes
  (e-mail + mot de passe provisoire à communiquer), choisit les sociétés accessibles à chacun, réinitialise
  les mots de passe et désactive les comptes.
- **Utilisateur** : ne voit que les sociétés attribuées, avec un rôle par société — lecteur (consultation),
  éditeur (import, tableaux de bord, rapports) ou propriétaire (gère aussi les membres).
- Chacun peut créer son compte depuis l'écran de connexion (« Pas encore de compte ? Inscrivez-vous ») ;
  le tout premier compte d'une installation devient administrateur. Un nouvel utilisateur ne voit que les
  sociétés qu'il crée ou que l'administrateur lui attribue. Pour réserver la création des comptes à
  l'administrateur : `VISIONBOARD_ALLOW_REGISTRATION=false` dans `backend/.env`.
- Un mot de passe provisoire (créé par l'administrateur) doit être changé à la première connexion.

### Mot de passe administrateur oublié

Le plus simple, depuis la racine du projet : choisir directement un nouveau mot de passe.

```bash
npm run mot-de-passe -- votre@email.ma
```

Ou générer un mot de passe provisoire, depuis le dossier `backend` :

```bash
.venv/Scripts/python -m app.manage reset-password votre@email.ma
```

Un mot de passe provisoire est affiché et enregistré dans `backend/acces_provisoire.txt` ; l'application
demande de le changer à la connexion. `app.manage users` liste les comptes, `app.manage make-admin EMAIL`
donne les droits d'administrateur.

## Jeu de démonstration

```bash
cd backend
.venv/Scripts/python -m app.demo --admin-email votre@email.ma
```

Crée (ou promeut) le compte administrateur, deux utilisateurs, et **12 sociétés d'exemple, une par secteur**
(commerce, agroalimentaire, industrie, textile, BTP, services, TIC, transport, hôtellerie, santé, agriculture,
immobilier), chacune avec tous les tableaux de bord pertinents pour son secteur et des données cohérentes
(fichiers dans `exemples/<société>/`, régénérables avec `backend/.venv/Scripts/python scripts/generer_exemples.py`).
Les identifiants provisoires sont affichés et enregistrés dans `backend/identifiants_demo.txt`.

Pour charger uniquement les sociétés et leurs données, sans toucher aux comptes :

```bash
.venv/Scripts/python -m app.demo --donnees-seulement
```

Le script complète ce qui manque et peut être relancé sans créer de doublons.

## Configuration

Variables d'environnement (ou fichier `backend/.env`), préfixe `VISIONBOARD_` :

| Variable | Rôle | Défaut |
|---|---|---|
| `VISIONBOARD_DATABASE_URL` | Base de données | SQLite `backend/visionboard.db` |
| `VISIONBOARD_SECRET_KEY` | Clé de signature des sessions (**à changer en production**) | valeur de développement |
| `VISIONBOARD_CORS_ORIGINS` | Origines autorisées | `["http://localhost:5173"]` |
| `VISIONBOARD_MAX_UPLOAD_MB` | Taille maximale d'un fichier | 20 |
| `VISIONBOARD_ANTHROPIC_API_KEY` | Clé de l'API Claude pour les rapports d'analyse | aucune (à renseigner) |
| `VISIONBOARD_REPORT_MODEL` | Modèle utilisé pour les rapports | `claude-opus-5-5` |

### Rapports d'analyse : mode gratuit ou IA

Sans aucune configuration, les rapports sont produits **gratuitement** par le moteur d'analyse intégré
(`app/reports/rules.py`) : interprétation de chaque indicateur selon ses seuils, sa tendance et son graphique,
points forts et de vigilance, recommandations types priorisées. Instantané, sans internet ni clé API.

Si une clé API Claude est configurée (ci-dessous), les rapports sont rédigés par l'IA, de façon plus nuancée.
`VISIONBOARD_REPORT_ENGINE` permet de forcer un mode : `auto` (défaut), `regles` ou `claude`.

### Activer les rapports rédigés par l'IA (payant)

1. Créez une clé API sur https://console.anthropic.com (rubrique *API Keys*).
2. Copiez `backend/.env.example` en `backend/.env` et collez la clé après `VISIONBOARD_ANTHROPIC_API_KEY=`.
3. Redémarrez le backend. Le bouton « Rapport d'analyse IA » d'un tableau de bord produit alors un rapport
   (synthèse, analyse, points forts et de vigilance, recommandations priorisées) téléchargeable en PDF et en Word.

L'IA ne reçoit que les indicateurs déjà calculés par l'application (pas les fichiers bruts) ; ces données sont
conservées avec chaque rapport. Chaque rapport consomme des crédits API (quelques centimes à quelques dizaines de
centimes de dollar selon la taille du tableau de bord).

## Feuille de route

1. ✅ Socle : comptes, sociétés et rôles, import CSV/Excel, catalogue de KPI et recommandation
2. ✅ Calcul des KPI et affichage graphique (ECharts) pour le tableau de bord **commercial** (17 KPI, filtre de période, alertes)
3. Import PDF (tableaux, relevés, balances)
4. ✅ Calculs et graphiques des modules Production (10 KPI), Stock (10), RH (14) et Trésorerie (9)
5. ✅ Comptabilité : balance PCM, CPC, soldes de gestion, bilan (CGNC), 15 ratios et 17 KPI
6. ✅ Rapports d'analyse rédigés par l'IA (API Claude, modèle claude-opus-5-5), export PDF / Word
