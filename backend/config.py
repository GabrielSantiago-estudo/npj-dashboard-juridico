"""Configuração central do NPJ."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicação
    app_name: str = "NPJ - Núcleo de Prática Jurídica"
    app_env: str = "development"
    app_debug: bool = True

    # Segurança
    secret_key: str = "troque-esta-chave"
    session_max_age_seconds: int = 28800

    # Banco
    database_url: str = "sqlite:///./data/npj.db"

    # Caminhos
    excel_operacional_path: str = "./data/NPJ_Operacional.xlsx"
    excel_historico_ficticio_path: str = "./imports/NPJ_Historico_FICTICIO_2006_2025.xlsx"
    backup_dir: str = "./data/backups"
    log_dir: str = "./logs"

    # Backup automático
    backup_auto_enabled: bool = False
    backup_auto_interval_hours: int = 24

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    def resolve_path(self, relative: str) -> Path:
        p = Path(relative)
        return p if p.is_absolute() else (self.project_root / p).resolve()

    def ensure_dirs(self) -> None:
        for d in (
            self.resolve_path(self.backup_dir),
            self.resolve_path(self.log_dir),
            self.resolve_path("./data"),
            self.resolve_path("./imports"),
            self.resolve_path("./exports"),
        ):
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()