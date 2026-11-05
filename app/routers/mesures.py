from fastapi import APIRouter

from app.routers.commun import route_a_implementer
from app.schemas.mesures import MesureCreate, MesureRead, MesureUpdate

router = APIRouter(tags=["Mesures"])


@router.post("/clients/{id}/mesures", response_model=MesureRead, status_code=201)
def creer_mesure(id: int, mesure: MesureCreate):
    raise route_a_implementer()


@router.get("/clients/{id}/mesures", response_model=list[MesureRead])
def lister_mesures_client(id: int):
    raise route_a_implementer()


@router.get("/clients/{id}/mesures/derniere", response_model=MesureRead)
def lire_dernieres_mesures(id: int):
    raise route_a_implementer()


@router.get("/mesures/{id}", response_model=MesureRead)
def lire_mesure(id: int):
    raise route_a_implementer()


@router.patch("/mesures/{id}", response_model=MesureRead)
def modifier_mesure(id: int, mesure: MesureUpdate):
    raise route_a_implementer()


@router.delete("/mesures/{id}", status_code=204)
def supprimer_mesure(id: int):
    raise route_a_implementer()
