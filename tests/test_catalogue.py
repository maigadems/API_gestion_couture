import pytest

from tests.outils import API, nouvelle_prestation

URL = f"{API}/catalogue"


def test_admin_ajoute_une_prestation_201(client, h_admin):
    reponse = client.post(
        URL,
        json={"nom": "Boubou", "description": "En bazin", "prix_base": 35000, "delai_jours": 10},
        headers=h_admin,
    )
    assert reponse.status_code == 201
    corps = reponse.json()
    assert (corps["nom"], corps["prix_base"], corps["delai_jours"], corps["actif"]) == (
        "Boubou", 35000, 10, True,
    )


def test_nom_unique_409(client, h_admin, boubou):
    reponse = client.post(
        URL, json={"nom": "Boubou", "prix_base": 1, "delai_jours": 1}, headers=h_admin
    )
    assert reponse.status_code == 409


@pytest.mark.parametrize("role", ["h_accueil", "h_tailleur"])
def test_ecriture_reservee_a_l_admin(client, request, role, boubou):
    entetes = request.getfixturevalue(role)
    assert client.post(
        URL, json={"nom": "Robe", "prix_base": 30000, "delai_jours": 7}, headers=entetes
    ).status_code == 403
    assert client.patch(f"{URL}/{boubou['id']}", json={"prix_base": 1}, headers=entetes).status_code == 403


def test_lecture_ouverte_a_tous_les_roles(client, h_accueil, h_tailleur, boubou):
    for entetes in (h_accueil, h_tailleur):
        assert client.get(URL, headers=entetes).status_code == 200
        assert client.get(f"{URL}/{boubou['id']}", headers=entetes).status_code == 200


@pytest.mark.parametrize(
    "corps",
    [
        {"nom": "X", "prix_base": -1, "delai_jours": 1},
        {"nom": "X", "prix_base": 1, "delai_jours": -1},
        {"nom": " ", "prix_base": 1, "delai_jours": 1},
        {"nom": "X", "delai_jours": 1},
    ],
)
def test_donnees_invalides_422(client, h_admin, corps):
    assert client.post(URL, json=corps, headers=h_admin).status_code == 422


def test_liste_triee_par_nom_et_actives_seulement_par_defaut(client, h_admin):
    nouvelle_prestation(client, h_admin, "Robe", 30000, 7)
    ancienne = nouvelle_prestation(client, h_admin, "Ancienne", 1000, 1)
    nouvelle_prestation(client, h_admin, "Chemise", 15000, 5)
    client.patch(f"{URL}/{ancienne['id']}", json={"actif": False}, headers=h_admin)

    noms = [p["nom"] for p in client.get(URL, headers=h_admin).json()]
    assert noms == ["Chemise", "Robe"]

    tous = client.get(URL, params={"actifs_seulement": False}, headers=h_admin).json()
    assert [p["nom"] for p in tous] == ["Ancienne", "Chemise", "Robe"]


def test_detail_404(client, h_admin):
    assert client.get(f"{URL}/9999", headers=h_admin).status_code == 404


def test_modification_prix_delai_et_nom(client, h_admin, boubou):
    reponse = client.patch(
        f"{URL}/{boubou['id']}",
        json={"prix_base": 40000, "delai_jours": 12, "nom": "Grand boubou"},
        headers=h_admin,
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert (corps["prix_base"], corps["delai_jours"], corps["nom"]) == (40000, 12, "Grand boubou")


def test_renommer_vers_un_nom_existant_409_mais_garder_le_sien_ok(client, h_admin, boubou, pantalon):
    assert client.patch(f"{URL}/{pantalon['id']}", json={"nom": "Boubou"}, headers=h_admin).status_code == 409
    assert client.patch(f"{URL}/{boubou['id']}", json={"nom": "Boubou"}, headers=h_admin).status_code == 200
