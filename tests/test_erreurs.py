from sqlalchemy.exc import OperationalError

from app.database import get_db
from app.main import app
from tests.outils import API


def test_route_inconnue_404_en_francais(client):
    reponse = client.get("/api/v1/inconnue")
    assert reponse.status_code == 404
    assert reponse.json() == {"detail": "Ressource introuvable"}


def test_methode_non_autorisee_405(client):
    reponse = client.delete("/health")
    assert reponse.status_code == 405
    assert reponse.json() == {"detail": "Méthode non autorisée"}


def test_422_a_toujours_la_forme_detail_texte(client, h_accueil):
    reponse = client.post(f"{API}/clients", json={}, headers=h_accueil)
    assert reponse.status_code == 422
    detail = reponse.json()["detail"]
    assert isinstance(detail, str)
    assert "nom : champ obligatoire" in detail
    assert "telephone : champ obligatoire" in detail


def test_json_invalide_422(client, h_accueil):
    reponse = client.post(
        f"{API}/clients",
        content="{pas du json",
        headers={**h_accueil, "Content-Type": "application/json"},
    )
    assert reponse.status_code == 422
    assert reponse.json()["detail"] == "Le corps de la requête n'est pas un JSON valide"


def test_type_incorrect_422_en_francais(client, h_accueil):
    reponse = client.get(f"{API}/clients/abc", headers=h_accueil)
    assert reponse.status_code == 422
    assert reponse.json()["detail"] == "id : doit être un nombre entier"


def test_health_verifie_la_base(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_health_503_si_la_base_ne_repond_pas(client):
    class SessionCassee:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", {}, Exception("base arrêtée"))

    def get_db_casse():
        yield SessionCassee()

    app.dependency_overrides[get_db] = get_db_casse
    try:
        reponse = client.get("/health")
    finally:
        app.dependency_overrides.clear()
    assert reponse.status_code == 503
    assert reponse.json() == {"detail": "Base de données indisponible"}
