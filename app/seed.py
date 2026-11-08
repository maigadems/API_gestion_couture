"""Initialisation de la base : python -m app.seed

Crée le premier administrateur (ADMIN_EMAIL / ADMIN_PASSWORD du .env) et le catalogue de départ.
Le script peut être relancé sans danger : ce qui existe déjà n'est pas recréé.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.type_vetement import TypeVetement
from app.models.utilisateur import Utilisateur
from app.security import hacher_mot_de_passe

CATALOGUE = [
    ("Boubou", "Boubou homme en bazin ou brodé", 35000, 10),
    ("Costume 2 pièces", "Veste et pantalon", 85000, 14),
    ("Robe", "Robe sur mesure", 30000, 7),
    ("Ensemble wax", "Tenue deux pièces en wax", 25000, 7),
    ("Chemise", "Chemise sur mesure", 15000, 5),
    ("Pantalon", "Pantalon sur mesure", 12000, 4),
    ("Retouche", "Ourlet, rétrécissement, remplacement de fermeture", 3000, 2),
]


def creer_administrateur(db: Session) -> bool:
    if not settings.admin_email or not settings.admin_password:
        raise SystemExit("ADMIN_EMAIL et ADMIN_PASSWORD doivent être définis (fichier .env)")
    if len(settings.admin_password) < 8:
        raise SystemExit("ADMIN_PASSWORD doit contenir au moins 8 caractères")
    email = settings.admin_email.strip().lower()
    if db.scalar(select(Utilisateur.id).where(Utilisateur.email == email)) is not None:
        return False
    db.add(
        Utilisateur(
            email=email,
            nom_complet=settings.admin_nom_complet,
            mot_de_passe_hash=hacher_mot_de_passe(settings.admin_password),
            role="admin",
        )
    )
    return True


def creer_catalogue(db: Session) -> int:
    crees = 0
    for nom, description, prix_base, delai_jours in CATALOGUE:
        if db.scalar(select(TypeVetement.id).where(TypeVetement.nom == nom)) is None:
            db.add(
                TypeVetement(
                    nom=nom, description=description, prix_base=prix_base, delai_jours=delai_jours
                )
            )
            crees += 1
    return crees


def executer() -> tuple[bool, int]:
    with SessionLocal() as db:
        admin_cree = creer_administrateur(db)
        prestations_creees = creer_catalogue(db)
        db.commit()
    return admin_cree, prestations_creees


if __name__ == "__main__":
    admin_cree, prestations_creees = executer()
    print("Administrateur créé" if admin_cree else "Administrateur déjà présent")
    print(f"{prestations_creees} prestation(s) ajoutée(s) au catalogue")
