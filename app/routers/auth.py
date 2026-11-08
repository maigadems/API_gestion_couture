from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.auth import Jeton
from app.schemas.utilisateurs import UtilisateurRead
from app.services import auth as service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=Jeton)
def se_connecter(
    formulaire: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    return service.connexion(db, formulaire.username, formulaire.password)


@router.get("/me", response_model=UtilisateurRead)
def lire_mon_profil(utilisateur: Utilisateur = Depends(get_current_user)):
    return utilisateur
