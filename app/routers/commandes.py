from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.routers.commun import route_a_implementer
from app.database import get_db
from app.dependencies import exiger_roles, get_current_user
from app.models.utilisateur import Utilisateur
from app.schemas.commandes import (
    ChangementStatut,
    CommandeCreate,
    CommandeDetail,
    CommandeListe,
    CommandeUpdate,
    HistoriqueStatutRead,
    LigneCommandeCreate,
    StatutCommande,
)
from app.schemas.commun import Page
from app.services import commandes as service

router = APIRouter(tags=["Commandes"], dependencies=[Depends(get_current_user)])


@router.post("/commandes", response_model=CommandeDetail, status_code=201)
def creer_commande(
    commande: CommandeCreate,
    utilisateur: Utilisateur = Depends(exiger_roles("accueil")),
    db: Session = Depends(get_db),
):
    resultat = service.creer_commande(db, commande, utilisateur)
    db.commit()
    return resultat


@router.get("/commandes", response_model=Page[CommandeListe])
def lister_commandes(
    statut: StatutCommande | None = None,
    client_id: int | None = None,
    en_retard: bool | None = None,
    date_min: date | None = None,
    date_max: date | None = None,
    numero: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return service.lister_commandes(
        db, statut, client_id, en_retard, date_min, date_max, numero, limit, offset
    )


@router.get("/commandes/{id}", response_model=CommandeDetail)
def lire_commande(id: int, db: Session = Depends(get_db)):
    return service.lire_commande(db, id)


@router.patch(
    "/commandes/{id}",
    response_model=CommandeDetail,
    dependencies=[Depends(exiger_roles("accueil"))],
)
def modifier_commande(id: int, commande: CommandeUpdate, db: Session = Depends(get_db)):
    raise route_a_implementer()


@router.post("/commandes/{id}/statut", response_model=CommandeDetail)
def changer_statut(
    id: int,
    changement: ChangementStatut,
    utilisateur: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raise route_a_implementer()


@router.get("/commandes/{id}/historique", response_model=list[HistoriqueStatutRead])
def lire_historique(id: int, db: Session = Depends(get_db)):
    raise route_a_implementer()


@router.post(
    "/commandes/{id}/lignes",
    response_model=CommandeDetail,
    status_code=201,
    dependencies=[Depends(exiger_roles("accueil"))],
)
def ajouter_ligne(id: int, ligne: LigneCommandeCreate, db: Session = Depends(get_db)):
    raise route_a_implementer()
@router.delete(
    "/commandes/{id}/lignes/{ligne_id}",
    response_model=CommandeDetail,
    dependencies=[Depends(exiger_roles("accueil"))],
)
def retirer_ligne(id: int, ligne_id: int, db: Session = Depends(get_db)):
    raise route_a_implementer()
@router.get("/clients/{id}/commandes", response_model=Page[CommandeListe])
def lister_commandes_client(
    id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return service.lister_commandes_client(db, id, limit, offset)
