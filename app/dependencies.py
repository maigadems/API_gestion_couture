from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import Interdit, NonAuthentifie
from app.models.utilisateur import Utilisateur
from app.security import lire_jeton

schema_oauth2 = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_current_user(
    jeton: str | None = Depends(schema_oauth2), db: Session = Depends(get_db)
) -> Utilisateur:
    if jeton is None:
        raise NonAuthentifie("Authentification requise : jeton manquant")
    utilisateur_id = lire_jeton(jeton)
    if utilisateur_id is None:
        raise NonAuthentifie("Jeton invalide ou expiré")
    utilisateur = db.get(Utilisateur, utilisateur_id)
    # RG22 : l'état du compte est relu à chaque requête, même avec un jeton valide.
    if utilisateur is None or not utilisateur.actif:
        raise NonAuthentifie("Compte inconnu ou désactivé")
    return utilisateur


def exiger_roles(*roles: str):
    """Dépendance qui n'accepte que les rôles indiqués. L'administrateur passe toujours."""

    def verifier(utilisateur: Utilisateur = Depends(get_current_user)) -> Utilisateur:
        if utilisateur.role != "admin" and utilisateur.role not in roles:
            if roles == ("admin",):
                raise Interdit("Cette action est réservée à l'administrateur")
            raise Interdit(
                "Droits insuffisants : cette action est réservée aux rôles "
                + ", ".join(sorted({*roles, "admin"}))
            )
        return utilisateur

    return verifier
