import pytest

from tests.outils import API, nouveau_client

URL = f"{API}/clients"


def test_creation_d_un_client_201(client, h_accueil):
    reponse = client.post(
        URL,
        json={"nom": "Diop", "prenom": "Fatou", "telephone": "771234567", "genre": "femme"},
        headers=h_accueil,
    )
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["id"] > 0
    assert corps["genre"] == "femme"
    assert corps["created_at"] and corps["updated_at"]


@pytest.mark.parametrize("role", ["h_admin", "h_accueil", "h_tailleur"])
def test_tout_utilisateur_connecte_peut_creer_un_client(client, request, role):
    entetes = request.getfixturevalue(role)
    reponse = client.post(
        URL, json={"nom": "Ba", "prenom": "Awa", "telephone": "700000001"}, headers=entetes
    )
    assert reponse.status_code == 201


def test_rg1_le_telephone_est_normalise(client, h_accueil):
    espaces = nouveau_client(client, h_accueil, telephone="77 123 45 67")
    assert espaces["telephone"] == "771234567"
    complexe = nouveau_client(client, h_accueil, telephone="+221 (76) 123-45.67")
    assert complexe["telephone"] == "+221761234567"


def test_rg1_doublon_409_meme_ecrit_autrement(client, h_accueil):
    nouveau_client(client, h_accueil, telephone="77 123 45 67")
    reponse = client.post(
        URL, json={"nom": "Autre", "prenom": "Client", "telephone": "771234567"}, headers=h_accueil
    )
    assert reponse.status_code == 409
    assert "téléphone" in reponse.json()["detail"]


@pytest.mark.parametrize("telephone", ["12345", "77a1234567", "", "+" + "1" * 21, "++771234567"])
def test_rg1_numero_invalide_422(client, h_accueil, telephone):
    reponse = client.post(
        URL, json={"nom": "Diop", "prenom": "Fatou", "telephone": telephone}, headers=h_accueil
    )
    assert reponse.status_code == 422
    assert isinstance(reponse.json()["detail"], str)


def test_rg1_limites_6_et_20_chiffres(client, h_accueil):
    assert nouveau_client(client, h_accueil, telephone="123456")["telephone"] == "123456"
    vingt = nouveau_client(client, h_accueil, telephone="+" + "9" * 20)
    assert len(vingt["telephone"]) == 21


def test_champ_obligatoire_manquant_422_en_francais(client, h_accueil):
    reponse = client.post(URL, json={"nom": "Diop", "telephone": "771234567"}, headers=h_accueil)
    assert reponse.status_code == 422
    assert reponse.json()["detail"] == "prenom : champ obligatoire"


def test_genre_inconnu_ou_email_invalide_422(client, h_accueil):
    base = {"nom": "Diop", "prenom": "Fatou", "telephone": "771234567"}
    assert client.post(URL, json={**base, "genre": "autre"}, headers=h_accueil).status_code == 422
    assert client.post(URL, json={**base, "email": "pas-un-mail"}, headers=h_accueil).status_code == 422


def test_lecture_d_un_client_et_404(client, h_accueil, fatou):
    assert client.get(f"{URL}/{fatou['id']}", headers=h_accueil).json()["nom"] == "Diop"
    assert client.get(f"{URL}/9999", headers=h_accueil).status_code == 404


def test_liste_paginee_format_et_valeurs_par_defaut(client, h_accueil):
    for i in range(3):
        nouveau_client(client, h_accueil, telephone=f"7000000{i}", nom=f"Nom{i}")
    corps = client.get(URL, headers=h_accueil).json()
    assert set(corps) == {"items", "total", "limit", "offset"}
    assert (corps["total"], corps["limit"], corps["offset"]) == (3, 20, 0)
    assert len(corps["items"]) == 3


def test_liste_triee_par_nom_puis_prenom(client, h_accueil):
    nouveau_client(client, h_accueil, telephone="700000001", nom="Sow", prenom="Zeynab")
    nouveau_client(client, h_accueil, telephone="700000002", nom="Ba", prenom="Moussa")
    nouveau_client(client, h_accueil, telephone="700000003", nom="Sow", prenom="Awa")
    noms = [(c["nom"], c["prenom"]) for c in client.get(URL, headers=h_accueil).json()["items"]]
    assert noms == [("Ba", "Moussa"), ("Sow", "Awa"), ("Sow", "Zeynab")]


def test_pagination_limit_et_offset(client, h_accueil):
    for i in range(5):
        nouveau_client(client, h_accueil, telephone=f"7000000{i}", nom=f"Nom{i}")
    page = client.get(URL, params={"limit": 2, "offset": 2}, headers=h_accueil).json()
    assert [c["nom"] for c in page["items"]] == ["Nom2", "Nom3"]
    assert (page["total"], page["limit"], page["offset"]) == (5, 2, 2)


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_pagination_bornes_422(client, h_accueil, params):
    assert client.get(URL, params=params, headers=h_accueil).status_code == 422


def test_recherche_de_2_caracteres_minimum(client, h_accueil):
    assert client.get(URL, params={"q": "a"}, headers=h_accueil).status_code == 422
    assert client.get(URL, params={"q": "di"}, headers=h_accueil).status_code == 200


def test_recherche_dans_nom_prenom_et_telephone(client, h_accueil):
    nouveau_client(client, h_accueil, telephone="771234567", nom="Diop", prenom="Fatou")
    nouveau_client(client, h_accueil, telephone="700000009", nom="Ba", prenom="Moussa")

    def trouves(q):
        return [c["nom"] for c in client.get(URL, params={"q": q}, headers=h_accueil).json()["items"]]

    assert trouves("dio") == ["Diop"]
    assert trouves("MOUS") == ["Ba"]
    assert trouves("1234") == ["Diop"]
    assert trouves("77 123") == ["Diop"]
    assert trouves("zzz") == []


def test_recherche_ne_traite_pas_les_jokers_sql_comme_des_jokers(client, h_accueil):
    nouveau_client(client, h_accueil)
    assert client.get(URL, params={"q": "%%"}, headers=h_accueil).json()["total"] == 0


def test_filtre_par_genre(client, h_accueil):
    nouveau_client(client, h_accueil, telephone="700000001", genre="femme")
    nouveau_client(client, h_accueil, telephone="700000002", genre="homme")
    femmes = client.get(URL, params={"genre": "femme"}, headers=h_accueil).json()
    assert femmes["total"] == 1
    assert client.get(URL, params={"genre": "inconnu"}, headers=h_accueil).status_code == 422


def test_modification_partielle_ne_change_que_les_champs_envoyes(client, h_accueil):
    cree = nouveau_client(client, h_accueil, adresse="Dakar", notes="Cliente fidèle")
    reponse = client.patch(f"{URL}/{cree['id']}", json={"adresse": "Thiès"}, headers=h_accueil)
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["adresse"] == "Thiès"
    assert (corps["nom"], corps["notes"], corps["telephone"]) == ("Diop", "Cliente fidèle", "771234567")


def test_modification_peut_vider_un_champ_facultatif(client, h_accueil):
    cree = nouveau_client(client, h_accueil, email="fatou@exemple.sn")
    corps = client.patch(f"{URL}/{cree['id']}", json={"email": None}, headers=h_accueil).json()
    assert corps["email"] is None


def test_garder_son_propre_numero_n_est_pas_un_doublon(client, h_accueil, fatou):
    reponse = client.patch(
        f"{URL}/{fatou['id']}", json={"telephone": "77 123 45 67", "nom": "Diop-Sy"}, headers=h_accueil
    )
    assert reponse.status_code == 200
    assert reponse.json()["nom"] == "Diop-Sy"


def test_prendre_le_numero_d_un_autre_client_409(client, h_accueil, fatou):
    autre = nouveau_client(client, h_accueil, telephone="700000001")
    reponse = client.patch(f"{URL}/{autre['id']}", json={"telephone": "771234567"}, headers=h_accueil)
    assert reponse.status_code == 409


@pytest.mark.parametrize(
    "corps",
    [{"nom": ""}, {"prenom": "   "}, {"telephone": ""}, {"nom": None}, {"telephone": None}],
)
def test_nom_prenom_telephone_ne_peuvent_pas_etre_vides_422(client, h_accueil, fatou, corps):
    assert client.patch(f"{URL}/{fatou['id']}", json=corps, headers=h_accueil).status_code == 422


def test_modification_d_un_client_inconnu_404(client, h_accueil):
    assert client.patch(f"{URL}/9999", json={"nom": "X"}, headers=h_accueil).status_code == 404


def test_updated_at_change_a_la_modification(client, h_accueil, fatou):
    apres = client.patch(f"{URL}/{fatou['id']}", json={"notes": "maj"}, headers=h_accueil).json()
    assert apres["updated_at"] >= fatou["updated_at"]
    assert apres["created_at"] == fatou["created_at"]
