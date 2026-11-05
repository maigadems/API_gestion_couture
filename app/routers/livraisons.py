from datetime import date

from fastapi import APIRouter

from app.routers.commun import route_a_implementer
from app.schemas.livraisons import (
    LivraisonConfirmation,
    LivraisonPlanification,
    LivraisonRead,
    LivraisonTournee,
    StatutLivraison,
)

router = APIRouter(tags=["Livraisons"])


@router.put("/commandes/{id}/livraison", response_model=LivraisonRead)
def planifier_livraison(id: int, livraison: LivraisonPlanification):
    raise route_a_implementer()


@router.get("/commandes/{id}/livraison", response_model=LivraisonRead)
def lire_livraison(id: int):
    raise route_a_implementer()


@router.post("/commandes/{id}/livraison/confirmer", response_model=LivraisonRead)
def confirmer_livraison(id: int, confirmation: LivraisonConfirmation | None = None):
    raise route_a_implementer()


@router.get("/livraisons", response_model=list[LivraisonTournee])
def lister_livraisons(
    statut: StatutLivraison | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
):
    raise route_a_implementer()
