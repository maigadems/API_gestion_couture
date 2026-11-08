from sqlalchemy.orm import Session

from app.exceptions import NonAuthentifie
from app.models.utilisateur import Utilisateur
from app.security import creer_jeton, hacher_mot_de_passe, verifier_mot_de_passe
from app.services.utilisateurs import trouver_par_email

# Sert à faire le même travail de hachage quand l'e-mail est inconnu :
# la durée de réponse ne révèle pas quels comptes existent (RG23).
HASH_FACTICE = hacher_mot_de_passe("mot-de-passe-factice")


def authentifier(db: Session, email: str, mot_de_passe: str) -> Utilisateur:
    utilisateur = trouver_par_email(db, email)
    hash_a_verifier = utilisateur.mot_de_passe_hash if utilisateur else HASH_FACTICE
    mot_de_passe_valide = verifier_mot_de_passe(mot_de_passe, hash_a_verifier)
    # RG23 : même message que l'e-mail soit inconnu, le mot de passe faux ou le compte désactivé
    if utilisateur is None or not mot_de_passe_valide or not utilisateur.actif:
        raise NonAuthentifie("E-mail ou mot de passe incorrect")
    return utilisateur


def connexion(db: Session, email: str, mot_de_passe: str) -> dict:
    utilisateur = authentifier(db, email, mot_de_passe)
    jeton, expires_in = creer_jeton(utilisateur.id)
    return {"access_token": jeton, "token_type": "bearer", "expires_in": expires_in}
