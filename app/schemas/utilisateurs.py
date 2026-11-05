from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.commun import TexteNonVide


class Role(str, Enum):
    admin = "admin"
    tailleur = "tailleur"
    accueil = "accueil"


class UtilisateurCreate(BaseModel):
    email: EmailStr
    nom_complet: TexteNonVide
    mot_de_passe: str = Field(min_length=8)
    role: Role


class UtilisateurUpdate(BaseModel):
    nom_complet: TexteNonVide = None
    role: Role = None
    actif: bool = None
    mot_de_passe: str = Field(default=None, min_length=8)


class UtilisateurRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nom_complet: str
    role: Role
    actif: bool
    created_at: datetime
