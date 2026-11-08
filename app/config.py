from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60

    # Utilisés uniquement par le script d'initialisation : python -m app.seed
    admin_email: str | None = None
    admin_password: str | None = None
    admin_nom_complet: str = "Administrateur"


settings = Settings()
