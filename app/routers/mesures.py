from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exiger_roles, get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.mesures import MesureCreate, MesureRead, MesureUpdate
from app.services import mesures as service

router = APIRouter(tags=["Mesures"], dependencies=[Depends(get_current_user)])


@router.post("/clients/{id}/mesures", response_model=MesureRead, status_code=201)
def creer_mesure(
    id: int,
    mesure: MesureCreate,
    utilisateur: Utilisateur = Depends(exiger_roles("tailleur")),
    db: Session = Depends(get_db),
):
    resultat = service.creer_mesure(db, id, mesure, utilisateur)
    db.commit()
    return resultat


@router.get("/clients/{id}/mesures", response_model=list[MesureRead])
def lister_mesures_client(id: int, db: Session = Depends(get_db)):
    return service.lister_mesures_client(db, id)


@router.get("/clients/{id}/mesures/derniere", response_model=MesureRead)
def lire_dernieres_mesures(id: int, db: Session = Depends(get_db)):
    return service.lire_dernieres_mesures(db, id)


@router.get("/mesures/{id}", response_model=MesureRead)
def lire_mesure(id: int, db: Session = Depends(get_db)):
    return service.lire_mesure(db, id)


@router.patch(
    "/mesures/{id}", response_model=MesureRead, dependencies=[Depends(exiger_roles("tailleur"))]
)
def modifier_mesure(id: int, mesure: MesureUpdate, db: Session = Depends(get_db)):
    resultat = service.modifier_mesure(db, id, mesure)
    db.commit()
    return resultat


@router.delete("/mesures/{id}", status_code=204, dependencies=[Depends(exiger_roles("tailleur"))])
def supprimer_mesure(id: int, db: Session = Depends(get_db)):
    service.supprimer_mesure(db, id)
    db.commit()
