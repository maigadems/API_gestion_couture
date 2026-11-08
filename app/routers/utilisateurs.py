from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exiger_roles, get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateurs import UtilisateurCreate, UtilisateurRead, UtilisateurUpdate
from app.services import utilisateurs as service

router = APIRouter(
    prefix="/utilisateurs",
    tags=["Utilisateurs"],
    dependencies=[Depends(exiger_roles("admin"))],
)


@router.post("", response_model=UtilisateurRead, status_code=201)
def creer_utilisateur(utilisateur: UtilisateurCreate, db: Session = Depends(get_db)):
    resultat = service.creer_utilisateur(db, utilisateur)
    db.commit()
    return resultat


@router.get("", response_model=list[UtilisateurRead])
def lister_utilisateurs(db: Session = Depends(get_db)):
    return service.lister_utilisateurs(db)


@router.get("/{id}", response_model=UtilisateurRead)
def lire_utilisateur(id: int, db: Session = Depends(get_db)):
    return service.lire_utilisateur(db, id)


@router.patch("/{id}", response_model=UtilisateurRead)
def modifier_utilisateur(
    id: int,
    utilisateur: UtilisateurUpdate,
    courant: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resultat = service.modifier_utilisateur(db, id, utilisateur, courant)
    db.commit()
    return resultat
