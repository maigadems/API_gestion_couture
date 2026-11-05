from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ModePaiement(str, Enum):
    especes = "especes"
    wave = "wave"
    orange_money = "orange_money"
    virement = "virement"
    cheque = "cheque"


class PaiementCreate(BaseModel):
    montant: int = Field(gt=0)
    mode: ModePaiement
    reference: str | None = None
    date_paiement: date | None = None


class PaiementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    commande_id: int
    montant: int
    mode: ModePaiement
    reference: str | None
    date_paiement: date
    enregistre_par_id: int | None
    created_at: datetime
