from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, DonneesInvalides, Introuvable
from app.models.commande import Commande
from app.models.mesure import Mesure
from app.models.utilisateur import Utilisateur
from app.schemas.mesures import MesureCreate, MesureUpdate, MesureValeurs
from app.services.clients import lire_client

NOMS_MESURES = list(MesureValeurs.model_fields)


def creer_mesure(
    db: Session, client_id: int, donnees: MesureCreate, utilisateur: Utilisateur
) -> Mesure:
    client = lire_client(db, client_id)
    valeurs = donnees.model_dump()
    valeurs["date_prise"] = valeurs["date_prise"] or date.today()
    mesure = Mesure(client_id=client.id, prise_par_id=utilisateur.id, **valeurs)
    db.add(mesure)
    db.flush()
    return mesure


def lister_mesures_client(db: Session, client_id: int) -> list[Mesure]:
    """RG3 : tout l'historique est conservé, la prise la plus récente en premier."""
    client = lire_client(db, client_id)
    return list(
        db.scalars(
            select(Mesure)
            .where(Mesure.client_id == client.id)
            .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
        )
    )


def derniere_mesure_du_client(db: Session, client_id: int) -> Mesure | None:
    return db.scalar(
        select(Mesure)
        .where(Mesure.client_id == client_id)
        .order_by(Mesure.date_prise.desc(), Mesure.id.desc())
        .limit(1)
    )


def lire_dernieres_mesures(db: Session, client_id: int) -> Mesure:
    client = lire_client(db, client_id)
    mesure = derniere_mesure_du_client(db, client.id)
    if mesure is None:
        raise Introuvable("Ce client n'a aucune prise de mesures")
    return mesure


def lire_mesure(db: Session, mesure_id: int) -> Mesure:
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise Introuvable("Prise de mesures introuvable")
    return mesure


def modifier_mesure(db: Session, mesure_id: int, donnees: MesureUpdate) -> Mesure:
    mesure = lire_mesure(db, mesure_id)
    champs = donnees.model_dump(exclude_unset=True)
    # RG2 : après correction, il doit rester au moins une mesure
    apres = {nom: champs.get(nom, getattr(mesure, nom)) for nom in NOMS_MESURES}
    if all(valeur is None for valeur in apres.values()):
        raise DonneesInvalides("La correction supprimerait toutes les mesures de cette prise")
    for nom, valeur in champs.items():
        setattr(mesure, nom, valeur)
    db.flush()
    return mesure


def supprimer_mesure(db: Session, mesure_id: int) -> None:
    mesure = lire_mesure(db, mesure_id)
    nb_commandes = db.scalar(
        select(func.count()).select_from(Commande).where(Commande.mesure_id == mesure.id)
    )
    if nb_commandes:
        raise Conflit("Ces mesures sont utilisées par une commande : suppression impossible")
    db.delete(mesure)
    db.flush()
