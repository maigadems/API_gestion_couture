"""Fonctions d'aide partagées par les tests."""

from argon2 import PasswordHasher
from sqlalchemy import update

from app.database import SessionLocal
from app.models.utilisateur import Utilisateur

API = "/api/v1"
MOT_DE_PASSE = "motdepasse123"
# Même algorithme (Argon2id) mais réglé au plus léger : les paramètres sont lus dans le hash
# lui-même, donc la vérification reste rapide. Les tests se connectent des centaines de fois.
HASH_DE_TEST = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(MOT_DE_PASSE)

# Chemin des statuts pour amener une commande à un statut donné
CHEMINS = {
    "en_attente": [],
    "en_coupe": ["en_coupe"],
    "en_couture": ["en_coupe", "en_couture"],
    "essayage": ["en_coupe", "en_couture", "essayage"],
    "retouches": ["en_coupe", "en_couture", "essayage", "retouches"],
    "terminee": ["en_coupe", "en_couture", "terminee"],
}


def creer_utilisateur_en_base(role: str, email: str, actif: bool = True) -> int:
    with SessionLocal() as db:
        utilisateur = Utilisateur(
            email=email,
            nom_complet=f"Test {role}",
            mot_de_passe_hash=HASH_DE_TEST,
            role=role,
            actif=actif,
        )
        db.add(utilisateur)
        db.commit()
        return utilisateur.id


def entetes_de(client, email: str, mot_de_passe: str = MOT_DE_PASSE) -> dict:
    reponse = client.post(
        f"{API}/auth/login", data={"username": email, "password": mot_de_passe}
    )
    assert reponse.status_code == 200, reponse.text
    return {"Authorization": f"Bearer {reponse.json()['access_token']}"}


def nouveau_client(client, entetes, **champs) -> dict:
    donnees = {"nom": "Diop", "prenom": "Fatou", "telephone": "771234567", **champs}
    reponse = client.post(f"{API}/clients", json=donnees, headers=entetes)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def nouvelle_prestation(client, entetes, nom, prix_base, delai_jours, **champs) -> dict:
    donnees = {"nom": nom, "prix_base": prix_base, "delai_jours": delai_jours, **champs}
    reponse = client.post(f"{API}/catalogue", json=donnees, headers=entetes)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def nouvelle_mesure(client, entetes, client_id: int, **valeurs) -> dict:
    donnees = valeurs or {"tour_poitrine": 100}
    reponse = client.post(f"{API}/clients/{client_id}/mesures", json=donnees, headers=entetes)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def ligne(prestation: dict, quantite: int = 1, prix_unitaire: int | None = None) -> dict:
    donnees = {"type_vetement_id": prestation["id"], "quantite": quantite}
    if prix_unitaire is not None:
        donnees["prix_unitaire"] = prix_unitaire
    return donnees


def nouvelle_commande(client, entetes, client_id: int, lignes: list[dict], **champs) -> dict:
    donnees = {"client_id": client_id, "lignes": lignes, **champs}
    reponse = client.post(f"{API}/commandes", json=donnees, headers=entetes)
    assert reponse.status_code == 201, reponse.text
    return reponse.json()


def poser_statut(client, entetes, commande_id: int, statut: str, commentaire: str | None = None):
    corps = {"statut": statut}
    if commentaire is not None:
        corps["commentaire"] = commentaire
    return client.post(f"{API}/commandes/{commande_id}/statut", json=corps, headers=entetes)


def amener_au_statut(client, entetes, commande_id: int, statut: str) -> None:
    """Fait avancer une commande, par l'API, jusqu'au statut demandé."""
    for etape in CHEMINS[statut]:
        reponse = poser_statut(client, entetes, commande_id, etape)
        assert reponse.status_code == 200, reponse.text


def payer(client, entetes, commande_id: int, montant: int, mode: str = "wave", **champs):
    return client.post(
        f"{API}/commandes/{commande_id}/paiements",
        json={"montant": montant, "mode": mode, **champs},
        headers=entetes,
    )


def modifier_en_base(commande_id: int, **champs) -> None:
    """Modifie directement une commande en base (pour fabriquer un retard, par exemple)."""
    from app.models.commande import Commande

    with SessionLocal() as db:
        db.execute(update(Commande).where(Commande.id == commande_id).values(**champs))
        db.commit()
