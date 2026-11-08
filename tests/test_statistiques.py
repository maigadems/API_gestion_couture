from datetime import date, timedelta

import pytest

from tests.outils import (
    API,
    amener_au_statut,
    ligne,
    modifier_en_base,
    nouveau_client,
    nouvelle_commande,
    payer,
    poser_statut,
)

URL = f"{API}/statistiques"
STATUTS = ["en_attente", "en_coupe", "en_couture", "essayage", "retouches", "terminee", "livree", "annulee"]
ROUTES = ["/tableau-de-bord", "/chiffre-affaires", "/types-vetement", "/top-clients", "/impayes"]


@pytest.mark.parametrize("chemin", ROUTES)
def test_les_statistiques_sont_reservees_a_l_admin(client, h_admin, h_accueil, h_tailleur, chemin):
    assert client.get(URL + chemin, headers=h_accueil).status_code == 403
    assert client.get(URL + chemin, headers=h_tailleur).status_code == 403
    assert client.get(URL + chemin, headers=h_admin).status_code == 200
    assert client.get(URL + chemin).status_code == 401


def test_tableau_de_bord_vide(client, h_admin):
    corps = client.get(f"{URL}/tableau-de-bord", headers=h_admin).json()
    assert corps["chiffre_affaires_mois"] == 0
    assert corps["encaisse_mois"] == 0
    assert corps["nb_commandes_mois"] == 0
    assert corps["reste_a_encaisser"] == 0
    assert corps["nb_commandes_en_retard"] == 0
    assert corps["commandes_pretes_a_livrer"] == 0
    assert corps["livraisons_du_jour"] == 0
    assert corps["commandes_par_statut"] == {statut: 0 for statut in STATUTS}


def test_tableau_de_bord_chiffres(client, h_admin, h_accueil, fatou, boubou, pantalon):
    c1 = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou, 2)])  # 70 000
    c2 = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(pantalon)], remise=2000)  # 10 000
    c3 = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])  # 35 000, annulée
    payer(client, h_accueil, c1["id"], 20000)
    payer(client, h_accueil, c2["id"], 10000)
    poser_statut(client, h_accueil, c3["id"], "annulee")
    amener_au_statut(client, h_accueil, c2["id"], "terminee")
    modifier_en_base(c1["id"], date_livraison_prevue=date.today() - timedelta(days=2))

    corps = client.get(f"{URL}/tableau-de-bord", headers=h_admin).json()
    assert corps["chiffre_affaires_mois"] == 80000
    assert corps["nb_commandes_mois"] == 2
    assert corps["encaisse_mois"] == 30000
    assert corps["reste_a_encaisser"] == 50000
    assert corps["nb_commandes_en_retard"] == 1
    assert corps["commandes_pretes_a_livrer"] == 1
    par_statut = corps["commandes_par_statut"]
    assert set(par_statut) == set(STATUTS)
    assert (par_statut["en_attente"], par_statut["terminee"], par_statut["annulee"]) == (1, 1, 1)
    assert par_statut["livree"] == 0


def test_le_chiffre_d_affaires_du_mois_augmente_du_montant_de_la_commande(
    client, h_admin, h_accueil, fatou, boubou
):
    avant = client.get(f"{URL}/tableau-de-bord", headers=h_admin).json()["chiffre_affaires_mois"]
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou, 2)], remise=5000)
    apres = client.get(f"{URL}/tableau-de-bord", headers=h_admin).json()["chiffre_affaires_mois"]
    assert apres - avant == 65000


def test_livraisons_du_jour(client, h_admin, h_accueil, fatou, boubou):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    client.put(
        f"{API}/commandes/{commande['id']}/livraison",
        json={"mode": "retrait_atelier", "date_prevue": date.today().isoformat()},
        headers=h_accueil,
    )
    assert client.get(f"{URL}/tableau-de-bord", headers=h_admin).json()["livraisons_du_jour"] == 1


def test_chiffre_d_affaires_par_jour_et_par_mois(client, h_admin, h_accueil, fatou, boubou):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou, 2)])
    payer(client, h_accueil, commande["id"], 20000)
    payer(client, h_accueil, commande["id"], 5000, date_paiement=(date.today() - timedelta(days=1)).isoformat())
    debut = (date.today() - timedelta(days=3)).isoformat()

    par_jour = client.get(f"{URL}/chiffre-affaires", params={"date_debut": debut}, headers=h_admin).json()
    hier = (date.today() - timedelta(days=1)).isoformat()
    assert par_jour == [
        {"periode": hier, "chiffre_affaires": 0, "encaisse": 5000},
        {"periode": date.today().isoformat(), "chiffre_affaires": 70000, "encaisse": 20000},
    ]

    par_mois = client.get(
        f"{URL}/chiffre-affaires", params={"granularite": "mois", "date_debut": debut}, headers=h_admin
    ).json()
    assert len(par_mois) in (1, 2)  # deux mois si la période chevauche un changement de mois
    assert sum(p["chiffre_affaires"] for p in par_mois) == 70000
    assert sum(p["encaisse"] for p in par_mois) == 25000
    assert all(len(p["periode"]) == 7 for p in par_mois)


def test_seules_les_periodes_avec_activite_sont_listees(client, h_admin, h_accueil, fatou, boubou):
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    params = {"date_debut": "2000-01-01", "date_fin": "2000-12-31"}
    assert client.get(f"{URL}/chiffre-affaires", params=params, headers=h_admin).json() == []


def test_les_commandes_annulees_sont_exclues_du_chiffre_d_affaires(client, h_admin, h_accueil, fatou, boubou):
    commande = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    poser_statut(client, h_accueil, commande["id"], "annulee")
    assert client.get(f"{URL}/chiffre-affaires", headers=h_admin).json() == []


def test_date_debut_apres_date_fin_422(client, h_admin):
    params = {"date_debut": "2026-05-10", "date_fin": "2026-05-01"}
    for chemin in ("/chiffre-affaires", "/types-vetement", "/top-clients"):
        reponse = client.get(URL + chemin, params=params, headers=h_admin)
        assert reponse.status_code == 422, chemin
        assert "date_debut" in reponse.json()["detail"]


def test_granularite_inconnue_422(client, h_admin):
    assert client.get(f"{URL}/chiffre-affaires", params={"granularite": "annee"}, headers=h_admin).status_code == 422


def test_types_vetement_quantite_et_chiffre_d_affaires_avant_remise(
    client, h_admin, h_accueil, fatou, boubou, pantalon
):
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou, 2), ligne(pantalon, 1)], remise=10000)
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(pantalon, 3)])
    annulee = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou, 5)])
    poser_statut(client, h_accueil, annulee["id"], "annulee")

    corps = client.get(f"{URL}/types-vetement", headers=h_admin).json()
    assert [(t["nom"], t["quantite"], t["chiffre_affaires"]) for t in corps] == [
        ("Boubou", 2, 70000),
        ("Pantalon", 4, 48000),
    ]


def test_top_clients_trie_par_chiffre_d_affaires_avec_limite(client, h_admin, h_accueil, fatou, boubou, pantalon):
    ba = nouveau_client(client, h_accueil, telephone="700000001", prenom="Awa", nom="Ba")
    sy = nouveau_client(client, h_accueil, telephone="700000002", prenom="Moussa", nom="Sy")
    nouvelle_commande(client, h_accueil, ba["id"], [ligne(pantalon)])  # 12 000
    gros = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou, 2)])  # 70 000
    nouvelle_commande(client, h_accueil, fatou["id"], [ligne(pantalon)])  # 12 000
    nouvelle_commande(client, h_accueil, sy["id"], [ligne(boubou)])  # 35 000
    payer(client, h_accueil, gros["id"], 30000)

    top = client.get(f"{URL}/top-clients", headers=h_admin).json()
    assert [(c["client_nom"], c["nb_commandes"], c["chiffre_affaires"], c["solde_du"]) for c in top] == [
        ("Fatou Diop", 2, 82000, 52000),
        ("Moussa Sy", 1, 35000, 35000),
        ("Awa Ba", 1, 12000, 12000),
    ]
    limite = client.get(f"{URL}/top-clients", params={"limite": 1}, headers=h_admin).json()
    assert [c["client_nom"] for c in limite] == ["Fatou Diop"]
    assert client.get(f"{URL}/top-clients", params={"limite": 0}, headers=h_admin).status_code == 422


def test_impayes_non_annules_et_non_soldes_les_plus_urgents_d_abord(client, h_admin, h_accueil, fatou, boubou, pantalon):
    urgente = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    tardive = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    soldee = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(pantalon)])
    annulee = nouvelle_commande(client, h_accueil, fatou["id"], [ligne(boubou)])
    payer(client, h_accueil, soldee["id"], 12000)
    poser_statut(client, h_accueil, annulee["id"], "annulee")
    modifier_en_base(urgente["id"], date_livraison_prevue=date.today() + timedelta(days=1))
    modifier_en_base(tardive["id"], date_livraison_prevue=date.today() + timedelta(days=30))

    corps = client.get(f"{URL}/impayes", headers=h_admin).json()
    assert set(corps) == {"items", "total", "limit", "offset"}
    assert [c["id"] for c in corps["items"]] == [urgente["id"], tardive["id"]]
    assert corps["total"] == 2
    page = client.get(f"{URL}/impayes", params={"limit": 1, "offset": 1}, headers=h_admin).json()
    assert [c["id"] for c in page["items"]] == [tardive["id"]]
