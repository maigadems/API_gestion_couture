from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.routers.commun import route_a_implementer
from app.database import get_db
from app.schemas.clients import ClientCreate, ClientRead, ClientResume, ClientUpdate, Genre
from app.schemas.commun import Page
from app.services import clients as service

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", response_model=ClientRead, status_code=201)
def creer_client(client: ClientCreate, db: Session = Depends(get_db)):
    resultat = service.creer_client(db, client)
    db.commit()
    return resultat


@router.get("", response_model=Page[ClientRead])
def lister_clients(
    q: str | None = Query(default=None, min_length=2),
    genre: Genre | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    raise route_a_implementer()


@router.get("/{id}", response_model=ClientRead)
def lire_client(id: int, db: Session = Depends(get_db)):
    return service.lire_client(db, id)


@router.patch("/{id}", response_model=ClientRead)
def modifier_client(id: int, client: ClientUpdate, db: Session = Depends(get_db)):
    raise route_a_implementer()


@router.delete("/{id}", status_code=204)
def supprimer_client(id: int, db: Session = Depends(get_db)):
    raise route_a_implementer()


@router.get("/{id}/resume", response_model=ClientResume)
def lire_resume_client(id: int, db: Session = Depends(get_db)):
    raise route_a_implementer()
