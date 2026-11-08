from app.database import SessionLocal
from app.models.utilisateur import Utilisateur
from tests.outils import API, MOT_DE_PASSE, entetes_de

URL = f"{API}/utilisateurs"


def compte(email="nouveau@atelier.sn", role="accueil", nom_complet="Nouveau Compte", **extra):
    return {
        "email": email,
        "nom_complet": nom_complet,
        "mot_de_passe": MOT_DE_PASSE,
        "role": role,
        **extra,
    }


def test_admin_cree_un_compte(client, h_admin):
    reponse = client.post(URL, json=compte(), headers=h_admin)
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["email"] == "nouveau@atelier.sn"
    assert corps["role"] == "accueil"
    assert corps["actif"] is True


def test_rg21_mot_de_passe_hache_et_jamais_renvoye(client, h_admin):
    reponse = client.post(URL, json=compte(), headers=h_admin)
    assert "mot_de_passe" not in reponse.json()
    assert "mot_de_passe_hash" not in reponse.json()
    with SessionLocal() as db:
        enregistre = db.query(Utilisateur).filter_by(email="nouveau@atelier.sn").one()
    assert enregistre.mot_de_passe_hash != MOT_DE_PASSE
    assert enregistre.mot_de_passe_hash.startswith("$argon2")


def test_rg21_mot_de_passe_de_8_caracteres_minimum(client, h_admin):
    reponse = client.post(URL, json=compte(mot_de_passe="court"), headers=h_admin)
    assert reponse.status_code == 422
    assert "mot_de_passe" in reponse.json()["detail"]


def test_email_deja_utilise_409_meme_avec_une_autre_casse(client, h_admin):
    assert client.post(URL, json=compte(), headers=h_admin).status_code == 201
    doublon = client.post(URL, json=compte(email="NOUVEAU@atelier.sn"), headers=h_admin)
    assert doublon.status_code == 409


def test_donnees_invalides_422(client, h_admin):
    assert client.post(URL, json=compte(email="pas-un-email"), headers=h_admin).status_code == 422
    assert client.post(URL, json=compte(role="patron"), headers=h_admin).status_code == 422
    assert client.post(URL, json=compte(nom_complet="  "), headers=h_admin).status_code == 422


def test_liste_triee_par_nom(client, h_admin):
    client.post(URL, json=compte("z@atelier.sn", nom_complet="Zoe Zidane"), headers=h_admin)
    client.post(URL, json=compte("a@atelier.sn", nom_complet="Alice Ba"), headers=h_admin)
    noms = [u["nom_complet"] for u in client.get(URL, headers=h_admin).json()]
    assert noms == sorted(noms)
    assert noms.index("Alice Ba") < noms.index("Zoe Zidane")


def test_detail_et_404(client, h_admin):
    cree = client.post(URL, json=compte(), headers=h_admin).json()
    assert client.get(f"{URL}/{cree['id']}", headers=h_admin).json()["email"] == cree["email"]
    assert client.get(f"{URL}/9999", headers=h_admin).status_code == 404


def test_modification_partielle_nom_role_etat(client, h_admin):
    cree = client.post(URL, json=compte(), headers=h_admin).json()
    reponse = client.patch(
        f"{URL}/{cree['id']}", json={"nom_complet": "Nom Modifié", "role": "tailleur"}, headers=h_admin
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert (corps["nom_complet"], corps["role"], corps["actif"]) == ("Nom Modifié", "tailleur", True)
    desactive = client.patch(f"{URL}/{cree['id']}", json={"actif": False}, headers=h_admin).json()
    assert desactive["actif"] is False
    assert desactive["role"] == "tailleur"


def test_changement_de_mot_de_passe(client, h_admin):
    cree = client.post(URL, json=compte(), headers=h_admin).json()
    client.patch(f"{URL}/{cree['id']}", json={"mot_de_passe": "nouveaumdp123"}, headers=h_admin)
    ancien = client.post(
        f"{API}/auth/login", data={"username": cree["email"], "password": MOT_DE_PASSE}
    )
    nouveau = client.post(
        f"{API}/auth/login", data={"username": cree["email"], "password": "nouveaumdp123"}
    )
    assert (ancien.status_code, nouveau.status_code) == (401, 200)


def test_rg24_un_admin_ne_peut_pas_se_desactiver_lui_meme(client, h_admin):
    mon_id = client.get(f"{API}/auth/me", headers=h_admin).json()["id"]
    reponse = client.patch(f"{URL}/{mon_id}", json={"actif": False}, headers=h_admin)
    assert reponse.status_code == 409


def test_rg24_un_admin_ne_peut_pas_retirer_son_propre_role(client, h_admin):
    mon_id = client.get(f"{API}/auth/me", headers=h_admin).json()["id"]
    assert client.patch(f"{URL}/{mon_id}", json={"role": "accueil"}, headers=h_admin).status_code == 409
    # Garder son rôle ou changer son nom reste permis
    assert client.patch(f"{URL}/{mon_id}", json={"role": "admin"}, headers=h_admin).status_code == 200
    assert client.patch(f"{URL}/{mon_id}", json={"nom_complet": "Le Patron"}, headers=h_admin).status_code == 200


def test_rg24_un_admin_peut_retrograder_un_autre_compte(client, h_admin):
    autre = client.post(URL, json=compte(role="admin"), headers=h_admin).json()
    reponse = client.patch(f"{URL}/{autre['id']}", json={"role": "tailleur"}, headers=h_admin)
    assert reponse.status_code == 200


def test_gestion_des_comptes_reservee_a_l_admin(client, h_accueil, h_tailleur):
    for entetes in (h_accueil, h_tailleur):
        assert client.get(URL, headers=entetes).status_code == 403
        assert client.post(URL, json=compte(), headers=entetes).status_code == 403
        assert client.patch(f"{URL}/1", json={"actif": False}, headers=entetes).status_code == 403


def test_nouveau_compte_peut_se_connecter(client, h_admin):
    client.post(URL, json=compte(role="tailleur"), headers=h_admin)
    entetes = entetes_de(client, "nouveau@atelier.sn")
    assert client.get(f"{API}/auth/me", headers=entetes).json()["role"] == "tailleur"
