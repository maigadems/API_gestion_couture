from fastapi import APIRouter

from app.routers.commun import route_a_implementer
from app.schemas.paiements import PaiementCreate, PaiementRead

router = APIRouter(tags=["Paiements"])


@router.post("/commandes/{id}/paiements", response_model=PaiementRead, status_code=201)
def encaisser_paiement(id: int, paiement: PaiementCreate):
    raise route_a_implementer()


@router.get("/commandes/{id}/paiements", response_model=list[PaiementRead])
def lister_paiements_commande(id: int):
    raise route_a_implementer()


@router.delete("/paiements/{id}", status_code=204)
def annuler_paiement(id: int):
    raise route_a_implementer()
