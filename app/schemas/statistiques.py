from enum import Enum

from pydantic import BaseModel


class Granularite(str, Enum):
    jour = "jour"
    mois = "mois"


class TableauDeBord(BaseModel):
    chiffre_affaires_mois: int
    encaisse_mois: int
    nb_commandes_mois: int
    reste_a_encaisser: int
    commandes_par_statut: dict[str, int]
    nb_commandes_en_retard: int
    commandes_pretes_a_livrer: int
    livraisons_du_jour: int


class ChiffreAffairesPeriode(BaseModel):
    periode: str
    chiffre_affaires: int
    encaisse: int


class StatistiqueTypeVetement(BaseModel):
    type_vetement_id: int
    nom: str
    quantite: int
    chiffre_affaires: int


class TopClient(BaseModel):
    client_id: int
    client_nom: str
    nb_commandes: int
    chiffre_affaires: int
    solde_du: int
