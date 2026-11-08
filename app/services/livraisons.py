from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.exceptions import Conflit, DonneesInvalides, Introuvable
from app.models.commande import Commande
from app.models.historique_statut import HistoriqueStatut
from app.models.livraison import Livraison
from app.models.utilisateur import Utilisateur
from app.schemas.livraisons import (
    LivraisonConfirmation,
    LivraisonPlanification,
    StatutLivraison,
)
from app.services.commandes import lire_commande
from app.services.workflow import STATUTS_FINAUX


def planifier_livraison(
    db: Session, commande_id: int, donnees: LivraisonPlanification
) -> Livraison:
    commande = lire_commande(db, commande_id, verrou=True)
    if commande.statut in STATUTS_FINAUX:
        etat = "livrée" if commande.statut == "livree" else "annulée"
        raise Conflit(f"Une commande {etat} ne peut plus être planifiée")
    if donnees.date_prevue < commande.date_commande:
        raise DonneesInvalides("La date de livraison prévue ne peut pas précéder la date de commande")
    livraison = commande.livraison
    if livraison is None:  # RG18 : une seule livraison par commande, replanifier la modifie
        livraison = Livraison(statut=StatutLivraison.planifiee.value)
        commande.livraison = livraison
    livraison.mode = donnees.mode.value
    livraison.date_prevue = donnees.date_prevue
    livraison.adresse = donnees.adresse
    livraison.livreur = donnees.livreur
    livraison.notes = donnees.notes
    commande.date_livraison_prevue = donnees.date_prevue  # RG18
    db.flush()
    return livraison


def lire_livraison(db: Session, commande_id: int) -> Livraison:
    commande = lire_commande(db, commande_id)
    if commande.livraison is None:
        raise Introuvable("Aucune livraison n'est planifiée pour cette commande")
    return commande.livraison


def confirmer_livraison(
    db: Session,
    commande_id: int,
    confirmation: LivraisonConfirmation | None,
    utilisateur: Utilisateur,
) -> Livraison:
    confirmation = confirmation or LivraisonConfirmation()
    commande = lire_commande(db, commande_id, verrou=True)
    if commande.statut != "terminee":  # RG19
        raise Conflit(
            "Seule une commande « terminee » peut être livrée "
            f"(statut actuel : {commande.statut})"
        )
    solde = commande.solde
    if solde > 0 and not confirmation.autoriser_solde_impaye:  # RG19
        raise Conflit(
            f"Livraison impossible : il reste {solde} FCFA à payer. "
            "Soldez la commande ou envoyez autoriser_solde_impaye à vrai"
        )
    date_effective = confirmation.date_effective or date.today()
    if date_effective > date.today():
        raise DonneesInvalides("La date effective de livraison ne peut pas être dans le futur")

    livraison = commande.livraison
    if livraison is None:  # RG20 : retrait à l'atelier créé automatiquement
        livraison = Livraison(
            mode="retrait_atelier", date_prevue=commande.date_livraison_prevue
        )
        commande.livraison = livraison
    livraison.statut = StatutLivraison.livree.value
    livraison.date_effective = date_effective

    commande.statut = "livree"  # RG20
    commande.date_livraison_reelle = date_effective
    if solde > 0:
        commentaire = f"Livraison confirmée avec un solde impayé de {solde} FCFA"
    else:
        commentaire = "Livraison confirmée"
    commande.historique.append(
        HistoriqueStatut(
            ancien_statut="terminee",
            nouveau_statut="livree",
            commentaire=commentaire,
            utilisateur_id=utilisateur.id,
        )
    )
    db.flush()
    return livraison


def lister_livraisons(
    db: Session,
    statut: StatutLivraison | None,
    date_min: date | None,
    date_max: date | None,
) -> list[Livraison]:
    requete = (
        select(Livraison)
        .options(joinedload(Livraison.commande).joinedload(Commande.client))
        .order_by(Livraison.date_prevue, Livraison.id)
    )
    if statut is not None:
        requete = requete.where(Livraison.statut == statut.value)
    if date_min is not None:
        requete = requete.where(Livraison.date_prevue >= date_min)
    if date_max is not None:
        requete = requete.where(Livraison.date_prevue <= date_max)
    return list(db.scalars(requete))
