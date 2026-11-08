from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exiger_roles, get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.livraisons import (
    LivraisonConfirmation,
    LivraisonPlanification,
    LivraisonRead,
    LivraisonTournee,
    StatutLivraison,
)
from app.services import livraisons as service

router = APIRouter(tags=["Livraisons"], dependencies=[Depends(get_current_user)])


@router.put(
    "/commandes/{id}/livraison",
    response_model=LivraisonRead,
    dependencies=[Depends(exiger_roles("accueil"))],
)
def planifier_livraison(id: int, livraison: LivraisonPlanification, db: Session = Depends(get_db)):
    resultat = service.planifier_livraison(db, id, livraison)
    db.commit()
    return resultat


@router.get("/commandes/{id}/livraison", response_model=LivraisonRead)
def lire_livraison(id: int, db: Session = Depends(get_db)):
    return service.lire_livraison(db, id)


@router.post("/commandes/{id}/livraison/confirmer", response_model=LivraisonRead)
def confirmer_livraison(
    id: int,
    confirmation: LivraisonConfirmation | None = None,
    utilisateur: Utilisateur = Depends(exiger_roles("accueil")),
    db: Session = Depends(get_db),
):
    resultat = service.confirmer_livraison(db, id, confirmation, utilisateur)
    db.commit()
    return resultat


@router.get("/livraisons", response_model=list[LivraisonTournee])
def lister_livraisons(
    statut: StatutLivraison | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
    db: Session = Depends(get_db),
):
    return service.lister_livraisons(db, statut, date_min, date_max)
