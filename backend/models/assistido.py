"""Assistido (cliente do NPJ).

Preserva o nome original da planilha (nome_original) e mantém um
nome normalizado (nome_normalizado) para busca e detecção de duplicidade.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.atendimento import Atendimento


class Assistido(Base):
    __tablename__ = "assistidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_original: Mapped[str] = mapped_column(String(200), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    cpf: Mapped[str | None] = mapped_column(String(14), nullable=True, index=True)

    atendimentos: Mapped[list["Atendimento"]] = relationship(
        back_populates="assistido", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Assistido {self.nome_original}>"