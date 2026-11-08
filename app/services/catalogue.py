from sqlalchemy import select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, Introuvable
from app.models.type_vetement import TypeVetement
from app.schemas.catalogue import TypeVetementCreate, TypeVetementUpdate


def verifier_nom_libre(db: Session, nom: str, sauf_id: int | None = None) -> None:
    requete = select(TypeVetement.id).where(TypeVetement.nom == nom)
    if sauf_id is not None:
        requete = requete.where(TypeVetement.id != sauf_id)
    if db.scalar(requete) is not None:
        raise Conflit("Une prestation portant ce nom existe déjà")


def creer_prestation(db: Session, donnees: TypeVetementCreate) -> TypeVetement:
    verifier_nom_libre(db, donnees.nom)
    prestation = TypeVetement(**donnees.model_dump())
    db.add(prestation)
    db.flush()
    return prestation


def lister_prestations(db: Session, actifs_seulement: bool) -> list[TypeVetement]:
    requete = select(TypeVetement).order_by(TypeVetement.nom)
    if actifs_seulement:
        requete = requete.where(TypeVetement.actif.is_(True))
    return list(db.scalars(requete))


def lire_prestation(db: Session, prestation_id: int) -> TypeVetement:
    prestation = db.get(TypeVetement, prestation_id)
    if prestation is None:
        raise Introuvable("Prestation introuvable")
    return prestation


def modifier_prestation(
    db: Session, prestation_id: int, donnees: TypeVetementUpdate
) -> TypeVetement:
    prestation = lire_prestation(db, prestation_id)
    champs = donnees.model_dump(exclude_unset=True)
    if "nom" in champs:
        verifier_nom_libre(db, champs["nom"], sauf_id=prestation.id)
    for nom, valeur in champs.items():
        setattr(prestation, nom, valeur)
    db.flush()
    return prestation
