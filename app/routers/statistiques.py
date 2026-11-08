from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exiger_roles
from app.schemas.commandes import CommandeListe
from app.schemas.commun import Page
from app.schemas.statistiques import (
    ChiffreAffairesPeriode,
    Granularite,
    StatistiqueTypeVetement,
    TableauDeBord,
    TopClient,
)
from app.services import statistiques as service

router = APIRouter(
    prefix="/statistiques",
    tags=["Statistiques"],
    dependencies=[Depends(exiger_roles("admin"))],
)


@router.get("/tableau-de-bord", response_model=TableauDeBord)
def lire_tableau_de_bord(db: Session = Depends(get_db)):
    return service.tableau_de_bord(db)


@router.get("/chiffre-affaires", response_model=list[ChiffreAffairesPeriode])
def lire_chiffre_affaires(
    granularite: Granularite = Granularite.jour,
    date_debut: date | None = None,
    date_fin: date | None = None,
    db: Session = Depends(get_db),
):
    return service.chiffre_affaires(db, granularite, date_debut, date_fin)


@router.get("/types-vetement", response_model=list[StatistiqueTypeVetement])
def lire_statistiques_types_vetement(
    date_debut: date | None = None,
    date_fin: date | None = None,
    db: Session = Depends(get_db),
):
    return service.types_vetement(db, date_debut, date_fin)


@router.get("/top-clients", response_model=list[TopClient])
def lire_top_clients(
    date_debut: date | None = None,
    date_fin: date | None = None,
    limite: int = Query(default=10, ge=1),
    db: Session = Depends(get_db),
):
    return service.top_clients(db, date_debut, date_fin, limite)


@router.get("/impayes", response_model=Page[CommandeListe])
def lire_impayes(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return service.impayes(db, limit, offset)
