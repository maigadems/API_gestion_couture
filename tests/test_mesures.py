from datetime import date

import pytest

from tests.outils import API, nouvelle_mesure

NOMS_DES_MESURES = [
    "taille_cm", "tour_cou", "carrure_dos", "longueur_epaule", "tour_poitrine", "tour_taille",
    "tour_bassin", "longueur_manche", "tour_bras", "tour_poignet", "longueur_dos", "longueur_haut",
    "longueur_pantalon", "tour_cuisse", "tour_genou", "bas_pantalon", "entrejambe", "longueur_robe",
]


def url(client_id: int) -> str:
    return f"{API}/clients/{client_id}/mesures"


def test_le_tailleur_prend_des_mesures_201(client, h_tailleur, fatou):
    reponse = client.post(
        url(fatou["id"]), json={"tour_poitrine": 100, "tour_taille": 85.5}, headers=h_tailleur
    )
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["client_id"] == fatou["id"]
    assert corps["tour_poitrine"] == 100
    assert corps["tour_taille"] == 85.5
    assert corps["tour_cou"] is None
    assert corps["date_prise"] == date.today().isoformat()
    moi = client.get(f"{API}/auth/me", headers=h_tailleur).json()
    assert corps["prise_par_id"] == moi["id"]


def test_l_accueil_ne_peut_pas_prendre_de_mesures_403(client, h_accueil, fatou):
    reponse = client.post(url(fatou["id"]), json={"tour_poitrine": 100}, headers=h_accueil)
    assert reponse.status_code == 403


def test_l_admin_peut_tout_faire_dont_prendre_des_mesures(client, h_admin, fatou):
    assert client.post(url(fatou["id"]), json={"tour_poitrine": 100}, headers=h_admin).status_code == 201


def test_rg2_une_prise_contient_au_moins_une_mesure(client, h_tailleur, fatou):
    for corps in ({}, {"notes": "rien mesuré"}, {"tour_cou": None}):
        reponse = client.post(url(fatou["id"]), json=corps, headers=h_tailleur)
        assert reponse.status_code == 422, corps
        assert "au moins une mesure" in reponse.json()["detail"]


@pytest.mark.parametrize("valeur", [0, -5, 300.1, 1000])
def test_rg2_mesure_strictement_positive_et_au_plus_300_cm(client, h_tailleur, fatou, valeur):
    reponse = client.post(url(fatou["id"]), json={"tour_cou": valeur}, headers=h_tailleur)
    assert reponse.status_code == 422


def test_rg2_300_cm_est_accepte(client, h_tailleur, fatou):
    assert client.post(url(fatou["id"]), json={"tour_cou": 300}, headers=h_tailleur).status_code == 201


def test_les_18_mesures_sont_acceptees(client, h_tailleur, fatou):
    assert len(NOMS_DES_MESURES) == 18
    reponse = client.post(
        url(fatou["id"]), json={nom: 50 for nom in NOMS_DES_MESURES}, headers=h_tailleur
    )
    assert reponse.status_code == 201
    assert all(reponse.json()[nom] == 50 for nom in NOMS_DES_MESURES)


def test_client_inconnu_404(client, h_tailleur):
    assert client.post(url(9999), json={"tour_cou": 40}, headers=h_tailleur).status_code == 404
    assert client.get(url(9999), headers=h_tailleur).status_code == 404
    assert client.get(url(9999) + "/derniere", headers=h_tailleur).status_code == 404


def test_rg3_historique_complet_la_plus_recente_d_abord(client, h_tailleur, fatou):
    for jour in ("2026-01-10", "2026-03-05", "2026-02-01"):
        nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100, date_prise=jour)
    dates = [m["date_prise"] for m in client.get(url(fatou["id"]), headers=h_tailleur).json()]
    assert dates == ["2026-03-05", "2026-02-01", "2026-01-10"]


def test_rg3_les_dernieres_mesures_sont_la_prise_de_date_la_plus_recente(client, h_tailleur, fatou):
    nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100, date_prise="2026-03-05")
    nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=101, date_prise="2026-01-10")
    derniere = client.get(url(fatou["id"]) + "/derniere", headers=h_tailleur).json()
    assert derniere["date_prise"] == "2026-03-05"
    assert derniere["tour_poitrine"] == 100


def test_dernieres_mesures_404_si_aucune_prise(client, h_tailleur, fatou):
    reponse = client.get(url(fatou["id"]) + "/derniere", headers=h_tailleur)
    assert reponse.status_code == 404
    assert client.get(url(fatou["id"]), headers=h_tailleur).json() == []


def test_lecture_d_une_prise_et_404(client, h_accueil, h_tailleur, fatou):
    mesure = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100)
    assert client.get(f"{API}/mesures/{mesure['id']}", headers=h_accueil).json()["id"] == mesure["id"]
    assert client.get(f"{API}/mesures/9999", headers=h_accueil).status_code == 404


def test_correction_d_une_erreur_de_saisie(client, h_tailleur, fatou):
    mesure = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100, tour_taille=80)
    reponse = client.patch(f"{API}/mesures/{mesure['id']}", json={"tour_poitrine": 102}, headers=h_tailleur)
    assert reponse.status_code == 200
    assert (reponse.json()["tour_poitrine"], reponse.json()["tour_taille"]) == (102, 80)


def test_correction_qui_supprimerait_toutes_les_mesures_422(client, h_tailleur, fatou):
    mesure = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100)
    reponse = client.patch(f"{API}/mesures/{mesure['id']}", json={"tour_poitrine": None}, headers=h_tailleur)
    assert reponse.status_code == 422
    # la prise n'a pas changé
    assert client.get(f"{API}/mesures/{mesure['id']}", headers=h_tailleur).json()["tour_poitrine"] == 100


def test_retirer_une_mesure_est_permis_s_il_en_reste_une(client, h_tailleur, fatou):
    mesure = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100, tour_taille=80)
    corps = client.patch(f"{API}/mesures/{mesure['id']}", json={"tour_taille": None}, headers=h_tailleur).json()
    assert corps["tour_taille"] is None


def test_correction_reservee_au_tailleur_et_a_l_admin(client, h_accueil, h_tailleur, fatou):
    mesure = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100)
    assert client.patch(f"{API}/mesures/{mesure['id']}", json={"tour_poitrine": 99}, headers=h_accueil).status_code == 403
    assert client.delete(f"{API}/mesures/{mesure['id']}", headers=h_accueil).status_code == 403


def test_suppression_204_puis_404(client, h_tailleur, fatou):
    mesure = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100)
    assert client.delete(f"{API}/mesures/{mesure['id']}", headers=h_tailleur).status_code == 204
    assert client.get(f"{API}/mesures/{mesure['id']}", headers=h_tailleur).status_code == 404
    assert client.delete(f"{API}/mesures/{mesure['id']}", headers=h_tailleur).status_code == 404
