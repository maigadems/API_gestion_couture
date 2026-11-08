from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import update

from app.config import settings
from app.database import SessionLocal
from app.models.utilisateur import Utilisateur
from app.security import ALGORITHME
from tests.outils import API, MOT_DE_PASSE, creer_utilisateur_en_base, entetes_de

LOGIN = f"{API}/auth/login"
ME = f"{API}/auth/me"


def test_connexion_reussie_renvoie_un_jeton(client):
    creer_utilisateur_en_base("accueil", "marie@atelier.test")
    reponse = client.post(LOGIN, data={"username": "marie@atelier.test", "password": MOT_DE_PASSE})
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["access_token"]
    assert corps["token_type"] == "bearer"
    assert corps["expires_in"] == settings.access_token_expire_minutes * 60


def test_rg23_meme_reponse_pour_email_inconnu_et_mauvais_mot_de_passe(client):
    creer_utilisateur_en_base("accueil", "marie@atelier.test")
    inconnu = client.post(LOGIN, data={"username": "inconnu@atelier.test", "password": MOT_DE_PASSE})
    faux = client.post(LOGIN, data={"username": "marie@atelier.test", "password": "mauvaismdp1"})
    assert inconnu.status_code == faux.status_code == 401
    assert inconnu.json() == faux.json()


def test_connexion_refusee_pour_un_compte_desactive(client):
    creer_utilisateur_en_base("accueil", "ancien@atelier.test", actif=False)
    reponse = client.post(LOGIN, data={"username": "ancien@atelier.test", "password": MOT_DE_PASSE})
    assert reponse.status_code == 401


def test_rg22_compte_desactive_refuse_meme_avec_un_jeton_encore_valide(client):
    utilisateur_id = creer_utilisateur_en_base("accueil", "marie@atelier.test")
    entetes = entetes_de(client, "marie@atelier.test")
    assert client.get(ME, headers=entetes).status_code == 200
    with SessionLocal() as db:
        db.execute(update(Utilisateur).where(Utilisateur.id == utilisateur_id).values(actif=False))
        db.commit()
    assert client.get(ME, headers=entetes).status_code == 401


def test_sans_jeton_401(client):
    reponse = client.get(ME)
    assert reponse.status_code == 401
    assert reponse.headers["www-authenticate"] == "Bearer"
    assert isinstance(reponse.json()["detail"], str)


def test_jeton_invalide_401(client):
    reponse = client.get(ME, headers={"Authorization": "Bearer nimportequoi"})
    assert reponse.status_code == 401


def test_jeton_expire_401(client):
    utilisateur_id = creer_utilisateur_en_base("accueil", "marie@atelier.test")
    expire = datetime.now(timezone.utc) - timedelta(hours=1)
    jeton = jwt.encode({"sub": str(utilisateur_id), "exp": expire}, settings.secret_key, ALGORITHME)
    assert client.get(ME, headers={"Authorization": f"Bearer {jeton}"}).status_code == 401


def test_jeton_signe_avec_une_autre_cle_401(client):
    utilisateur_id = creer_utilisateur_en_base("accueil", "marie@atelier.test")
    valide_longtemps = datetime.now(timezone.utc) + timedelta(hours=1)
    jeton = jwt.encode(
        {"sub": str(utilisateur_id), "exp": valide_longtemps}, "une-autre-cle-secrete-assez-longue!", ALGORITHME
    )
    assert client.get(ME, headers={"Authorization": f"Bearer {jeton}"}).status_code == 401


def test_me_renvoie_le_profil_sans_donnee_sensible(client, h_accueil):
    reponse = client.get(ME, headers=h_accueil)
    assert reponse.status_code == 200
    profil = reponse.json()
    assert profil["email"] == "accueil@atelier.test"
    assert profil["role"] == "accueil"
    assert set(profil) == {"id", "email", "nom_complet", "role", "actif", "created_at"}


def test_identifiants_manquants_422(client):
    reponse = client.post(LOGIN, data={"username": "marie@atelier.test"})
    assert reponse.status_code == 422
    assert "password" in reponse.json()["detail"]
