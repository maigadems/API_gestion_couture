from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import exiger_roles, get_current_user
from app.schemas.catalogue import TypeVetementCreate, TypeVetementRead, TypeVetementUpdate
from app.services import catalogue as service

router = APIRouter(
    prefix="/catalogue", tags=["Catalogue"], dependencies=[Depends(get_current_user)]
)


@router.post(
    "",
    response_model=TypeVetementRead,
    status_code=201,
    dependencies=[Depends(exiger_roles("admin"))],
)
def creer_prestation(prestation: TypeVetementCreate, db: Session = Depends(get_db)):
    resultat = service.creer_prestation(db, prestation)
    db.commit()
    return resultat


@router.get("", response_model=list[TypeVetementRead])
def lister_prestations(actifs_seulement: bool = True, db: Session = Depends(get_db)):
    return service.lister_prestations(db, actifs_seulement)


@router.get("/{id}", response_model=TypeVetementRead)
def lire_prestation(id: int, db: Session = Depends(get_db)):
    return service.lire_prestation(db, id)


@router.patch(
    "/{id}", response_model=TypeVetementRead, dependencies=[Depends(exiger_roles("admin"))]
)
def modifier_prestation(id: int, prestation: TypeVetementUpdate, db: Session = Depends(get_db)):
    resultat = service.modifier_prestation(db, id, prestation)
    db.commit()
    return resultat
