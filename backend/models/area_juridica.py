"""Área jurídica padronizada."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class AreaJuridica(Base):
    __tablename__ = "areas_juridicas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AreaJuridica {self.nome}>"