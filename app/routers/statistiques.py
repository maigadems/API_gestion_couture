from datetime import date

from fastapi import APIRouter, Query

from app.routers.commun import route_a_implementer
from app.schemas.commandes import CommandeListe
from app.schemas.commun import Page
from app.schemas.statistiques import (
    ChiffreAffairesPeriode,
    Granularite,
    StatistiqueTypeVetement,
    TableauDeBord,
    TopClient,
)

router = APIRouter(prefix="/statistiques", tags=["Statistiques"])


@router.get("/tableau-de-bord", response_model=TableauDeBord)
def lire_tableau_de_bord():
    raise route_a_implementer()


@router.get("/chiffre-affaires", response_model=list[ChiffreAffairesPeriode])
def lire_chiffre_affaires(
    granularite: Granularite = Granularite.jour,
    date_debut: date | None = None,
    date_fin: date | None = None,
):
    raise route_a_implementer()


@router.get("/types-vetement", response_model=list[StatistiqueTypeVetement])
def lire_statistiques_types_vetement(date_debut: date | None = None, date_fin: date | None = None):
    raise route_a_implementer()


@router.get("/top-clients", response_model=list[TopClient])
def lire_top_clients(
    date_debut: date | None = None,
    date_fin: date | None = None,
    limite: int = Query(default=10, ge=1),
):
    raise route_a_implementer()


@router.get("/impayes", response_model=Page[CommandeListe])
def lire_impayes(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    raise route_a_implementer()
