from datetime import date

from tests.outils import API, ligne, nouvelle_commande, nouvelle_mesure, payer, poser_statut

URL = f"{API}/clients"


def test_l_admin_supprime_un_client_204(client, h_admin, fatou):
    assert client.delete(f"{URL}/{fatou['id']}", headers=h_admin).status_code == 204
    assert client.get(f"{URL}/{fatou['id']}", headers=h_admin).status_code == 404


def test_la_suppression_est_reservee_a_l_admin_403(client, h_accueil, h_tailleur, fatou):
    assert client.delete(f"{URL}/{fatou['id']}", headers=h_accueil).status_code == 403
    assert client.delete(f"{URL}/{fatou['id']}", headers=h_tailleur).status_code == 403
    assert client.get(f"{URL}/{fatou['id']}", headers=h_accueil).status_code == 200


def test_client_inconnu_404(client, h_admin):
    assert client.delete(f"{URL}/9999", headers=h_admin).status_code == 404
    assert client.get(f"{URL}/9999/resume", headers=h_admin).status_code == 404


def test_rg4_un_client_qui_a_des_commandes_ne_peut_pas_etre_supprime_409(client, h_admin, h_accueil, fatou, boubou):
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    reponse = client.delete(f"{URL}/{fatou['id']}", headers=h_admin)
    assert reponse.status_code == 409
    assert "commande" in reponse.json()["detail"]
    assert client.get(f"{URL}/{fatou['id']}", headers=h_admin).status_code == 200


def test_rg4_meme_une_commande_annulee_empeche_la_suppression(client, h_admin, h_accueil, fatou, boubou):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    poser_statut(client, h_accueil, commande["id"], "annulee")
    assert client.delete(f"{URL}/{fatou['id']}", headers=h_admin).status_code == 409


def test_la_suppression_supprime_aussi_les_mesures_du_client(client, h_admin, h_tailleur, fatou):
    mesure = nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100)
    assert client.delete(f"{URL}/{fatou['id']}", headers=h_admin).status_code == 204
    assert client.get(f"{API}/mesures/{mesure['id']}", headers=h_admin).status_code == 404


def test_resume_d_un_client_sans_commande(client, h_accueil, fatou):
    resume = client.get(f"{URL}/{fatou['id']}/resume", headers=h_accueil).json()
    assert resume == {
        "nb_commandes": 0,
        "chiffre_affaires": 0,
        "total_paye": 0,
        "solde_du": 0,
        "derniere_commande": None,
        "a_des_mesures": False,
    }


def test_resume_chiffres_et_commandes_annulees_exclues(client, h_accueil, h_tailleur, fatou, boubou, pantalon):
    premiere = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou, 2)])  # 70 000
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(pantalon)], remise=2000)  # 10 000
    annulee = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    payer(client, h_accueil, premiere["id"], 25000)
    poser_statut(client, h_accueil, annulee["id"], "annulee")
    nouvelle_mesure(client, h_tailleur, fatou["id"], tour_poitrine=100)

    resume = client.get(f"{URL}/{fatou['id']}/resume", headers=h_tailleur).json()
    assert resume["nb_commandes"] == 2
    assert resume["chiffre_affaires"] == 80000
    assert resume["total_paye"] == 25000
    assert resume["solde_du"] == 55000
    assert resume["derniere_commande"] == date.today().isoformat()
    assert resume["a_des_mesures"] is True
