from datetime import date, timedelta

import pytest

from tests.outils import API, amener_au_statut, ligne, nouvelle_commande, payer, poser_statut

URL = f"{API}/commandes"


@pytest.fixture
def commande(client, h_accueil, fatou, boubou):
    """Une commande de 70 000 FCFA."""
    return nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou, 2)])


def lire(client, entetes, commande_id):
    return client.get(f"{URL}/{commande_id}", headers=entetes).json()


def test_un_acompte_met_a_jour_le_montant_paye_et_le_solde(client, h_accueil, commande):
    reponse = payer(client, h_accueil, commande["id"], 20000, "wave", reference="WAVE-123")
    assert reponse.status_code == 201
    paiement = reponse.json()
    assert (paiement["montant"], paiement["mode"], paiement["reference"]) == (20000, "wave", "WAVE-123")
    assert paiement["date_paiement"] == date.today().isoformat()
    relue = lire(client, h_accueil, commande["id"])
    assert (relue["montant_paye"], relue["solde"]) == (20000, 50000)
    assert len(relue["paiements"]) == 1


@pytest.mark.parametrize("mode", ["especes", "wave", "orange_money", "virement", "cheque"])
def test_les_cinq_modes_de_paiement(client, h_accueil, commande, mode):
    assert payer(client, h_accueil, commande["id"], 1000, mode).status_code == 201


def test_mode_inconnu_422(client, h_accueil, commande):
    assert payer(client, h_accueil, commande["id"], 1000, "bitcoin").status_code == 422


@pytest.mark.parametrize("montant", [0, -1000])
def test_rg16_montant_strictement_positif_422(client, h_accueil, commande, montant):
    assert payer(client, h_accueil, commande["id"], montant).status_code == 422


def test_rg16_paiement_superieur_au_solde_409(client, h_accueil, commande):
    payer(client, h_accueil, commande["id"], 60000)
    reponse = payer(client, h_accueil, commande["id"], 10001)
    assert reponse.status_code == 409
    assert "10000" in reponse.json()["detail"]
    assert lire(client, h_accueil, commande["id"])["montant_paye"] == 60000


def test_rg16_le_solde_exact_est_accepte_et_ramene_le_solde_a_zero(client, h_accueil, commande):
    assert payer(client, h_accueil, commande["id"], 70000).status_code == 201
    assert lire(client, h_accueil, commande["id"])["solde"] == 0
    assert payer(client, h_accueil, commande["id"], 1).status_code == 409


def test_rg16_date_future_422_et_date_passee_acceptee(client, h_accueil, commande):
    demain = (date.today() + timedelta(days=1)).isoformat()
    assert payer(client, h_accueil, commande["id"], 1000, date_paiement=demain).status_code == 422
    hier = (date.today() - timedelta(days=1)).isoformat()
    reponse = payer(client, h_accueil, commande["id"], 1000, date_paiement=hier)
    assert reponse.status_code == 201
    assert reponse.json()["date_paiement"] == hier


def test_rg16_refuse_sur_une_commande_annulee_409(client, h_accueil, commande):
    poser_statut(client, h_accueil, commande["id"], "annulee")
    reponse = payer(client, h_accueil, commande["id"], 1000)
    assert reponse.status_code == 409
    assert "annulée" in reponse.json()["detail"]


def test_paiement_sur_une_commande_inconnue_404(client, h_accueil):
    assert payer(client, h_accueil, 9999, 1000).status_code == 404
    assert client.get(f"{URL}/9999/paiements", headers=h_accueil).status_code == 404


def test_liste_des_paiements_dans_l_ordre_de_saisie(client, h_accueil, h_tailleur, commande):
    for montant in (30000, 10000, 5000):
        payer(client, h_accueil, commande["id"], montant)
    paiements = client.get(f"{URL}/{commande['id']}/paiements", headers=h_tailleur).json()
    assert [p["montant"] for p in paiements] == [30000, 10000, 5000]
    moi = client.get(f"{API}/auth/me", headers=h_accueil).json()
    assert paiements[0]["enregistre_par_id"] == moi["id"]


def test_seuls_l_accueil_et_l_admin_encaissent(client, h_tailleur, h_admin, commande):
    assert payer(client, h_tailleur, commande["id"], 1000).status_code == 403
    assert payer(client, h_admin, commande["id"], 1000).status_code == 201


def test_rg17_annuler_un_paiement_recalcule_le_montant_paye_et_le_solde(client, h_accueil, h_admin, commande):
    premier = payer(client, h_accueil, commande["id"], 30000).json()
    payer(client, h_accueil, commande["id"], 10000)
    assert client.delete(f"{API}/paiements/{premier['id']}", headers=h_admin).status_code == 204
    relue = lire(client, h_accueil, commande["id"])
    assert (relue["montant_paye"], relue["solde"]) == (10000, 60000)
    assert [p["montant"] for p in relue["paiements"]] == [10000]


def test_annuler_un_paiement_est_reserve_a_l_admin(client, h_accueil, h_tailleur, commande):
    paiement = payer(client, h_accueil, commande["id"], 1000).json()
    assert client.delete(f"{API}/paiements/{paiement['id']}", headers=h_accueil).status_code == 403
    assert client.delete(f"{API}/paiements/{paiement['id']}", headers=h_tailleur).status_code == 403
    assert lire(client, h_accueil, commande["id"])["montant_paye"] == 1000


def test_annuler_un_paiement_inconnu_404(client, h_admin):
    assert client.delete(f"{API}/paiements/9999", headers=h_admin).status_code == 404


def test_rg7_le_total_ne_peut_pas_passer_sous_le_montant_deja_paye_409(client, h_accueil, commande):
    payer(client, h_accueil, commande["id"], 60000)
    reponse = client.patch(f"{URL}/{commande['id']}", json={"remise": 30000}, headers=h_accueil)
    assert reponse.status_code == 409
    assert "déjà payé" in reponse.json()["detail"]
    accepte = client.patch(f"{URL}/{commande['id']}", json={"remise": 10000}, headers=h_accueil)
    assert accepte.status_code == 200
    assert accepte.json()["solde"] == 0


def test_rg7_retirer_une_ligne_sous_le_montant_paye_409(client, h_accueil, fatou, boubou, pantalon):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou), ligne(pantalon)])
    payer(client, h_accueil, commande["id"], 40000)
    ligne_boubou = next(l for l in commande["lignes"] if l["type_vetement_nom"] == "Boubou")
    reponse = client.delete(f"{URL}/{commande['id']}/lignes/{ligne_boubou['id']}", headers=h_accueil)
    assert reponse.status_code == 409


def test_rg14_annuler_une_commande_qui_a_recu_un_acompte_exige_un_commentaire(client, h_accueil, commande):
    payer(client, h_accueil, commande["id"], 20000)
    sans = poser_statut(client, h_accueil, commande["id"], "annulee")
    assert sans.status_code == 422
    assert "acompte" in sans.json()["detail"]
    vide = poser_statut(client, h_accueil, commande["id"], "annulee", "   ")
    assert vide.status_code == 422
    avec = poser_statut(client, h_accueil, commande["id"], "annulee", "Remboursement en espèces")
    assert avec.status_code == 200
    historique = client.get(f"{URL}/{commande['id']}/historique", headers=h_accueil).json()
    assert historique[-1]["commentaire"] == "Remboursement en espèces"


def test_annuler_sans_acompte_n_exige_pas_de_commentaire(client, h_accueil, commande):
    assert poser_statut(client, h_accueil, commande["id"], "annulee").status_code == 200


def test_on_peut_encaisser_le_solde_apres_la_fin_de_la_production(client, h_accueil, commande):
    amener_au_statut(client, h_accueil, commande["id"], "terminee")
    assert payer(client, h_accueil, commande["id"], 70000).status_code == 201
