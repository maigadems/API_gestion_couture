from datetime import date, timedelta

import pytest

from tests.outils import (
    API,
    ligne,
    modifier_en_base,
    nouvelle_commande,
    nouvelle_mesure,
    poser_statut,
)

URL = f"{API}/commandes"


@pytest.fixture
def commande(client, h_accueil, fatou, boubou):
    return nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou, 2)])


def patch(client, entetes, commande_id, **champs):
    return client.patch(f"{URL}/{commande_id}", json=champs, headers=entetes)


def test_modification_de_la_remise_recalcule_les_montants(client, h_accueil, commande):
    assert commande["montant_total"] == 70000
    reponse = patch(client, h_accueil, commande["id"], remise=10000, notes="Remise fidélité")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert (corps["remise"], corps["montant_total"], corps["solde"]) == (10000, 60000, 60000)
    assert corps["notes"] == "Remise fidélité"


def test_modification_partielle_ne_change_que_les_champs_envoyes(client, h_accueil, commande):
    corps = patch(client, h_accueil, commande["id"], notes="Nouvelle note").json()
    assert corps["remise"] == 0
    assert corps["date_livraison_prevue"] == commande["date_livraison_prevue"]


def test_rg7_remise_superieure_a_la_somme_422(client, h_accueil, commande):
    assert patch(client, h_accueil, commande["id"], remise=70001).status_code == 422
    relue = client.get(f"{URL}/{commande['id']}", headers=h_accueil).json()
    assert relue["remise"] == 0


def test_rg8_date_prevue_modifiable_mais_pas_avant_la_commande(client, h_accueil, commande):
    dans_un_mois = (date.today() + timedelta(days=30)).isoformat()
    assert patch(client, h_accueil, commande["id"], date_livraison_prevue=dans_un_mois).json()[
        "date_livraison_prevue"
    ] == dans_un_mois
    hier = (date.today() - timedelta(days=1)).isoformat()
    assert patch(client, h_accueil, commande["id"], date_livraison_prevue=hier).status_code == 422


def test_rg9_mesures_modifiables_si_elles_appartiennent_au_client(
    client, h_accueil, h_tailleur, fatou, commande
):
    mesure = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100)
    assert patch(client, h_accueil, commande["id"], mesure_id=mesure["id"]).json()["mesure_id"] == mesure["id"]
    autre = client.post(
        f"{API}/clients", json={"nom": "Ba", "prenom": "Awa", "telephone": "700000001"}, headers=h_accueil
    ).json()
    mesure_autre = nouvelle_mesure(client, h_tailleur, autre["id"], tour_poitrine=90)
    assert patch(client, h_accueil, commande["id"], mesure_id=mesure_autre["id"]).status_code == 422
    assert patch(client, h_accueil, commande["id"], mesure_id=None).json()["mesure_id"] is None


@pytest.mark.parametrize("statut", ["livree", "annulee"])
def test_rg12_une_commande_livree_ou_annulee_n_est_plus_modifiable_409(client, h_accueil, commande, statut):
    modifier_en_base(commande["id"], statut=statut)
    assert patch(client, h_accueil, commande["id"], notes="trop tard").status_code == 409
    assert client.post(
        f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": 1}, headers=h_accueil
    ).status_code == 409


def test_rg12_annulee_par_l_api_puis_modification_409(client, h_accueil, commande):
    assert poser_statut(client, h_accueil, commande["id"], "annulee").status_code == 200
    assert patch(client, h_accueil, commande["id"], notes="trop tard").status_code == 409


def test_modification_reservee_a_l_accueil_et_a_l_admin(client, h_tailleur, h_admin, commande):
    assert patch(client, h_tailleur, commande["id"], notes="x").status_code == 403
    assert patch(client, h_admin, commande["id"], notes="x").status_code == 200


def test_modification_d_une_commande_inconnue_404(client, h_accueil):
    assert patch(client, h_accueil, 9999, notes="x").status_code == 404


def test_rg10_ajouter_une_ligne_recalcule_les_montants(client, h_accueil, commande, pantalon):
    reponse = client.post(
        f"{URL}/{commande['id']}/lignes",
        json={"type_vetement_id": pantalon["id"], "quantite": 2, "description": "Lin beige"},
        headers=h_accueil,
    )
    assert reponse.status_code == 201
    corps = reponse.json()
    assert len(corps["lignes"]) == 2
    assert corps["montant_total"] == 70000 + 2 * 12000
    assert corps["solde"] == corps["montant_total"]


def test_ajouter_une_prestation_inactive_ou_inconnue(client, h_accueil, h_admin, commande, pantalon):
    client.patch(f"{API}/catalogue/{pantalon['id']}", json={"actif": False}, headers=h_admin)
    ajout = client.post(f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": pantalon["id"]}, headers=h_accueil)
    assert ajout.status_code == 422
    inconnue = client.post(f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": 9999}, headers=h_accueil)
    assert inconnue.status_code == 404


def test_rg10_les_lignes_ne_changent_que_tant_que_la_commande_est_en_attente(
    client, h_accueil, commande, pantalon
):
    assert poser_statut(client, h_accueil, commande["id"], "en_coupe").status_code == 200
    ajout = client.post(f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": pantalon["id"]}, headers=h_accueil)
    assert ajout.status_code == 409
    assert "en_attente" in ajout.json()["detail"]
    retrait = client.delete(f"{URL}/{commande['id']}/lignes/{commande['lignes'][0]['id']}", headers=h_accueil)
    assert retrait.status_code == 409


def test_rg10_retirer_une_ligne_recalcule_les_montants(client, h_accueil, commande, pantalon):
    avec_pantalon = client.post(
        f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": pantalon["id"]}, headers=h_accueil
    ).json()
    ligne_pantalon = next(l for l in avec_pantalon["lignes"] if l["type_vetement_nom"] == "Pantalon")
    reponse = client.delete(f"{URL}/{commande['id']}/lignes/{ligne_pantalon['id']}", headers=h_accueil)
    assert reponse.status_code == 200
    assert len(reponse.json()["lignes"]) == 1
    assert reponse.json()["montant_total"] == 70000


def test_rg10_une_commande_garde_toujours_au_moins_une_ligne_409(client, h_accueil, commande):
    reponse = client.delete(f"{URL}/{commande['id']}/lignes/{commande['lignes'][0]['id']}", headers=h_accueil)
    assert reponse.status_code == 409
    assert "au moins une ligne" in reponse.json()["detail"]


def test_retirer_une_ligne_inconnue_ou_d_une_autre_commande_404(
    client, h_accueil, fatou, boubou, commande, pantalon
):
    autre = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou), ligne(pantalon)])
    assert client.delete(f"{URL}/{commande['id']}/lignes/9999", headers=h_accueil).status_code == 404
    ligne_d_une_autre = autre["lignes"][0]["id"]
    assert client.delete(f"{URL}/{commande['id']}/lignes/{ligne_d_une_autre}", headers=h_accueil).status_code == 404


def test_retirer_une_ligne_ne_peut_pas_laisser_une_remise_trop_grande_422(client, h_accueil, fatou, boubou, pantalon):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou), ligne(pantalon)], remise=20000)
    ligne_boubou = next(l for l in commande["lignes"] if l["type_vetement_nom"] == "Boubou")
    reponse = client.delete(f"{URL}/{commande['id']}/lignes/{ligne_boubou['id']}", headers=h_accueil)
    assert reponse.status_code == 422


def test_lignes_reservees_a_l_accueil_et_a_l_admin(client, h_tailleur, commande, pantalon):
    ajout = client.post(f"{URL}/{commande['id']}/lignes", json={"type_vetement_id": pantalon["id"]}, headers=h_tailleur)
    assert ajout.status_code == 403
    retrait = client.delete(f"{URL}/{commande['id']}/lignes/{commande['lignes'][0]['id']}", headers=h_tailleur)
    assert retrait.status_code == 403
