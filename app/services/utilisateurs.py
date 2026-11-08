from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import Conflit, Introuvable
from app.models.utilisateur import Utilisateur
from app.schemas.utilisateurs import UtilisateurCreate, UtilisateurUpdate
from app.security import hacher_mot_de_passe


def trouver_par_email(db: Session, email: str) -> Utilisateur | None:
    return db.scalar(
        select(Utilisateur).where(func.lower(Utilisateur.email) == email.strip().lower())
    )


def creer_utilisateur(db: Session, donnees: UtilisateurCreate) -> Utilisateur:
    if trouver_par_email(db, donnees.email) is not None:
        raise Conflit("Un compte avec cet e-mail existe déjà")
    utilisateur = Utilisateur(
        email=donnees.email.strip().lower(),
        nom_complet=donnees.nom_complet,
        mot_de_passe_hash=hacher_mot_de_passe(donnees.mot_de_passe),
        role=donnees.role.value,
    )
    db.add(utilisateur)
    db.flush()
    return utilisateur


def lister_utilisateurs(db: Session) -> list[Utilisateur]:
    return list(db.scalars(select(Utilisateur).order_by(Utilisateur.nom_complet, Utilisateur.id)))


def lire_utilisateur(db: Session, utilisateur_id: int) -> Utilisateur:
    utilisateur = db.get(Utilisateur, utilisateur_id)
    if utilisateur is None:
        raise Introuvable("Utilisateur introuvable")
    return utilisateur


def modifier_utilisateur(
    db: Session, utilisateur_id: int, donnees: UtilisateurUpdate, courant: Utilisateur
) -> Utilisateur:
    utilisateur = lire_utilisateur(db, utilisateur_id)
    champs = donnees.model_dump(exclude_unset=True, mode="json")
    # RG24 : un administrateur ne peut pas se couper l'accès à lui-même
    if utilisateur.id == courant.id:
        if champs.get("actif") is False:
            raise Conflit("Un administrateur ne peut pas se désactiver lui-même")
        if "role" in champs and champs["role"] != "admin":
            raise Conflit("Un administrateur ne peut pas retirer son propre rôle d'administrateur")
    mot_de_passe = champs.pop("mot_de_passe", None)
    if mot_de_passe is not None:
        utilisateur.mot_de_passe_hash = hacher_mot_de_passe(mot_de_passe)
    for nom, valeur in champs.items():
        setattr(utilisateur, nom, valeur)
    db.flush()
    return utilisateur
