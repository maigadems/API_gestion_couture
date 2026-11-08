from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.config import settings

ALGORITHME = "HS256"

_hacheur = PasswordHasher()


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    return _hacheur.hash(mot_de_passe)


def verifier_mot_de_passe(mot_de_passe: str, hash_enregistre: str) -> bool:
    try:
        return _hacheur.verify(hash_enregistre, mot_de_passe)
    except (VerificationError, InvalidHashError):
        return False


def creer_jeton(utilisateur_id: int) -> tuple[str, int]:
    """Renvoie le jeton JWT signé et sa durée de validité en secondes."""
    expires_in = settings.access_token_expire_minutes * 60
    expiration = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    charge = {"sub": str(utilisateur_id), "exp": expiration}
    return jwt.encode(charge, settings.secret_key, algorithm=ALGORITHME), expires_in


def lire_jeton(jeton: str) -> int | None:
    """Renvoie l'identifiant de l'utilisateur, ou None si le jeton est invalide ou expiré."""
    try:
        charge = jwt.decode(jeton, settings.secret_key, algorithms=[ALGORITHME])
        return int(charge["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
