from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, DonneesInvalides, Introuvable
from app.models.paiement import Paiement
from app.models.utilisateur import Utilisateur
from app.schemas.paiements import PaiementCreate
from app.services.commandes import lire_commande, recalculer_montants


def encaisser_paiement(
    db: Session, commande_id: int, donnees: PaiementCreate, utilisateur: Utilisateur
) -> Paiement:
    commande = lire_commande(db, commande_id, verrou=True)
    if commande.statut == "annulee":  # RG16
        raise Conflit("Impossible d'encaisser un paiement sur une commande annulée")
    date_paiement = donnees.date_paiement or date.today()
    if date_paiement > date.today():  # RG16
        raise DonneesInvalides("La date de paiement ne peut pas être dans le futur")
    if donnees.montant > commande.solde:  # RG16
        raise Conflit(
            f"Le paiement ({donnees.montant} FCFA) dépasse le solde restant "
            f"({commande.solde} FCFA)"
        )
    paiement = Paiement(
        montant=donnees.montant,
        mode=donnees.mode.value,
        reference=donnees.reference,
        date_paiement=date_paiement,
        enregistre_par_id=utilisateur.id,
    )
    commande.paiements.append(paiement)
    recalculer_montants(commande)
    db.flush()
    return paiement


def lister_paiements(db: Session, commande_id: int) -> list[Paiement]:
    commande = lire_commande(db, commande_id)
    return list(
        db.scalars(
            select(Paiement).where(Paiement.commande_id == commande.id).order_by(Paiement.id)
        )
    )


def annuler_paiement(db: Session, paiement_id: int) -> None:
    paiement = db.get(Paiement, paiement_id)
    if paiement is None:
        raise Introuvable("Paiement introuvable")
    commande = lire_commande(db, paiement.commande_id, verrou=True)
    commande.paiements.remove(paiement)  # supprimé de la base (delete-orphan)
    recalculer_montants(commande)  # RG17
    db.flush()
