from pydantic import BaseModel, ConfigDict, Field

from app.schemas.commun import TexteNonVide


class TypeVetementCreate(BaseModel):
    nom: TexteNonVide
    description: str | None = None
    prix_base: int = Field(ge=0)
    delai_jours: int = Field(ge=0)


class TypeVetementUpdate(BaseModel):
    nom: TexteNonVide = None
    description: str | None = None
    prix_base: int = Field(default=None, ge=0)
    delai_jours: int = Field(default=None, ge=0)
    actif: bool = None


class TypeVetementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nom: str
    description: str | None
    prix_base: int
    delai_jours: int
    actif: bool
