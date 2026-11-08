from datetime import date, timedelta

from sqlalchemy import func, literal_column, select
from sqlalchemy.orm import Session, selectinload

from app.exceptions import DonneesInvalides
from app.models.client import Client
from app.models.commande import Commande
from app.models.ligne_commande import LigneCommande
from app.models.livraison import Livraison
from app.models.paiement import Paiement
from app.models.type_vetement import TypeVetement
from app.schemas.statistiques import Granularite
from app.services.commandes import condition_en_retard
from app.services.pagination import paginer
from app.services.workflow import TOUS_LES_STATUTS

NON_ANNULEE = Commande.statut != "annulee"


def _periode(date_debut: date | None, date_fin: date | None) -> tuple[date, date]:
    aujourdhui = date.today()
    debut = date_debut or aujourdhui.replace(day=1)
    fin = date_fin or aujourdhui
    if debut > fin:
        raise DonneesInvalides("date_debut doit être antérieure ou égale à date_fin")
    return debut, fin


def tableau_de_bord(db: Session) -> dict:
    aujourdhui = date.today()
    debut_mois = aujourdhui.replace(day=1)
    mois_suivant = (debut_mois + timedelta(days=32)).replace(day=1)

    chiffre_affaires, nb_commandes = db.execute(
        select(func.coalesce(func.sum(Commande.montant_total), 0), func.count(Commande.id)).where(
            NON_ANNULEE, Commande.date_commande >= debut_mois, Commande.date_commande < mois_suivant
        )
    ).one()
    encaisse = db.scalar(
        select(func.coalesce(func.sum(Paiement.montant), 0)).where(
            Paiement.date_paiement >= debut_mois, Paiement.date_paiement < mois_suivant
        )
    )
    reste_a_encaisser = db.scalar(
        select(func.coalesce(func.sum(Commande.montant_total - Commande.montant_paye), 0)).where(
            NON_ANNULEE
        )
    )
    par_statut = {statut: 0 for statut in TOUS_LES_STATUTS}
    for statut, nombre in db.execute(select(Commande.statut, func.count()).group_by(Commande.statut)):
        par_statut[statut] = nombre
    nb_en_retard = db.scalar(select(func.count()).select_from(Commande).where(condition_en_retard()))
    livraisons_du_jour = db.scalar(
        select(func.count())
        .select_from(Livraison)
        .where(Livraison.date_prevue == aujourdhui, Livraison.statut == "planifiee")
    )
    return {
        "chiffre_affaires_mois": chiffre_affaires,
        "encaisse_mois": encaisse,
        "nb_commandes_mois": nb_commandes,
        "reste_a_encaisser": reste_a_encaisser,
        "commandes_par_statut": par_statut,
        "nb_commandes_en_retard": nb_en_retard,
        "commandes_pretes_a_livrer": par_statut["terminee"],
        "livraisons_du_jour": livraisons_du_jour,
    }


def chiffre_affaires(
    db: Session, granularite: Granularite, date_debut: date | None, date_fin: date | None
) -> list[dict]:
    debut, fin = _periode(date_debut, date_fin)
    format_date = "YYYY-MM-DD" if granularite == Granularite.jour else "YYYY-MM"
    jour_commande = func.to_char(Commande.date_commande, literal_column(f"'{format_date}'"))
    jour_paiement = func.to_char(Paiement.date_paiement, literal_column(f"'{format_date}'"))
    ventes = dict(
        db.execute(
            select(jour_commande, func.sum(Commande.montant_total))
            .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
            .group_by(jour_commande)
        ).all()
    )
    encaissements = dict(
        db.execute(
            select(jour_paiement, func.sum(Paiement.montant))
            .where(Paiement.date_paiement.between(debut, fin))
            .group_by(jour_paiement)
        ).all()
    )
    # Seules les périodes avec de l'activité sont listées
    return [
        {
            "periode": periode,
            "chiffre_affaires": ventes.get(periode, 0),
            "encaisse": encaissements.get(periode, 0),
        }
        for periode in sorted(set(ventes) | set(encaissements))
    ]


def types_vetement(db: Session, date_debut: date | None, date_fin: date | None) -> list[dict]:
    debut, fin = _periode(date_debut, date_fin)
    chiffre = func.sum(LigneCommande.quantite * LigneCommande.prix_unitaire)  # avant remise
    lignes = db.execute(
        select(TypeVetement.id, TypeVetement.nom, func.sum(LigneCommande.quantite), chiffre)
        .select_from(LigneCommande)
        .join(Commande, LigneCommande.commande_id == Commande.id)
        .join(TypeVetement, LigneCommande.type_vetement_id == TypeVetement.id)
        .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
        .group_by(TypeVetement.id, TypeVetement.nom)
        .order_by(chiffre.desc(), TypeVetement.nom)
    ).all()
    return [
        {"type_vetement_id": id_, "nom": nom, "quantite": quantite, "chiffre_affaires": ca}
        for id_, nom, quantite, ca in lignes
    ]


def top_clients(
    db: Session, date_debut: date | None, date_fin: date | None, limite: int
) -> list[dict]:
    debut, fin = _periode(date_debut, date_fin)
    chiffre = func.sum(Commande.montant_total)
    lignes = db.execute(
        select(
            Client.id,
            Client.prenom,
            Client.nom,
            func.count(Commande.id),
            chiffre,
            func.sum(Commande.montant_total - Commande.montant_paye),
        )
        .join(Commande, Commande.client_id == Client.id)
        .where(NON_ANNULEE, Commande.date_commande.between(debut, fin))
        .group_by(Client.id, Client.prenom, Client.nom)
        .order_by(chiffre.desc(), Client.id)
        .limit(limite)
    ).all()
    return [
        {
            "client_id": id_,
            "client_nom": f"{prenom} {nom}",
            "nb_commandes": nb,
            "chiffre_affaires": ca,
            "solde_du": solde,
        }
        for id_, prenom, nom, nb, ca, solde in lignes
    ]


def impayes(db: Session, limit: int, offset: int) -> dict:
    requete = (
        select(Commande)
        .where(NON_ANNULEE, Commande.montant_total > Commande.montant_paye)
        .order_by(Commande.date_livraison_prevue, Commande.id)  # les plus urgentes d'abord
    )
    return paginer(db, requete, limit, offset, selectinload(Commande.client))
