import re
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.schemas.commun import TexteNonVide


class Genre(str, Enum):
    homme = "homme"
    femme = "femme"
    enfant = "enfant"


def normaliser_telephone(valeur: str) -> str:
    numero = re.sub(r"[ .\-()]", "", valeur)
    if not re.fullmatch(r"\+?[0-9]{6,20}", numero):
        raise ValueError("6 à 20 chiffres, avec un + initial facultatif")
    return numero


class ClientCreate(BaseModel):
    nom: TexteNonVide
    prenom: TexteNonVide
    telephone: str
    email: EmailStr | None = None
    adresse: str | None = None
    genre: Genre | None = None
    notes: str | None = None

    @field_validator("telephone")
    @classmethod
    def valider_telephone(cls, valeur: str) -> str:
        return normaliser_telephone(valeur)


class ClientUpdate(BaseModel):
    # Sans "| None" : un null explicite est refusé (422), ces champs ne peuvent pas être vidés
    nom: TexteNonVide = None
    prenom: TexteNonVide = None
    telephone: str = None
    email: EmailStr | None = None
    adresse: str | None = None
    genre: Genre | None = None
    notes: str | None = None

    @field_validator("telephone")
    @classmethod
    def valider_telephone(cls, valeur: str) -> str:
        return normaliser_telephone(valeur)


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    prenom: str
    telephone: str
    email: str | None
    adresse: str | None
    genre: Genre | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ClientResume(BaseModel):
    nb_commandes: int
    chiffre_affaires: int
    total_paye: int
    solde_du: int
    derniere_commande: date | None
    a_des_mesures: bool
