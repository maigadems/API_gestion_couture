from fastapi import APIRouter

from app.routers.commun import route_a_implementer
from app.schemas.utilisateurs import UtilisateurCreate, UtilisateurRead, UtilisateurUpdate

router = APIRouter(prefix="/utilisateurs", tags=["Utilisateurs"])


@router.post("", response_model=UtilisateurRead, status_code=201)
def creer_utilisateur(utilisateur: UtilisateurCreate):
    raise route_a_implementer()


@router.get("", response_model=list[UtilisateurRead])
def lister_utilisateurs():
    raise route_a_implementer()


@router.get("/{id}", response_model=UtilisateurRead)
def lire_utilisateur(id: int):
    raise route_a_implementer()


@router.patch("/{id}", response_model=UtilisateurRead)
def modifier_utilisateur(id: int, utilisateur: UtilisateurUpdate):
    raise route_a_implementer()
