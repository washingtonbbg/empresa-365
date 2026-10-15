from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Empresa 365"
    database_url: str = "sqlite:///./empresa365.db"
    documents_dir: Path = Path("storage/documents")
    exports_dir: Path = Path("storage/exports")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

