from fastapi import APIRouter, Query

from app.routers.commun import route_a_implementer
from app.schemas.clients import ClientCreate, ClientRead, ClientResume, ClientUpdate, Genre
from app.schemas.commun import Page

router = APIRouter(prefix="/clients", tags=["Clients"])


@router.post("", response_model=ClientRead, status_code=201)
def creer_client(client: ClientCreate):
    raise route_a_implementer()


@router.get("", response_model=Page[ClientRead])
def lister_clients(
    q: str | None = Query(default=None, min_length=2),
    genre: Genre | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    raise route_a_implementer()


@router.get("/{id}", response_model=ClientRead)
def lire_client(id: int):
    raise route_a_implementer()


@router.patch("/{id}", response_model=ClientRead)
def modifier_client(id: int, client: ClientUpdate):
    raise route_a_implementer()


@router.delete("/{id}", status_code=204)
def supprimer_client(id: int):
    raise route_a_implementer()


@router.get("/{id}/resume", response_model=ClientResume)
def lire_resume_client(id: int):
    raise route_a_implementer()
