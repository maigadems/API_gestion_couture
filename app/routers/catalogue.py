from fastapi import APIRouter

from app.routers.commun import route_a_implementer
from app.schemas.catalogue import TypeVetementCreate, TypeVetementRead, TypeVetementUpdate

router = APIRouter(prefix="/catalogue", tags=["Catalogue"])


@router.post("", response_model=TypeVetementRead, status_code=201)
def creer_prestation(prestation: TypeVetementCreate):
    raise route_a_implementer()


@router.get("", response_model=list[TypeVetementRead])
def lister_prestations(actifs_seulement: bool = True):
    raise route_a_implementer()


@router.get("/{id}", response_model=TypeVetementRead)
def lire_prestation(id: int):
    raise route_a_implementer()


@router.patch("/{id}", response_model=TypeVetementRead)
def modifier_prestation(id: int, prestation: TypeVetementUpdate):
    raise route_a_implementer()
