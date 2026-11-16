"""Equipe do NPJ (agrupamento de estagiários).

No protótipo, o campo EQUIPE da planilha histórica é tratado como
texto livre. A tabela permite, no futuro, normalizar as equipes.
"""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class Equipe(Base):
    __tablename__ = "equipes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Equipe {self.nome}>"