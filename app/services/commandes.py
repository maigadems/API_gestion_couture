from datetime import date, timedelta

from sqlalchemy import and_, not_, select, text
from sqlalchemy.orm import Session, selectinload

from app.exceptions import Conflit, DonneesInvalides, Interdit, Introuvable
from app.models.commande import Commande
from app.models.historique_statut import HistoriqueStatut
from app.models.ligne_commande import LigneCommande
from app.models.mesure import Mesure
from app.models.type_vetement import TypeVetement
from app.models.utilisateur import Utilisateur
from app.schemas.commandes import (
    ChangementStatut,
    CommandeCreate,
    CommandeUpdate,
    LigneCommandeCreate,
    StatutCommande,
)
from app.services.clients import lire_client
from app.services.mesures import derniere_mesure_du_client
from app.services.pagination import paginer
from app.services.workflow import STATUTS_FINAUX, verifier_transition


def lire_commande(db: Session, commande_id: int, verrou: bool = False) -> Commande:
    """`verrou=True` bloque la ligne jusqu'à la fin de la transaction (modifications concurrentes)."""
    commande = db.get(Commande, commande_id, with_for_update=verrou)
    if commande is None:
        raise Introuvable("Commande introuvable")
    return commande


def condition_en_retard():
    """RG11 en SQL : date prévue dépassée et commande ni livrée ni annulée."""
    return and_(
        Commande.date_livraison_prevue < date.today(),
        Commande.statut.notin_(STATUTS_FINAUX),
    )


def recalculer_montants(commande: Commande) -> None:
    """RG7 : les montants sont toujours calculés par le serveur."""
    somme = sum(ligne.quantite * ligne.prix_unitaire for ligne in commande.lignes)
    commande.montant_total = somme - commande.remise
    commande.montant_paye = sum(paiement.montant for paiement in commande.paiements)


def _verifier_montants(commande: Commande) -> None:
    somme = sum(ligne.quantite * ligne.prix_unitaire for ligne in commande.lignes)
    if commande.remise > somme:
        raise DonneesInvalides(
            f"La remise ({commande.remise} FCFA) dépasse la somme des prestations ({somme} FCFA)"
        )
    paye = sum(paiement.montant for paiement in commande.paiements)
    if somme - commande.remise < paye:
        raise Conflit(
            f"Le nouveau total ({somme - commande.remise} FCFA) serait inférieur "
            f"au montant déjà payé ({paye} FCFA)"
        )


def _verifier_modifiable(commande: Commande) -> None:
    """RG12 : une commande livrée ou annulée n'est plus modifiable."""
    if commande.statut in STATUTS_FINAUX:
        etat = "livrée" if commande.statut == "livree" else "annulée"
        raise Conflit(f"Une commande {etat} n'est plus modifiable")


def _verifier_lignes_modifiables(commande: Commande) -> None:
    """RG10 : les lignes ne changent que tant que la commande est « en_attente »."""
    _verifier_modifiable(commande)
    if commande.statut != "en_attente":
        raise Conflit(
            "Les lignes ne sont modifiables que tant que la commande est « en_attente » "
            f"(statut actuel : {commande.statut})"
        )


def _prochain_numero(db: Session) -> tuple[int, str]:
    """RG5 : CMD-AAAA-NNNNN. On réserve l'identifiant avant l'insertion pour en bâtir le numéro."""
    identifiant = db.scalar(text("SELECT nextval(pg_get_serial_sequence('commandes', 'id'))"))
    return identifiant, f"CMD-{date.today().year}-{identifiant:05d}"


def _creer_ligne(db: Session, donnees: LigneCommandeCreate) -> LigneCommande:
    prestation = db.get(TypeVetement, donnees.type_vetement_id)
    if prestation is None:
        raise Introuvable("Prestation introuvable")
    if not prestation.actif:
        raise DonneesInvalides(f"La prestation « {prestation.nom} » n'est plus disponible")
    # RG6 : prix du catalogue par défaut, négociable ligne par ligne
    prix = donnees.prix_unitaire if donnees.prix_unitaire is not None else prestation.prix_base
    return LigneCommande(
        type_vetement=prestation,
        description=donnees.description,
        quantite=donnees.quantite,
        prix_unitaire=prix,
    )


def _mesure_du_client(db: Session, client_id: int, mesure_id: int) -> int:
    mesure = db.get(Mesure, mesure_id)
    if mesure is None:
        raise Introuvable("Prise de mesures introuvable")
    if mesure.client_id != client_id:  # RG9
        raise DonneesInvalides("Les mesures doivent appartenir au client de la commande")
    return mesure.id


def creer_commande(db: Session, donnees: CommandeCreate, utilisateur: Utilisateur) -> Commande:
    client = lire_client(db, donnees.client_id)
    lignes = [_creer_ligne(db, ligne) for ligne in donnees.lignes]

    somme = sum(ligne.quantite * ligne.prix_unitaire for ligne in lignes)
    if donnees.remise > somme:
        raise DonneesInvalides(
            f"La remise ({donnees.remise} FCFA) dépasse la somme des prestations ({somme} FCFA)"
        )

    aujourdhui = date.today()
    if donnees.date_livraison_prevue is None:  # RG8 : le plus long délai des prestations
        delai = max(ligne.type_vetement.delai_jours for ligne in lignes)
        date_prevue = aujourdhui + timedelta(days=delai)
    else:
        date_prevue = donnees.date_livraison_prevue
    if date_prevue < aujourdhui:
        raise DonneesInvalides("La date de livraison prévue ne peut pas précéder la date de commande")

    if donnees.mesure_id is not None:
        mesure_id = _mesure_du_client(db, client.id, donnees.mesure_id)
    else:  # RG9 : sans précision, les dernières mesures du client
        derniere = derniere_mesure_du_client(db, client.id)
        mesure_id = derniere.id if derniere else None

    identifiant, numero = _prochain_numero(db)
    commande = Commande(
        id=identifiant,
        numero=numero,
        client=client,
        mesure_id=mesure_id,
        statut="en_attente",
        date_commande=aujourdhui,
        date_livraison_prevue=date_prevue,
        remise=donnees.remise,
        notes=donnees.notes,
        cree_par_id=utilisateur.id,
    )
    commande.lignes = lignes
    # RG15 : la création inscrit la première ligne de l'historique (ancien statut vide)
    commande.historique.append(
        HistoriqueStatut(
            ancien_statut=None,
            nouveau_statut="en_attente",
            commentaire="Création de la commande",
            utilisateur_id=utilisateur.id,
        )
    )
    recalculer_montants(commande)
    db.add(commande)
    db.flush()
    return commande


def lister_commandes(
    db: Session,
    statut: StatutCommande | None,
    client_id: int | None,
    en_retard: bool | None,
    date_min: date | None,
    date_max: date | None,
    numero: str | None,
    limit: int,
    offset: int,
) -> dict:
    requete = select(Commande).order_by(Commande.date_commande.desc(), Commande.id.desc())
    if statut is not None:
        requete = requete.where(Commande.statut == statut.value)
    if client_id is not None:
        requete = requete.where(Commande.client_id == client_id)
    if en_retard is True:
        requete = requete.where(condition_en_retard())
    elif en_retard is False:
        requete = requete.where(not_(condition_en_retard()))
    if date_min is not None:
        requete = requete.where(Commande.date_commande >= date_min)
    if date_max is not None:
        requete = requete.where(Commande.date_commande <= date_max)
    if numero:
        requete = requete.where(Commande.numero.icontains(numero.strip(), autoescape=True))
    return paginer(db, requete, limit, offset, selectinload(Commande.client))


def lister_commandes_client(db: Session, client_id: int, limit: int, offset: int) -> dict:
    client = lire_client(db, client_id)
    return lister_commandes(db, None, client.id, None, None, None, None, limit, offset)


def modifier_commande(db: Session, commande_id: int, donnees: CommandeUpdate) -> Commande:
    commande = lire_commande(db, commande_id, verrou=True)
    _verifier_modifiable(commande)
    champs = donnees.model_dump(exclude_unset=True)
    if "mesure_id" in champs:
        valeur = champs["mesure_id"]
        commande.mesure_id = None if valeur is None else _mesure_du_client(db, commande.client_id, valeur)
    if "date_livraison_prevue" in champs:
        if champs["date_livraison_prevue"] < commande.date_commande:
            raise DonneesInvalides(
                "La date de livraison prévue ne peut pas précéder la date de commande"
            )
        commande.date_livraison_prevue = champs["date_livraison_prevue"]
    if "remise" in champs:
        commande.remise = champs["remise"]
    if "notes" in champs:
        commande.notes = champs["notes"]
    _verifier_montants(commande)
    recalculer_montants(commande)
    db.flush()
    return commande


def ajouter_ligne(db: Session, commande_id: int, donnees: LigneCommandeCreate) -> Commande:
    commande = lire_commande(db, commande_id, verrou=True)
    _verifier_lignes_modifiables(commande)
    commande.lignes.append(_creer_ligne(db, donnees))
    recalculer_montants(commande)
    db.flush()
    return commande


def retirer_ligne(db: Session, commande_id: int, ligne_id: int) -> Commande:
    commande = lire_commande(db, commande_id, verrou=True)
    _verifier_lignes_modifiables(commande)
    ligne = next((ligne for ligne in commande.lignes if ligne.id == ligne_id), None)
    if ligne is None:
        raise Introuvable("Ligne introuvable dans cette commande")
    if len(commande.lignes) == 1:
        raise Conflit("Une commande garde toujours au moins une ligne")
    commande.lignes.remove(ligne)
    _verifier_montants(commande)
    recalculer_montants(commande)
    db.flush()
    return commande


def changer_statut(
    db: Session, commande_id: int, donnees: ChangementStatut, utilisateur: Utilisateur
) -> Commande:
    commande = lire_commande(db, commande_id, verrou=True)
    cible = donnees.statut.value
    if cible == "annulee" and utilisateur.role == "tailleur":  # RG14
        raise Interdit("Un tailleur ne peut pas annuler une commande")
    verifier_transition(commande.statut, cible)  # RG13 + workflow
    commentaire = (donnees.commentaire or "").strip() or None
    if cible == "annulee" and commande.montant_paye > 0 and commentaire is None:  # RG14
        raise DonneesInvalides(
            "Cette commande a reçu un acompte : un commentaire est obligatoire pour préciser "
            "le sort de l'argent (remboursement, avoir...)"
        )
    commande.historique.append(  # RG15
        HistoriqueStatut(
            ancien_statut=commande.statut,
            nouveau_statut=cible,
            commentaire=commentaire,
            utilisateur_id=utilisateur.id,
        )
    )
    commande.statut = cible
    db.flush()
    return commande


def lire_historique(db: Session, commande_id: int) -> list[HistoriqueStatut]:
    commande = lire_commande(db, commande_id)
    return list(
        db.scalars(
            select(HistoriqueStatut)
            .where(HistoriqueStatut.commande_id == commande.id)
            .order_by(HistoriqueStatut.date_changement, HistoriqueStatut.id)
        )
    )
