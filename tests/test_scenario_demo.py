"""Annexe A de l'énoncé : le scénario de démonstration, déroulé de bout en bout."""

import re
from datetime import date, timedelta

from tests.outils import API, MOT_DE_PASSE, entetes_de, modifier_en_base


def test_scenario_de_demonstration(client, h_admin):
    # Les comptes sont créés par l'admin, puis chacun se connecte
    for role in ("accueil", "tailleur"):
        client.post(
            f"{API}/utilisateurs",
            json={"email": f"{role}@atelier.sn", "nom_complet": f"Compte {role}",
                  "mot_de_passe": MOT_DE_PASSE, "role": role},
            headers=h_admin,
        )
    accueil = entetes_de(client, "accueil@atelier.sn")
    tailleur = entetes_de(client, "tailleur@atelier.sn")

    # Catalogue de départ (annexe B)
    def prestation(nom, prix, delai):
        return client.post(
            f"{API}/catalogue", json={"nom": nom, "prix_base": prix, "delai_jours": delai}, headers=h_admin
        ).json()

    boubou = prestation("Boubou", 35000, 10)
    pantalon = prestation("Pantalon", 12000, 4)

    # 1. Accueil : crée Fatou Diop ; le même numéro écrit autrement est refusé (409)
    fatou = client.post(
        f"{API}/clients", json={"nom": "Diop", "prenom": "Fatou", "telephone": "77 123 45 67"}, headers=accueil
    )
    assert fatou.status_code == 201
    fatou = fatou.json()
    doublon = client.post(
        f"{API}/clients", json={"nom": "Autre", "prenom": "Personne", "telephone": "771234567"}, headers=accueil
    )
    assert doublon.status_code == 409

    # 2. Tailleur : prend les mesures ; l'accueil reçoit 403
    mesures = {"tour_poitrine": 98, "tour_taille": 80, "longueur_manche": 60}
    interdit = client.post(f"{API}/clients/{fatou['id']}/mesures", json=mesures, headers=accueil)
    assert interdit.status_code == 403
    prise = client.post(f"{API}/clients/{fatou['id']}/mesures", json=mesures, headers=tailleur)
    assert prise.status_code == 201

    # 3. Accueil : 2 boubous + 1 pantalon à prix négocié, avec une remise
    reponse = client.post(
        f"{API}/commandes",
        json={
            "client_id": fatou["id"],
            "lignes": [
                {"type_vetement_id": boubou["id"], "quantite": 2},
                {"type_vetement_id": pantalon["id"], "quantite": 1, "prix_unitaire": 10000},
            ],
            "remise": 5000,
        },
        headers=accueil,
    )
    assert reponse.status_code == 201
    commande = reponse.json()
    assert re.fullmatch(rf"CMD-{date.today().year}-\d{{5}}", commande["numero"])
    assert commande["montant_total"] == 2 * 35000 + 10000 - 5000
    assert commande["date_livraison_prevue"] == (date.today() + timedelta(days=10)).isoformat()
    assert commande["mesure_id"] == prise.json()["id"]
    cid = commande["id"]

    # 4. Accueil : tente « terminee » → 409 avec les statuts possibles
    refus = client.post(f"{API}/commandes/{cid}/statut", json={"statut": "terminee"}, headers=accueil)
    assert refus.status_code == 409
    assert "Statuts possibles : annulee, en_coupe" in refus.json()["detail"]

    # 5. Tailleur : fait avancer jusqu'à « terminee », avec un aller-retour essayage / retouches
    for statut in ("en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee"):
        etape = client.post(f"{API}/commandes/{cid}/statut", json={"statut": statut}, headers=tailleur)
        assert etape.status_code == 200, (statut, etape.text)
    historique = client.get(f"{API}/commandes/{cid}/historique", headers=accueil).json()
    assert [h["nouveau_statut"] for h in historique] == [
        "en_attente", "en_coupe", "en_couture", "essayage", "retouches", "essayage", "terminee",
    ]

    # 6. Accueil : acompte Wave ; un paiement supérieur au solde est refusé (409)
    acompte = client.post(
        f"{API}/commandes/{cid}/paiements", json={"montant": 30000, "mode": "wave"}, headers=accueil
    )
    assert acompte.status_code == 201
    trop = client.post(
        f"{API}/commandes/{cid}/paiements", json={"montant": 50000, "mode": "especes"}, headers=accueil
    )
    assert trop.status_code == 409

    # 7. Accueil : confirmer la livraison est refusé, le solde n'est pas payé
    impaye = client.post(f"{API}/commandes/{cid}/livraison/confirmer", headers=accueil)
    assert impaye.status_code == 409
    assert "45000" in impaye.json()["detail"]

    # 8. Accueil : encaisse le solde, puis confirme la livraison
    solde = client.post(
        f"{API}/commandes/{cid}/paiements", json={"montant": 45000, "mode": "orange_money"}, headers=accueil
    )
    assert solde.status_code == 201
    livraison = client.post(f"{API}/commandes/{cid}/livraison/confirmer", headers=accueil)
    assert livraison.status_code == 200
    finale = client.get(f"{API}/commandes/{cid}", headers=accueil).json()
    assert finale["statut"] == "livree"
    assert finale["solde"] == 0

    # 9. Admin : le chiffre d'affaires du mois reflète la commande ; l'accueil reçoit 403
    tableau = client.get(f"{API}/statistiques/tableau-de-bord", headers=h_admin).json()
    assert tableau["chiffre_affaires_mois"] == 75000
    assert tableau["encaisse_mois"] == 75000
    assert client.get(f"{API}/statistiques/tableau-de-bord", headers=accueil).status_code == 403

    # 10. Admin : impayés et commandes en retard
    en_retard = client.post(
        f"{API}/commandes",
        json={"client_id": fatou["id"], "lignes": [{"type_vetement_id": boubou["id"]}]},
        headers=accueil,
    ).json()
    modifier_en_base(en_retard["id"], date_livraison_prevue=date.today() - timedelta(days=3))
    impayes = client.get(f"{API}/statistiques/impayes", headers=h_admin).json()
    assert [c["id"] for c in impayes["items"]] == [en_retard["id"]]
    retards = client.get(f"{API}/commandes", params={"en_retard": True}, headers=h_admin).json()
    assert [c["id"] for c in retards["items"]] == [en_retard["id"]]
    assert client.get(f"{API}/statistiques/tableau-de-bord", headers=h_admin).json()["nb_commandes_en_retard"] == 1
