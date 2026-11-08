from datetime import date, timedelta

from tests.outils import (
    API,
    amener_au_statut,
    ligne,
    modifier_en_base,
    nouveau_client,
    nouvelle_commande,
    poser_statut,
)

URL = f"{API}/commandes"


def test_liste_paginee_la_plus_recente_d_abord(client, h_accueil, fatou, boubou):
    ids = [nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])["id"] for _ in range(3)]
    corps = client.get(URL, headers=h_accueil).json()
    assert set(corps) == {"items", "total", "limit", "offset"}
    assert (corps["total"], corps["limit"], corps["offset"]) == (3, 20, 0)
    assert [c["id"] for c in corps["items"]] == sorted(ids, reverse=True)


def test_chaque_element_contient_client_nom_solde_et_en_retard(client, h_accueil, fatou, boubou):
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    element = client.get(URL, headers=h_accueil).json()["items"][0]
    assert element["client_nom"] == "Fatou Diop"
    assert element["solde"] == 35000
    assert element["en_retard"] is False
    assert {"numero", "statut", "montant_total", "montant_paye", "date_livraison_prevue"} <= set(element)


def test_pagination(client, h_accueil, fatou, boubou):
    for _ in range(5):
        nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    page = client.get(URL, params={"limit": 2, "offset": 4}, headers=h_accueil).json()
    assert (page["total"], len(page["items"])) == (5, 1)
    assert client.get(URL, params={"limit": 101}, headers=h_accueil).status_code == 422


def test_filtre_par_statut_et_par_client(client, h_accueil, fatou, boubou):
    autre = nouveau_client(client, h_accueil, telephone="700000001", nom="Ba")
    en_coupe = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    nouvelle_commande(client, h_accueil, autre["id"], [ligne(boubou)])
    poser_statut(client, h_accueil, en_coupe["id"], "en_coupe")

    par_statut = client.get(URL, params={"statut": "en_coupe"}, headers=h_accueil).json()
    assert [c["id"] for c in par_statut["items"]] == [en_coupe["id"]]
    par_client = client.get(URL, params={"client_id": autre["id"]}, headers=h_accueil).json()
    assert par_client["total"] == 1
    assert par_client["items"][0]["client_nom"] == "Fatou Ba"
    assert client.get(URL, params={"statut": "inconnu"}, headers=h_accueil).status_code == 422


def test_filtre_par_numero(client, h_accueil, fatou, boubou):
    premiere = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    trouves = client.get(URL, params={"numero": premiere["numero"]}, headers=h_accueil).json()
    assert [c["numero"] for c in trouves["items"]] == [premiere["numero"]]
    assert client.get(URL, params={"numero": "CMD-"}, headers=h_accueil).json()["total"] == 2


def test_filtre_par_dates_de_commande(client, h_accueil, fatou, boubou):
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    aujourdhui, demain = date.today(), date.today() + timedelta(days=1)
    hier = aujourdhui - timedelta(days=1)

    def total(**params):
        return client.get(URL, params=params, headers=h_accueil).json()["total"]

    assert total(date_min=aujourdhui.isoformat()) == 1
    assert total(date_min=demain.isoformat()) == 0
    assert total(date_max=hier.isoformat()) == 0
    assert total(date_min=hier.isoformat(), date_max=demain.isoformat()) == 1


def test_rg11_en_retard_date_depassee_et_ni_livree_ni_annulee(client, h_accueil, fatou, boubou):
    hier = date.today() - timedelta(days=1)
    en_retard = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    a_temps = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    annulee = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    livree = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    poser_statut(client, h_accueil, annulee["id"], "annulee")
    for commande in (en_retard, annulee, livree):
        modifier_en_base(commande["id"], date_livraison_prevue=hier)
    modifier_en_base(livree["id"], statut="livree")

    retard = client.get(URL, params={"en_retard": True}, headers=h_accueil).json()
    assert [c["id"] for c in retard["items"]] == [en_retard["id"]]
    assert retard["items"][0]["en_retard"] is True
    pas_en_retard = client.get(URL, params={"en_retard": False}, headers=h_accueil).json()
    assert {c["id"] for c in pas_en_retard["items"]} == {a_temps["id"], annulee["id"], livree["id"]}
    detail = client.get(f"{URL}/{en_retard['id']}", headers=h_accueil).json()
    assert detail["en_retard"] is True
    assert client.get(f"{URL}/{a_temps['id']}", headers=h_accueil).json()["en_retard"] is False


def test_une_commande_due_aujourd_hui_n_est_pas_en_retard(client, h_accueil, fatou, boubou):
    commande = nouvelle_commande(
        client, h_accueil, fatou["id"], [ligne(boubou)], date_livraison_prevue=date.today().isoformat()
    )
    assert commande["en_retard"] is False
    assert client.get(URL, params={"en_retard": True}, headers=h_accueil).json()["total"] == 0


def test_commandes_d_un_client_paginees_la_plus_recente_d_abord(client, h_accueil, fatou, boubou):
    autre = nouveau_client(client, h_accueil, telephone="700000001", nom="Ba")
    ids = [nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])["id"] for _ in range(3)]
    nouvelle_commande(client, h_accueil, autre["id"], [ligne(boubou)])
    corps = client.get(f"{API}/clients/{fatou['id']}/commandes", headers=h_accueil).json()
    assert corps["total"] == 3
    assert [c["id"] for c in corps["items"]] == sorted(ids, reverse=True)
    page = client.get(f"{API}/clients/{fatou['id']}/commandes", params={"limit": 1, "offset": 1}, headers=h_accueil).json()
    assert page["items"][0]["id"] == sorted(ids, reverse=True)[1]
    assert client.get(f"{API}/clients/9999/commandes", headers=h_accueil).status_code == 404


def test_la_liste_inclut_les_commandes_a_tous_les_statuts(client, h_accueil, fatou, boubou):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    amener_au_statut(client, h_accueil, commande["id"], "terminee")
    corps = client.get(URL, params={"statut": "terminee"}, headers=h_accueil).json()
    assert corps["total"] == 1
