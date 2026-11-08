import re
from datetime import date, timedelta

import pytest

from tests.outils import API, ligne, nouvelle_commande, nouvelle_mesure

URL = f"{API}/commandes"


def creer(client, entetes, client_id, lignes, **champs):
    return client.post(
        URL, json={"client_id": client_id, "lignes": lignes, **champs}, headers=entetes
    )


def test_creation_201_avec_le_detail_complet(client, h_accueil, fatou, boubou, pantalon):
    reponse = creer(
        client, h_accueil, fatou["id"],
        [ligne(boubou, 2), ligne(pantalon, 1, prix_unitaire=10000)],
        remise=5000, notes="Pour la Tabaski",
    )
    assert reponse.status_code == 201
    commande = reponse.json()
    assert commande["statut"] == "en_attente"
    assert commande["montant_total"] == 2 * 35000 + 10000 - 5000
    assert (commande["montant_paye"], commande["solde"]) == (0, 75000)
    assert commande["remise"] == 5000
    assert commande["en_retard"] is False
    assert commande["client_nom"] == "Fatou Diop"
    assert commande["notes"] == "Pour la Tabaski"
    assert commande["paiements"] == [] and commande["livraison"] is None
    noms = {l["type_vetement_nom"]: l for l in commande["lignes"]}
    assert noms["Boubou"]["sous_total"] == 70000
    assert noms["Pantalon"]["prix_unitaire"] == 10000


def test_rg5_numero_au_format_cmd_annee_identifiant_sur_5_chiffres(client, h_accueil, fatou, boubou):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    assert re.fullmatch(rf"CMD-{date.today().year}-\d{{5}}", commande["numero"])
    assert commande["numero"] == f"CMD-{date.today().year}-{commande['id']:05d}"


def test_rg5_numeros_distincts(client, h_accueil, fatou, boubou):
    premier = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    second = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    assert premier["numero"] != second["numero"]
    assert second["id"] == premier["id"] + 1


def test_rg6_prix_du_catalogue_par_defaut_et_prix_negocie(client, h_accueil, fatou, boubou, pantalon):
    commande = nouvelle_commande(
        client, h_accueil, fatou["id"], [ligne(boubou), ligne(pantalon, 1, prix_unitaire=0)]
    )
    prix = {l["type_vetement_nom"]: l["prix_unitaire"] for l in commande["lignes"]}
    assert prix == {"Boubou": 35000, "Pantalon": 0}


def test_rg6_le_prix_negocie_ne_modifie_pas_le_catalogue(client, h_accueil, h_admin, fatou, boubou):
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou, 1, prix_unitaire=30000)])
    assert client.get(f"{API}/catalogue/{boubou['id']}", headers=h_admin).json()["prix_base"] == 35000


def test_rg6_prestation_inactive_422(client, h_accueil, h_admin, fatou, boubou):
    client.patch(f"{API}/catalogue/{boubou['id']}", json={"actif": False}, headers=h_admin)
    reponse = creer(client, h_accueil, fatou["id"], [ligne(boubou)])
    assert reponse.status_code == 422
    assert "Boubou" in reponse.json()["detail"]


def test_une_prestation_desactivee_ne_touche_pas_aux_anciennes_commandes(
    client, h_accueil, h_admin, fatou, boubou
):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    client.patch(f"{API}/catalogue/{boubou['id']}", json={"actif": False}, headers=h_admin)
    relue = client.get(f"{URL}/{commande['id']}", headers=h_accueil).json()
    assert relue["montant_total"] == 35000
    assert relue["lignes"][0]["type_vetement_nom"] == "Boubou"


def test_references_inconnues_404(client, h_accueil, fatou, boubou):
    assert creer(client, h_accueil, 9999, [ligne(boubou)]).status_code == 404
    assert creer(client, h_accueil, fatou["id"], [{"type_vetement_id": 9999}]).status_code == 404


@pytest.mark.parametrize("lignes", [[], [{"type_vetement_id": 1, "quantite": 0}]])
def test_au_moins_une_ligne_de_quantite_positive_422(client, h_accueil, fatou, boubou, lignes):
    assert creer(client, h_accueil, fatou["id"], lignes).status_code == 422


def test_rg7_la_remise_ne_peut_pas_depasser_la_somme_des_prestations_422(client, h_accueil, fatou, boubou):
    reponse = creer(client, h_accueil, fatou["id"], [ligne(boubou)], remise=35001)
    assert reponse.status_code == 422
    assert "remise" in reponse.json()["detail"]
    assert creer(client, h_accueil, fatou["id"], [ligne(boubou)], remise=-1).status_code == 422


def test_rg7_une_remise_egale_a_la_somme_est_permise(client, h_accueil, fatou, boubou):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)], remise=35000)
    assert commande["montant_total"] == 0


def test_rg8_date_prevue_par_defaut_le_plus_long_delai(client, h_accueil, fatou, boubou, pantalon):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou), ligne(pantalon)])
    assert commande["date_commande"] == date.today().isoformat()
    assert commande["date_livraison_prevue"] == (date.today() + timedelta(days=10)).isoformat()


def test_rg8_date_prevue_choisie_et_date_anterieure_422(client, h_accueil, fatou, boubou):
    demain = (date.today() + timedelta(days=1)).isoformat()
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)], date_livraison_prevue=demain)
    assert commande["date_livraison_prevue"] == demain
    hier = (date.today() - timedelta(days=1)).isoformat()
    assert creer(client, h_accueil, fatou["id"], [ligne(boubou)], date_livraison_prevue=hier).status_code == 422


def test_rg9_les_dernieres_mesures_du_client_sont_rattachees_automatiquement(
    client, h_accueil, h_tailleur, fatou, boubou
):
    nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100, date_prise="2026-01-01")
    recente = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=102, date_prise="2026-05-01")
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    assert commande["mesure_id"] == recente["id"]


def test_rg9_sans_mesures_la_commande_n_en_a_pas(client, h_accueil, fatou, boubou):
    assert nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])["mesure_id"] is None


def test_rg9_mesure_choisie_explicitement(client, h_accueil, h_tailleur, fatou, boubou):
    ancienne = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100, date_prise="2026-01-01")
    nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=102, date_prise="2026-05-01")
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)], mesure_id=ancienne["id"])
    assert commande["mesure_id"] == ancienne["id"]


def test_rg9_mesures_d_un_autre_client_422(client, h_accueil, h_tailleur, fatou, boubou):
    autre = client.post(
        f"{API}/clients", json={"nom": "Ba", "prenom": "Awa", "telephone": "700000001"}, headers=h_accueil
    ).json()
    mesure_autre = nouvelle_mesure(client, h_tailleur, autre["id"], tour_poitrine=90)
    reponse = creer(client, h_accueil, fatou["id"], [ligne(boubou)], mesure_id=mesure_autre["id"])
    assert reponse.status_code == 422
    assert creer(client, h_accueil, fatou["id"], [ligne(boubou)], mesure_id=9999).status_code == 404


def test_rg4_des_mesures_utilisees_par_une_commande_ne_peuvent_pas_etre_supprimees(
    client, h_accueil, h_tailleur, fatou, boubou
):
    mesure = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100)
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    assert client.delete(f"{API}/mesures/{mesure['id']}", headers=h_tailleur).status_code == 409
    assert client.get(f"{API}/mesures/{mesure['id']}", headers=h_tailleur).status_code == 200


@pytest.mark.parametrize("role, attendu", [("h_accueil", 201), ("h_admin", 201), ("h_tailleur", 403)])
def test_seuls_l_accueil_et_l_admin_creent_des_commandes(client, request, fatou, boubou, role, attendu):
    entetes = request.getfixturevalue(role)
    assert creer(client, entetes, fatou["id"], [ligne(boubou)]).status_code == attendu


def test_rg15_la_creation_inscrit_la_premiere_ligne_de_l_historique(client, h_accueil, fatou, boubou):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    historique = client.get(f"{URL}/{commande['id']}/historique", headers=h_accueil).json()
    assert len(historique) == 1
    assert historique[0]["ancien_statut"] is None
    assert historique[0]["nouveau_statut"] == "en_attente"
    moi = client.get(f"{API}/auth/me", headers=h_accueil).json()
    assert historique[0]["utilisateur_id"] == moi["id"]
    assert commande["cree_par_id"] == moi["id"]


def test_detail_et_404(client, h_tailleur, h_accueil, fatou, boubou):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    assert client.get(f"{URL}/{commande['id']}", headers=h_tailleur).status_code == 200
    assert client.get(f"{URL}/9999", headers=h_tailleur).status_code == 404
    assert client.get(f"{URL}/9999/historique", headers=h_tailleur).status_code == 404
