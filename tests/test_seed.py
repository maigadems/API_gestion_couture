import pytest

from app import seed
from tests.outils import API, MOT_DE_PASSE, entetes_de


def test_seed_cree_l_admin_et_le_catalogue_de_l_annexe_b(client, monkeypatch):
    monkeypatch.setattr(seed.settings, "admin_email", "patron@atelier.sn")
    monkeypatch.setattr(seed.settings, "admin_password", MOT_DE_PASSE)

    assert seed.executer() == (True, 7)

    entetes = entetes_de(client, "patron@atelier.sn")
    assert client.get(f"{API}/auth/me", headers=entetes).json()["role"] == "admin"
    catalogue = {p["nom"]: p for p in client.get(f"{API}/catalogue", headers=entetes).json()}
    assert len(catalogue) == 7
    assert (catalogue["Boubou"]["prix_base"], catalogue["Boubou"]["delai_jours"]) == (35000, 10)
    assert (catalogue["Costume 2 pièces"]["prix_base"], catalogue["Costume 2 pièces"]["delai_jours"]) == (85000, 14)
    assert (catalogue["Retouche"]["prix_base"], catalogue["Retouche"]["delai_jours"]) == (3000, 2)


def test_seed_peut_etre_relance_sans_doublon(client, monkeypatch):
    monkeypatch.setattr(seed.settings, "admin_email", "patron@atelier.sn")
    monkeypatch.setattr(seed.settings, "admin_password", MOT_DE_PASSE)
    seed.executer()
    assert seed.executer() == (False, 0)
    entetes = entetes_de(client, "patron@atelier.sn")
    assert len(client.get(f"{API}/utilisateurs", headers=entetes).json()) == 1


@pytest.mark.parametrize(
    "email, mot_de_passe", [(None, MOT_DE_PASSE), ("patron@atelier.sn", None), ("patron@atelier.sn", "court")]
)
def test_seed_exige_des_variables_admin_valides(monkeypatch, email, mot_de_passe):
    monkeypatch.setattr(seed.settings, "admin_email", email)
    monkeypatch.setattr(seed.settings, "admin_password", mot_de_passe)
    with pytest.raises(SystemExit):
        seed.executer()
