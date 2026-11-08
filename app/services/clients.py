import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, Introuvable
from app.models.client import Client
from app.models.commande import Commande
from app.models.mesure import Mesure
from app.schemas.clients import ClientCreate, ClientUpdate, Genre
from app.services.pagination import paginer


def verifier_telephone_libre(db: Session, telephone: str, sauf_id: int | None = None) -> None:
    """RG1 : le téléphone est unique. `sauf_id` permet à un client de garder son propre numéro."""
    requete = select(Client.id).where(Client.telephone == telephone)
    if sauf_id is not None:
        requete = requete.where(Client.id != sauf_id)
    if db.scalar(requete) is not None:
        raise Conflit("Un client avec ce numéro de téléphone existe déjà")


def creer_client(db: Session, donnees: ClientCreate) -> Client:
    verifier_telephone_libre(db, donnees.telephone)
    client = Client(**donnees.model_dump(mode="json"))
    db.add(client)
    db.flush()
    return client


def lire_client(db: Session, client_id: int) -> Client:
    client = db.get(Client, client_id)
    if client is None:
        raise Introuvable("Client introuvable")
    return client


def lister_clients(
    db: Session, q: str | None, genre: Genre | None, limit: int, offset: int
) -> dict:
    requete = select(Client).order_by(Client.nom, Client.prenom, Client.id)
    if q:
        q = q.strip()
        criteres = [
            Client.nom.icontains(q, autoescape=True),
            Client.prenom.icontains(q, autoescape=True),
            Client.telephone.icontains(q, autoescape=True),
        ]
        # « 77 123 » doit aussi retrouver le numéro enregistré sans espaces
        chiffres = re.sub(r"[ .\-()]", "", q)
        if chiffres and chiffres != q:
            criteres.append(Client.telephone.icontains(chiffres, autoescape=True))
        requete = requete.where(or_(*criteres))
    if genre is not None:
        requete = requete.where(Client.genre == genre.value)
    return paginer(db, requete, limit, offset)


def modifier_client(db: Session, client_id: int, donnees: ClientUpdate) -> Client:
    client = lire_client(db, client_id)
    # Seuls les champs réellement envoyés sont modifiés (PATCH partiel)
    champs = donnees.model_dump(exclude_unset=True, mode="json")
    if "telephone" in champs:
        verifier_telephone_libre(db, champs["telephone"], sauf_id=client.id)
    for nom, valeur in champs.items():
        setattr(client, nom, valeur)
    db.flush()
    return client


def supprimer_client(db: Session, client_id: int) -> None:
    client = lire_client(db, client_id)
    nb_commandes = db.scalar(
        select(func.count()).select_from(Commande).where(Commande.client_id == client.id)
    )
    if nb_commandes:
        raise Conflit(f"Ce client a {nb_commandes} commande(s) : suppression impossible")
    db.delete(client)  # ses mesures sont supprimées par la base (ON DELETE CASCADE)
    db.flush()


def resume_client(db: Session, client_id: int) -> dict:
    client = lire_client(db, client_id)
    nb, chiffre_affaires, total_paye, derniere = db.execute(
        select(
            func.count(Commande.id),
            func.coalesce(func.sum(Commande.montant_total), 0),
            func.coalesce(func.sum(Commande.montant_paye), 0),
            func.max(Commande.date_commande),
        ).where(Commande.client_id == client.id, Commande.statut != "annulee")
    ).one()
    nb_mesures = db.scalar(
        select(func.count()).select_from(Mesure).where(Mesure.client_id == client.id)
    )
    return {
        "nb_commandes": nb,
        "chiffre_affaires": chiffre_affaires,
        "total_paye": total_paye,
        "solde_du": chiffre_affaires - total_paye,
        "derniere_commande": derniere,
        "a_des_mesures": nb_mesures > 0,
    }
