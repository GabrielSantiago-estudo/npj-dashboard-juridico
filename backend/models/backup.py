"""Registro de backups gerados pelo sistema (seção 13)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class Backup(Base):
    __tablename__ = "backups"

    id: Mapped[int] = mapped_column(primary_key=True)
    caminho: Mapped[str] = mapped_column(String(500), nullable=False)
    tamanho_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)  # manual|automatico
    integridade_ok: Mapped[bool | None] = mapped_column(nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Backup {self.caminho}>"