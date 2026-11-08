"""Matrice des droits : pour chaque route, quels rôles ont le droit d'appeler (403 sinon)."""

import pytest

from tests.outils import API

TOUS = {"admin", "accueil", "tailleur"}
ADMIN = {"admin"}
ACCUEIL = {"admin", "accueil"}
TAILLEUR = {"admin", "tailleur"}

ROUTES = [
    # Authentification et comptes
    ("GET", "/auth/me", TOUS),
    ("POST", "/utilisateurs", ADMIN),
    ("GET", "/utilisateurs", ADMIN),
    ("GET", "/utilisateurs/1", ADMIN),
    ("PATCH", "/utilisateurs/1", ADMIN),
    # Clients
    ("POST", "/clients", TOUS),
    ("GET", "/clients", TOUS),
    ("GET", "/clients/1", TOUS),
    ("PATCH", "/clients/1", TOUS),
    ("DELETE", "/clients/1", ADMIN),
    ("GET", "/clients/1/commandes", TOUS),
    ("GET", "/clients/1/resume", TOUS),
    # Catalogue
    ("POST", "/catalogue", ADMIN),
    ("GET", "/catalogue", TOUS),
    ("GET", "/catalogue/1", TOUS),
    ("PATCH", "/catalogue/1", ADMIN),
    # Mesures
    ("POST", "/clients/1/mesures", TAILLEUR),
    ("GET", "/clients/1/mesures", TOUS),
    ("GET", "/clients/1/mesures/derniere", TOUS),
    ("GET", "/mesures/1", TOUS),
    ("PATCH", "/mesures/1", TAILLEUR),
    ("DELETE", "/mesures/1", TAILLEUR),
    # Commandes
    ("POST", "/commandes", ACCUEIL),
    ("GET", "/commandes", TOUS),
    ("GET", "/commandes/1", TOUS),
    ("PATCH", "/commandes/1", ACCUEIL),
    ("POST", "/commandes/1/statut", TOUS),
    ("GET", "/commandes/1/historique", TOUS),
    ("POST", "/commandes/1/lignes", ACCUEIL),
    ("DELETE", "/commandes/1/lignes/1", ACCUEIL),
    # Paiements
    ("POST", "/commandes/1/paiements", ACCUEIL),
    ("GET", "/commandes/1/paiements", TOUS),
    ("DELETE", "/paiements/1", ADMIN),
    # Livraisons
    ("PUT", "/commandes/1/livraison", ACCUEIL),
    ("GET", "/commandes/1/livraison", TOUS),
    ("POST", "/commandes/1/livraison/confirmer", ACCUEIL),
    ("GET", "/livraisons", TOUS),
    # Statistiques
    ("GET", "/statistiques/tableau-de-bord", ADMIN),
    ("GET", "/statistiques/chiffre-affaires", ADMIN),
    ("GET", "/statistiques/types-vetement", ADMIN),
    ("GET", "/statistiques/top-clients", ADMIN),
    ("GET", "/statistiques/impayes", ADMIN),
]


def appeler(client, methode, chemin, entetes=None):
    corps = {} if methode in ("POST", "PUT", "PATCH") else None
    return client.request(methode, API + chemin, json=corps, headers=entetes)


def test_la_matrice_couvre_les_43_routes_du_prefixe_api():
    # 44 routes au total, dont /health (hors préfixe) et /auth/login (publique)
    assert len(ROUTES) == 42


@pytest.mark.parametrize("methode, chemin, autorises", ROUTES, ids=[f"{m} {c}" for m, c, _ in ROUTES])
def test_droits_par_role(client, h_admin, h_accueil, h_tailleur, methode, chemin, autorises):
    entetes = {"admin": h_admin, "accueil": h_accueil, "tailleur": h_tailleur}
    for role, en_tetes in entetes.items():
        statut = appeler(client, methode, chemin, en_tetes).status_code
        if role in autorises:
            assert statut not in (401, 403), f"{role} devrait avoir accès à {methode} {chemin}"
        else:
            assert statut == 403, f"{role} ne devrait pas avoir accès à {methode} {chemin}"


@pytest.mark.parametrize("methode, chemin, autorises", ROUTES, ids=[f"{m} {c}" for m, c, _ in ROUTES])
def test_sans_jeton_401(client, methode, chemin, autorises):
    assert appeler(client, methode, chemin).status_code == 401


def test_routes_publiques(client):
    assert client.get("/health").status_code == 200
    assert client.post(f"{API}/auth/login", data={"username": "x@y.sn", "password": "motdepasse1"}).status_code == 401
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200
