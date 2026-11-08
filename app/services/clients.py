import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, Introuvable
from app.models.client import Client
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
