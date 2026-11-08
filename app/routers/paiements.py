from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exiger_roles, get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.paiements import PaiementCreate, PaiementRead
from app.services import paiements as service

router = APIRouter(tags=["Paiements"], dependencies=[Depends(get_current_user)])


@router.post("/commandes/{id}/paiements", response_model=PaiementRead, status_code=201)
def encaisser_paiement(
    id: int,
    paiement: PaiementCreate,
    utilisateur: Utilisateur = Depends(exiger_roles("accueil")),
    db: Session = Depends(get_db),
):
    resultat = service.encaisser_paiement(db, id, paiement, utilisateur)
    db.commit()
    return resultat


@router.get("/commandes/{id}/paiements", response_model=list[PaiementRead])
def lister_paiements_commande(id: int, db: Session = Depends(get_db)):
    return service.lister_paiements(db, id)


@router.delete("/paiements/{id}", status_code=204, dependencies=[Depends(exiger_roles("admin"))])
def annuler_paiement(id: int, db: Session = Depends(get_db)):
    service.annuler_paiement(db, id)
    db.commit()
