from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.livraisons import LivraisonRead
from app.schemas.paiements import PaiementRead


class StatutCommande(str, Enum):
    en_attente = "en_attente"
    en_coupe = "en_coupe"
    en_couture = "en_couture"
    essayage = "essayage"
    retouches = "retouches"
    terminee = "terminee"
    livree = "livree"
    annulee = "annulee"


class LigneCommandeCreate(BaseModel):
    type_vetement_id: int
    description: str | None = None
    quantite: int = Field(default=1, gt=0)
    prix_unitaire: int | None = Field(default=None, ge=0)


class LigneCommandeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    type_vetement_id: int
    type_vetement_nom: str
    description: str | None
    quantite: int
    prix_unitaire: int
    sous_total: int


class CommandeCreate(BaseModel):
    client_id: int
    mesure_id: int | None = None
    lignes: list[LigneCommandeCreate] = Field(min_length=1)
    remise: int = Field(default=0, ge=0)
    date_livraison_prevue: date | None = None
    notes: str | None = None


class CommandeUpdate(BaseModel):
    mesure_id: int | None = None
    date_livraison_prevue: date = None
    remise: int = Field(default=None, ge=0)
    notes: str | None = None


class ChangementStatut(BaseModel):
    statut: StatutCommande
    commentaire: str | None = None


class HistoriqueStatutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    ancien_statut: StatutCommande | None
    nouveau_statut: StatutCommande
    commentaire: str | None
    utilisateur_id: int | None
    date_changement: datetime


class CommandeListe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numero: str
    client_id: int
    client_nom: str
    statut: StatutCommande
    date_commande: date
    date_livraison_prevue: date
    montant_total: int
    montant_paye: int
    solde: int
    en_retard: bool


class CommandeDetail(CommandeListe):
    mesure_id: int | None
    date_livraison_reelle: date | None
    remise: int
    notes: str | None
    cree_par_id: int | None
    created_at: datetime
    updated_at: datetime
    lignes: list[LigneCommandeRead]
    paiements: list[PaiementRead]
    livraison: LivraisonRead | None
