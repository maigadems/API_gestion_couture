"""Configuration commune des tests.

Les tests utilisent une base PostgreSQL dédiée (celle du .env, suffixée par « _test »),
créée par les migrations Alembic : on teste donc aussi les migrations.
"""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.config import settings

# Doit précéder l'import de app.database : l'engine y est créé avec cette URL.
URL_DEVELOPPEMENT = make_url(settings.database_url)
NOM_BASE_TEST = URL_DEVELOPPEMENT.database
if not NOM_BASE_TEST.endswith("_test"):
    NOM_BASE_TEST += "_test"
settings.database_url = URL_DEVELOPPEMENT.set(database=NOM_BASE_TEST).render_as_string(
    hide_password=False
)

from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from tests.outils import creer_utilisateur_en_base, entetes_de, nouveau_client, nouvelle_prestation  # noqa: E402

RACINE = Path(__file__).resolve().parents[1]


def _creer_la_base_de_test() -> None:
    serveur = create_engine(
        URL_DEVELOPPEMENT.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with serveur.connect() as connexion:
        existe = connexion.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :nom"), {"nom": NOM_BASE_TEST}
        )
        if not existe:
            connexion.execute(text(f'CREATE DATABASE "{NOM_BASE_TEST}"'))
    serveur.dispose()


@pytest.fixture(scope="session", autouse=True)
def base_de_test():
    # Garde-fou : on vide les tables après chaque test, jamais sur une autre base que celle des tests
    assert engine.url.database.endswith("_test"), "les tests ne doivent viser qu'une base *_test"
    _creer_la_base_de_test()
    config = Config(str(RACINE / "alembic.ini"))
    config.set_main_option("script_location", str(RACINE / "alembic"))
    command.downgrade(config, "base")  # on rejoue toutes les migrations, dans les deux sens
    command.upgrade(config, "head")
    yield
    engine.dispose()


@pytest.fixture(autouse=True)
def base_vide(base_de_test):
    """Chaque test démarre sur une base vide : on la vide après chacun."""
    yield
    tables = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with engine.begin() as connexion:
        connexion.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _entetes(client, role: str) -> dict:
    email = f"{role}@atelier.test"
    creer_utilisateur_en_base(role, email)
    return entetes_de(client, email)


@pytest.fixture
def h_admin(client):
    return _entetes(client, "admin")


@pytest.fixture
def h_accueil(client):
    return _entetes(client, "accueil")


@pytest.fixture
def h_tailleur(client):
    return _entetes(client, "tailleur")


@pytest.fixture
def fatou(client, h_accueil):
    return nouveau_client(client, h_accueil)


@pytest.fixture
def boubou(client, h_admin):
    return nouvelle_prestation(client, h_admin, "Boubou", 35000, 10)


@pytest.fixture
def pantalon(client, h_admin):
    return nouvelle_prestation(client, h_admin, "Pantalon", 12000, 4)
