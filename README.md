# API de gestion d'un atelier de couture

Back-end REST d'un atelier de couture à Dakar : clients et historique de leurs mesures, commandes et
suivi de production, paiements (espèces, Wave, Orange Money…), livraisons, et tableau de bord du patron.

**Pile technique** : Python 3.12 · FastAPI · Pydantic 2 · SQLAlchemy 2 · PostgreSQL 16 · Alembic ·
JWT + Argon2 · pytest · Docker.

## Prérequis

- Python **3.12**
- Docker et Docker Compose

## Lancement rapide (tout dans Docker)

```bash
cp .env.example .env        # puis remplacer les valeurs (mot de passe de la base, SECRET_KEY, compte admin)
docker compose up --build
```

L'API démarre sur <http://localhost:8000> (documentation interactive Swagger : <http://localhost:8000/docs>).
Au démarrage, le conteneur applique les migrations (`alembic upgrade head`), crée l'administrateur et le
catalogue de départ (`python -m app.seed`, sans doublon si on relance), puis lance l'API.

Dans le `.env`, les variables `POSTGRES_USER`, `POSTGRES_PASSWORD` et `POSTGRES_DB` doivent avoir **les mêmes
valeurs** que dans `DATABASE_URL`.

## Installation en local (développement)

Windows (PowerShell) :

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # puis renseigner le .env
```

Linux / macOS :

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # puis renseigner le .env
```

Puis :

```bash
docker compose up -d db          # PostgreSQL seul, publié sur le port 5433 de votre machine
alembic upgrade head             # crée le schéma (aucun create_all)
python -m app.seed               # premier administrateur + catalogue de l'annexe B
uvicorn app.main:app --reload    # API sur http://127.0.0.1:8000
```

### Variables d'environnement (`.env`)

| Variable | Rôle |
|---|---|
| `DATABASE_URL` | Connexion à PostgreSQL (`postgresql+psycopg://utilisateur:mot_de_passe@localhost:5433/base`) |
| `SECRET_KEY` | Clé de signature des jetons JWT (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Durée de validité d'un jeton (60 par défaut) |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Création de la base par le conteneur PostgreSQL |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD`, `ADMIN_NOM_COMPLET` | Compte administrateur créé par `python -m app.seed` |
| `DB_PORT`, `API_PORT` | (facultatif) ports publiés par Docker, 5433 et 8000 par défaut |

Le fichier `.env` n'est jamais versionné ; `.env.example` en est le modèle.

## Comptes de test

Le seul compte créé par le script d'initialisation est l'**administrateur** (`ADMIN_EMAIL` /
`ADMIN_PASSWORD` du `.env`). Il crée ensuite les comptes `accueil` et `tailleur` :

1. Ouvrir <http://localhost:8000/docs>, route `POST /api/v1/auth/login`, se connecter avec
   l'e-mail et le mot de passe de l'administrateur.
2. Cliquer sur **Authorize** (cadenas) et saisir les mêmes identifiants.
3. `POST /api/v1/utilisateurs` avec par exemple :

```json
{"email": "accueil@atelier.sn", "nom_complet": "Awa Accueil", "mot_de_passe": "motdepasse123", "role": "accueil"}
{"email": "tailleur@atelier.sn", "nom_complet": "Mamadou Tailleur", "mot_de_passe": "motdepasse123", "role": "tailleur"}
```

Le déroulé de l'annexe A de l'énoncé (démonstration) est automatisé par `tests/test_scenario_demo.py`.

## Tests

```bash
pytest
```

Les tests utilisent une base PostgreSQL dédiée, **créée automatiquement** à côté de la vôtre
(`<nom_de_la_base>_test`) : les migrations Alembic y sont rejouées (dans les deux sens) au début de la
session, et la base est vidée après chaque test. La base de développement n'est jamais touchée.
PostgreSQL doit donc être démarré (`docker compose up -d db`).

Avec Docker : `docker compose run --rm api pytest`.

## Architecture

```
app/
├── main.py            création de l'application, gestionnaires d'erreurs, /health
├── config.py          variables d'environnement (pydantic-settings)
├── database.py        engine, session, Base, dépendance get_db
├── security.py        hachage Argon2, jetons JWT
├── dependencies.py    get_current_user, exiger_roles(...)
├── exceptions.py      erreurs métier (404, 409, 422…), sans notion de HTTP dans les services
├── erreurs.py         traduction des erreurs en {"detail": "message en français"}
├── seed.py            python -m app.seed
├── models/            tables SQLAlchemy 2 (Mapped, mapped_column)
├── schemas/           schémas Pydantic : Create / Update / Read distincts
├── services/          toute la logique métier (règles de gestion RG1 à RG24)
└── routers/           un fichier par domaine : droits, appel du service, commit
alembic/versions/      migrations (le schéma se crée avec `alembic upgrade head`)
tests/                 pytest + TestClient
```

Les routeurs vérifient les droits, appellent un service puis valident la transaction ; ils ne contiennent
aucune règle de gestion. Les modèles ne sont jamais renvoyés tels quels : chaque réponse passe par un
schéma de lecture (le hash du mot de passe ne sort jamais).

## Droits par rôle

| Rôle | Peut |
|---|---|
| `admin` | tout faire ; seul à gérer les comptes et le catalogue, supprimer un client, annuler un paiement et consulter les statistiques |
| `accueil` | créer/modifier clients et commandes, encaisser, planifier et confirmer les livraisons, annuler une commande |
| `tailleur` | prendre/corriger/supprimer les mesures, faire avancer la production (jamais annuler) |

Tout utilisateur connecté peut consulter clients, mesures, commandes, catalogue et livraisons.
Sans jeton valide : **401** ; rôle insuffisant : **403**.

## Routes réalisées (44 sur 44)

Toutes les routes sont préfixées par `/api/v1`, sauf `/health`.

| Domaine | Routes |
|---|---|
| Santé | `GET /health` (hors préfixe, vérifie la base) |
| Authentification | `POST /auth/login` · `GET /auth/me` |
| Utilisateurs (admin) | `POST /utilisateurs` · `GET /utilisateurs` · `GET /utilisateurs/{id}` · `PATCH /utilisateurs/{id}` |
| Clients | `POST /clients` · `GET /clients` (q, genre, limit, offset) · `GET /clients/{id}` · `PATCH /clients/{id}` · `DELETE /clients/{id}` (admin) · `GET /clients/{id}/commandes` · `GET /clients/{id}/resume` |
| Catalogue | `POST /catalogue` (admin) · `GET /catalogue` (actifs_seulement) · `GET /catalogue/{id}` · `PATCH /catalogue/{id}` (admin) |
| Mesures | `POST /clients/{id}/mesures` · `GET /clients/{id}/mesures` · `GET /clients/{id}/mesures/derniere` · `GET /mesures/{id}` · `PATCH /mesures/{id}` · `DELETE /mesures/{id}` |
| Commandes | `POST /commandes` · `GET /commandes` (statut, client_id, en_retard, date_min, date_max, numero) · `GET /commandes/{id}` · `PATCH /commandes/{id}` · `POST /commandes/{id}/statut` · `GET /commandes/{id}/historique` · `POST /commandes/{id}/lignes` · `DELETE /commandes/{id}/lignes/{ligne_id}` |
| Paiements | `POST /commandes/{id}/paiements` · `GET /commandes/{id}/paiements` · `DELETE /paiements/{id}` (admin) |
| Livraisons | `PUT /commandes/{id}/livraison` · `GET /commandes/{id}/livraison` · `POST /commandes/{id}/livraison/confirmer` · `GET /livraisons` |
| Statistiques (admin) | `GET /statistiques/tableau-de-bord` · `/chiffre-affaires` · `/types-vetement` · `/top-clients` · `/impayes` |

Conventions : erreurs `{"detail": "message en français"}` ; listes paginées
`{"items": [...], "total": n, "limit": n, "offset": n}` (limit 20 par défaut, 100 au maximum) ;
`PATCH` ne modifie que les champs envoyés ; montants en FCFA (entiers), mesures en centimètres.

## Règles de gestion

Les 24 règles de l'énoncé (RG1 à RG24) sont appliquées par le serveur, dans `app/services/`, et couvertes
par les tests : le nom des tests de règles porte le numéro de la règle (`test_rg16_...`). Le workflow des statuts
(table des transitions, message d'erreur listant les statuts possibles) est dans `app/services/workflow.py`.
