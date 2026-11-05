from datetime import date

from fastapi import APIRouter, Query

from app.routers.commun import route_a_implementer
from app.schemas.commandes import (
    ChangementStatut,
    CommandeCreate,
    CommandeDetail,
    CommandeListe,
    CommandeUpdate,
    HistoriqueStatutRead,
    LigneCommandeCreate,
    StatutCommande,
)
from app.schemas.commun import Page

router = APIRouter(tags=["Commandes"])


@router.post("/commandes", response_model=CommandeDetail, status_code=201)
def creer_commande(commande: CommandeCreate):
    raise route_a_implementer()


@router.get("/commandes", response_model=Page[CommandeListe])
def lister_commandes(
    statut: StatutCommande | None = None,
    client_id: int | None = None,
    en_retard: bool | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
    numero: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    raise route_a_implementer()


@router.get("/commandes/{id}", response_model=CommandeDetail)
def lire_commande(id: int):
    raise route_a_implementer()


@router.patch("/commandes/{id}", response_model=CommandeDetail)
def modifier_commande(id: int, commande: CommandeUpdate):
    raise route_a_implementer()


@router.post("/commandes/{id}/statut", response_model=CommandeDetail)
def changer_statut(id: int, changement: ChangementStatut):
    raise route_a_implementer()


@router.get("/commandes/{id}/historique", response_model=list[HistoriqueStatutRead])
def lire_historique(id: int):
    raise route_a_implementer()


@router.post("/commandes/{id}/lignes", response_model=CommandeDetail, status_code=201)
def ajouter_ligne(id: int, ligne: LigneCommandeCreate):
    raise route_a_implementer()


@router.delete("/commandes/{id}/lignes/{ligne_id}", response_model=CommandeDetail)
def retirer_ligne(id: int, ligne_id: int):
    raise route_a_implementer()


@router.get("/clients/{id}/commandes", response_model=Page[CommandeListe])
def lister_commandes_client(
    id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    raise route_a_implementer()
