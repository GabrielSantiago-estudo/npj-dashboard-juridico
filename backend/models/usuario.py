"""Usuário autorizado do NPJ (perfil único, conforme seção 5)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    nome_completo: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    ultimo_login: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Usuario {self.username}>"