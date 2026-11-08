from datetime import date, timedelta

import pytest

from tests.outils import (
    API,
    amener_au_statut,
    ligne,
    nouveau_client,
    nouvelle_commande,
    payer,
    poser_statut,
)

URL = f"{API}/commandes"


@pytest.fixture
def commande(client, h_accueil, fatou, boubou):
    """Une commande de 35 000 FCFA."""
    return nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])


def jour(decalage: int = 0) -> str:
    return (date.today() + timedelta(days=decalage)).isoformat()


def planifier(client, entetes, commande_id, **champs):
    corps = {"mode": "retrait_atelier", "date_prevue": jour(5), **champs}
    return client.put(f"{URL}/{commande_id}/livraison", json=corps, headers=entetes)


def confirmer(client, entetes, commande_id, corps=None):
    return client.post(f"{URL}/{commande_id}/livraison/confirmer", json=corps, headers=entetes)


def terminer_et_solder(client, entetes, commande_id, montant=35000):
    amener_au_statut(client, entetes, commande_id, "terminee")
    if montant:
        assert payer(client, entetes, commande_id, montant).status_code == 201


def test_planifier_une_livraison_a_domicile(client, h_accueil, commande):
    reponse = planifier(
        client, h_accueil, commande["id"],
        mode="domicile", adresse="Sacré-Cœur 3, Dakar", livreur="Modou", notes="Appeler avant",
    )
    assert reponse.status_code == 200
    corps = reponse.json()
    assert (corps["mode"], corps["statut"], corps["livreur"]) == ("domicile", "planifiee", "Modou")
    assert corps["adresse"] == "Sacré-Cœur 3, Dakar"
    assert corps["date_effective"] is None


def test_rg18_une_livraison_a_domicile_exige_une_adresse_422(client, h_accueil, commande):
    for adresse in ({}, {"adresse": ""}):
        reponse = planifier(client, h_accueil, commande["id"], mode="domicile", **adresse)
        assert reponse.status_code == 422, adresse
        assert "adresse" in reponse.json()["detail"]
    assert planifier(client, h_accueil, commande["id"], mode="retrait_atelier").status_code == 200


def test_rg18_planifier_met_a_jour_la_date_prevue_de_la_commande(client, h_accueil, commande):
    planifier(client, h_accueil, commande["id"], date_prevue=jour(20))
    relue = client.get(f"{URL}/{commande['id']}", headers=h_accueil).json()
    assert relue["date_livraison_prevue"] == jour(20)
    assert relue["livraison"]["date_prevue"] == jour(20)


def test_rg18_replanifier_modifie_la_livraison_sans_en_creer_une_seconde(client, h_accueil, commande):
    premiere = planifier(client, h_accueil, commande["id"], date_prevue=jour(5)).json()
    seconde = planifier(
        client, h_accueil, commande["id"], mode="domicile", adresse="Pikine", date_prevue=jour(8)
    ).json()
    assert seconde["id"] == premiere["id"]
    assert (seconde["mode"], seconde["date_prevue"]) == ("domicile", jour(8))
    assert len(client.get(f"{API}/livraisons", headers=h_accueil).json()) == 1


def test_rg18_date_prevue_avant_la_commande_422(client, h_accueil, commande):
    assert planifier(client, h_accueil, commande["id"], date_prevue=jour(-1)).status_code == 422


@pytest.mark.parametrize("statut", ["livree", "annulee"])
def test_rg18_commande_livree_ou_annulee_non_planifiable_409(client, h_accueil, commande, statut):
    if statut == "annulee":
        poser_statut(client, h_accueil, commande["id"], "annulee")
    else:
        terminer_et_solder(client, h_accueil, commande["id"])
        assert confirmer(client, h_accueil, commande["id"]).status_code == 200
    assert planifier(client, h_accueil, commande["id"]).status_code == 409


def test_lire_la_livraison_404_tant_qu_aucune_n_est_planifiee(client, h_accueil, commande):
    assert client.get(f"{URL}/{commande['id']}/livraison", headers=h_accueil).status_code == 404
    assert client.get(f"{URL}/9999/livraison", headers=h_accueil).status_code == 404
    planifier(client, h_accueil, commande["id"])
    assert client.get(f"{URL}/{commande['id']}/livraison", headers=h_accueil).status_code == 200


def test_rg19_confirmer_exige_une_commande_terminee_409(client, h_accueil, commande):
    reponse = confirmer(client, h_accueil, commande["id"])
    assert reponse.status_code == 409
    assert "terminee" in reponse.json()["detail"]


def test_rg19_confirmer_refuse_si_le_solde_n_est_pas_paye_avec_le_montant_impaye(client, h_accueil, commande):
    terminer_et_solder(client, h_accueil, commande["id"], montant=15000)
    reponse = confirmer(client, h_accueil, commande["id"])
    assert reponse.status_code == 409
    assert "20000" in reponse.json()["detail"]
    assert client.get(f"{URL}/{commande['id']}", headers=h_accueil).json()["statut"] == "terminee"


def test_rg19_autoriser_solde_impaye_livre_et_inscrit_la_mention_dans_l_historique(client, h_accueil, commande):
    terminer_et_solder(client, h_accueil, commande["id"], montant=15000)
    reponse = confirmer(client, h_accueil, commande["id"], {"autoriser_solde_impaye": True})
    assert reponse.status_code == 200
    relue = client.get(f"{URL}/{commande['id']}", headers=h_accueil).json()
    assert relue["statut"] == "livree"
    assert relue["solde"] == 20000  # la dette reste visible
    historique = client.get(f"{URL}/{commande['id']}/historique", headers=h_accueil).json()
    assert historique[-1]["nouveau_statut"] == "livree"
    assert "impayé" in historique[-1]["commentaire"]
    assert "20000" in historique[-1]["commentaire"]


def test_rg20_la_confirmation_met_a_jour_la_commande_et_la_livraison(client, h_accueil, commande):
    terminer_et_solder(client, h_accueil, commande["id"])
    planifier(client, h_accueil, commande["id"], mode="domicile", adresse="Dakar")
    reponse = confirmer(client, h_accueil, commande["id"])
    assert reponse.status_code == 200
    livraison = reponse.json()
    assert (livraison["statut"], livraison["date_effective"]) == ("livree", jour())
    relue = client.get(f"{URL}/{commande['id']}", headers=h_accueil).json()
    assert (relue["statut"], relue["date_livraison_reelle"], relue["solde"]) == ("livree", jour(), 0)
    assert relue["livraison"]["statut"] == "livree"
    historique = client.get(f"{URL}/{commande['id']}/historique", headers=h_accueil).json()
    assert (historique[-1]["ancien_statut"], historique[-1]["nouveau_statut"]) == ("terminee", "livree")


def test_rg20_sans_planification_un_retrait_atelier_est_cree_automatiquement(client, h_accueil, commande):
    terminer_et_solder(client, h_accueil, commande["id"])
    assert client.get(f"{URL}/{commande['id']}/livraison", headers=h_accueil).status_code == 404
    livraison = confirmer(client, h_accueil, commande["id"]).json()
    assert (livraison["mode"], livraison["statut"]) == ("retrait_atelier", "livree")
    assert client.get(f"{URL}/{commande['id']}/livraison", headers=h_accueil).json()["id"] == livraison["id"]


def test_rg20_date_effective_choisie_et_pas_dans_le_futur(client, h_accueil, commande):
    terminer_et_solder(client, h_accueil, commande["id"])
    assert confirmer(client, h_accueil, commande["id"], {"date_effective": jour(1)}).status_code == 422
    reponse = confirmer(client, h_accueil, commande["id"], {"date_effective": jour(-1)})
    assert reponse.json()["date_effective"] == jour(-1)
    relue = client.get(f"{URL}/{commande['id']}", headers=h_accueil).json()
    assert relue["date_livraison_reelle"] == jour(-1)


def test_on_ne_confirme_pas_deux_fois_la_meme_livraison_409(client, h_accueil, commande):
    terminer_et_solder(client, h_accueil, commande["id"])
    assert confirmer(client, h_accueil, commande["id"]).status_code == 200
    assert confirmer(client, h_accueil, commande["id"]).status_code == 409


def test_livraisons_reservees_a_l_accueil_et_a_l_admin(client, h_tailleur, h_admin, commande):
    assert planifier(client, h_tailleur, commande["id"]).status_code == 403
    assert confirmer(client, h_tailleur, commande["id"]).status_code == 403
    assert planifier(client, h_admin, commande["id"]).status_code == 200


def test_liste_de_tournee_triee_par_date_prevue_avec_les_infos_utiles(client, h_accueil, h_tailleur, fatou, boubou):
    autre = nouveau_client(client, h_accueil, telephone="700000001", prenom="Awa", nom="Ba")
    tardive = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    proche = nouvelle_commande(client, h_accueil, autre["id"], [ligne(boubou)])
    planifier(client, h_accueil, tardive["id"], date_prevue=jour(9))
    planifier(client, h_accueil, proche["id"], date_prevue=jour(2))
    payer(client, h_accueil, proche["id"], 5000)

    tournee = client.get(f"{API}/livraisons", headers=h_tailleur).json()
    assert [l["numero_commande"] for l in tournee] == [proche["numero"], tardive["numero"]]
    premiere = tournee[0]
    assert (premiere["client_nom"], premiere["client_telephone"]) == ("Awa Ba", "700000001")
    assert premiere["solde_commande"] == 30000
    assert {"id", "commande_id", "mode", "date_prevue", "statut"} <= set(premiere)


def test_liste_de_tournee_filtres_statut_et_dates(client, h_accueil, fatou, boubou):
    a_livrer = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    livree = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    planifier(client, h_accueil, a_livrer["id"], date_prevue=jour(3))
    terminer_et_solder(client, h_accueil, livree["id"])
    confirmer(client, h_accueil, livree["id"])

    def ids(**params):
        reponse = client.get(f"{API}/livraisons", params=params, headers=h_accueil)
        assert reponse.status_code == 200
        return [l["commande_id"] for l in reponse.json()]

    assert ids(statut="planifiee") == [a_livrer["id"]]
    assert ids(statut="livree") == [livree["id"]]
    assert ids(date_min=jour(2), date_max=jour(4)) == [a_livrer["id"]]
    assert ids(date_min=jour(11)) == []
    assert client.get(f"{API}/livraisons", params={"statut": "perdue"}, headers=h_accueil).status_code == 422
