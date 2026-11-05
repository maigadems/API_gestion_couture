from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

Centimetres = Annotated[float, Field(gt=0, le=300)]


class MesureValeurs(BaseModel):
    taille_cm: Centimetres | None = None
    tour_cou: Centimetres | None = None
    carrure_dos: Centimetres | None = None
    longueur_epaule: Centimetres | None = None
    tour_poitrine: Centimetres | None = None
    tour_taille: Centimetres | None = None
    tour_bassin: Centimetres | None = None
    longueur_manche: Centimetres | None = None
    tour_bras: Centimetres | None = None
    tour_poignet: Centimetres | None = None
    longueur_dos: Centimetres | None = None
    longueur_haut: Centimetres | None = None
    longueur_pantalon: Centimetres | None = None
    tour_cuisse: Centimetres | None = None
    tour_genou: Centimetres | None = None
    bas_pantalon: Centimetres | None = None
    entrejambe: Centimetres | None = None
    longueur_robe: Centimetres | None = None


class MesureCreate(MesureValeurs):
    date_prise: date | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def verifier_au_moins_une_mesure(self):
        if all(getattr(self, champ) is None for champ in MesureValeurs.model_fields):
            raise ValueError("Une prise doit contenir au moins une mesure")
        return self


class MesureUpdate(MesureValeurs):
    date_prise: date = None
    notes: str | None = None


class MesureRead(MesureValeurs):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    date_prise: date
    prise_par_id: int | None
    notes: str | None
