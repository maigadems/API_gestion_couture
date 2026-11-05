from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict, model_validator


class ModeLivraison(str, Enum):
    retrait_atelier = "retrait_atelier"
    domicile = "domicile"


class StatutLivraison(str, Enum):
    planifiee = "planifiee"
    livree = "livree"


class LivraisonPlanification(BaseModel):
    mode: ModeLivraison
    date_prevue: date
    adresse: str | None = None
    livreur: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def verifier_adresse(self):
        if self.mode == ModeLivraison.domicile and not self.adresse:
            raise ValueError("Une livraison à domicile exige une adresse")
        return self


class LivraisonConfirmation(BaseModel):
    date_effective: date | None = None
    autoriser_solde_impaye: bool = False


class LivraisonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    mode: ModeLivraison
    adresse: str | None
    livreur: str | None
    date_prevue: date
    date_effective: date | None
    statut: StatutLivraison
    notes: str | None


class LivraisonTournee(LivraisonRead):
    numero_commande: str
    client_nom: str
    client_telephone: str
    solde_commande: int
