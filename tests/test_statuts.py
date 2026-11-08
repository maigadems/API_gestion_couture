import pytest

from tests.outils import API, CHEMINS, amener_au_statut, ligne, nouvelle_commande, poser_statut

URL = f"{API}/commandes"


@pytest.fixture
def commande(client, h_accueil, fatou, boubou):
    return nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])


def test_parcours_complet_avec_aller_retour_essayage_retouches(client, h_accueil, h_tailleur, commande):
    suite = ["en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"]
    for statut in suite:
        reponse = poser_statut(client, h_tailleur, commande["id"], statut)
        assert reponse.status_code == 200, (statut, reponse.text)
        assert reponse.json()["statut"] == statut
    historique = client.get(f"{URL}/{commande['id']}/historique", headers=h_accueil).json()
    assert [(h["ancien_statut"], h["nouveau_statut"]) for h in historique] == [
        (None, "en_attente"),
        ("en_attente", "en_coupe"),
        ("en_coupe", "en_couture"),
        ("en_couture", "essayage"),
        ("essayage", "retouches"),
        ("retouches", "essayage"),
        ("essayage", "terminee"),
    ]


def test_message_de_transition_interdite_indique_les_statuts_possibles(client, h_accueil, commande):
    reponse = poser_statut(client, h_accueil, commande["id"], "terminee")
    assert reponse.status_code == 409
    assert reponse.json()["detail"] == (
        "Transition interdite : en_attente → terminee. Statuts possibles : annulee, en_coupe"
    )


@pytest.mark.parametrize(
    "depart, cible",
    [
        ("en_attente", "essayage"),
        ("en_attente", "retouches"),
        ("en_coupe", "terminee"),
        ("en_coupe", "essayage"),
        ("en_couture", "en_coupe"),
        ("en_couture", "retouches"),
        ("essayage", "en_couture"),
        ("retouches", "en_couture"),
        ("terminee", "en_couture"),
        ("terminee", "annulee"),
    ],
)
def test_transitions_interdites_409(client, h_accueil, commande, depart, cible):
    amener_au_statut(client, h_accueil, commande["id"], depart)
    reponse = poser_statut(client, h_accueil, commande["id"], cible)
    assert reponse.status_code == 409
    assert "Statuts possibles" in reponse.json()["detail"]
    assert client.get(f"{URL}/{commande['id']}", headers=h_accueil).json()["statut"] == depart


@pytest.mark.parametrize("depart", ["en_attente", "en_coupe", "en_couture", "essayage", "retouches"])
def test_l_annulation_est_possible_depuis_chaque_statut_en_cours(client, h_accueil, commande, depart):
    amener_au_statut(client, h_accueil, commande["id"], depart)
    reponse = poser_statut(client, h_accueil, commande["id"], "annulee")
    assert reponse.status_code == 200
    assert reponse.json()["statut"] == "annulee"


def test_les_statuts_finaux_n_ont_aucune_issue(client, h_accueil, commande):
    poser_statut(client, h_accueil, commande["id"], "annulee")
    reponse = poser_statut(client, h_accueil, commande["id"], "en_coupe")
    assert reponse.status_code == 409
    assert "aucun" in reponse.json()["detail"]


def test_rg13_demander_le_statut_deja_en_cours_409(client, h_accueil, commande):
    reponse = poser_statut(client, h_accueil, commande["id"], "en_attente")
    assert reponse.status_code == 409
    assert "déjà" in reponse.json()["detail"]


def test_rg13_livree_ne_peut_pas_etre_pose_par_la_route_de_statut(client, h_accueil, commande):
    amener_au_statut(client, h_accueil, commande["id"], "terminee")
    reponse = poser_statut(client, h_accueil, commande["id"], "livree")
    assert reponse.status_code == 409
    assert "livraison" in reponse.json()["detail"]
    assert client.get(f"{URL}/{commande['id']}", headers=h_accueil).json()["statut"] == "terminee"


def test_rg14_le_tailleur_ne_peut_pas_annuler_403(client, h_tailleur, commande):
    reponse = poser_statut(client, h_tailleur, commande["id"], "annulee")
    assert reponse.status_code == 403
    assert "tailleur" in reponse.json()["detail"]
    assert client.get(f"{URL}/{commande['id']}", headers=h_tailleur).json()["statut"] == "en_attente"


def test_l_accueil_et_l_admin_peuvent_annuler(client, h_accueil, h_admin, fatou, boubou):
    for entetes in (h_accueil, h_admin):
        commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
        assert poser_statut(client, entetes, commande["id"], "annulee").status_code == 200


def test_tout_utilisateur_connecte_peut_changer_le_statut(client, h_accueil, h_tailleur, h_admin, commande):
    assert poser_statut(client, h_tailleur, commande["id"], "en_coupe").status_code == 200
    assert poser_statut(client, h_accueil, commande["id"], "en_couture").status_code == 200
    assert poser_statut(client, h_admin, commande["id"], "essayage").status_code == 200


def test_rg15_historique_avec_utilisateur_commentaire_et_ordre_chronologique(
    client, h_accueil, h_tailleur, commande
):
    poser_statut(client, h_tailleur, commande["id"], "en_coupe", "Tissu reçu")
    poser_statut(client, h_accueil, commande["id"], "annulee", "Client injoignable")
    historique = client.get(f"{URL}/{commande['id']}/historique", headers=h_accueil).json()
    assert [h["nouveau_statut"] for h in historique] == ["en_attente", "en_coupe", "annulee"]
    assert historique[1]["commentaire"] == "Tissu reçu"
    assert historique[2]["commentaire"] == "Client injoignable"
    assert historique[1]["utilisateur_id"] != historique[2]["utilisateur_id"]
    assert all(h["date_changement"] for h in historique)


def test_un_commentaire_vide_n_est_pas_enregistre(client, h_accueil, commande):
    poser_statut(client, h_accueil, commande["id"], "en_coupe", "   ")
    historique = client.get(f"{URL}/{commande['id']}/historique", headers=h_accueil).json()
    assert historique[-1]["commentaire"] is None


def test_statut_inconnu_422_et_commande_inconnue_404(client, h_accueil, commande):
    assert poser_statut(client, h_accueil, commande["id"], "fini").status_code == 422
    assert poser_statut(client, h_accueil, 9999, "en_coupe").status_code == 404


def test_les_chemins_de_test_sont_valides():
    assert set(CHEMINS) == {"en_attente", "en_coupe", "en_couture", "essayage", "retouches", "terminee"}
