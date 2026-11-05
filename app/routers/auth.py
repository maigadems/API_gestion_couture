from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.routers.commun import route_a_implementer
from app.schemas.auth import Jeton
from app.schemas.utilisateurs import UtilisateurRead

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=Jeton)
def se_connecter(formulaire: OAuth2PasswordRequestForm = Depends()):
    raise route_a_implementer()


@router.get("/me", response_model=UtilisateurRead)
def lire_mon_profil():
    raise route_a_implementer()
