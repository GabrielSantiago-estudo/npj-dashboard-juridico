"""Atendimento do NPJ.

Mapeamento das 12 colunas da planilha histórica:
  DATA, NUMERO DE PROTOCOLO, CLIENTE, EQUIPE, SITUACAO,
  MOTIVO DO ARQUIVAMENTO/INDEFERIMENTO, PROCESSO, VARA, AREA,
  ASSUNTO, ENDERECO DAS PASTAS, PARTE CONTRARIADA.

Decisões provisórias (ver docs/MODELO_PROVISORIO.md):
- CLIENTE -> assistido_id (FK) + cliente_texto_original
- EQUIPE  -> equipe_id (FK) + equipe_texto_original
- AREA    -> area_juridica_id (FK) + area_texto_original
- SITUACAO -> enum provisório
- Exclusão é lógica (ativo=False), nunca física.
"""
from __future__ import annotations

import enum
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.area_juridica import AreaJuridica
    from backend.models.assistido import Assistido
    from backend.models.equipe import Equipe


class SituacaoAtendimento(str, enum.Enum):
    """Situação provisória do atendimento.

    Valores inferidos a partir das informações fornecidas pelo NPJ.
    Serão validados/ajustados quando a planilha real estiver disponível.
    """

    ATIVO = "Ativo"
    ARQUIVADO = "Arquivado"
    INDEFERIDO = "Indeferido"
    CONCLUIDO = "Concluído"


class Atendimento(Base):
    __tablename__ = "atendimentos"

    id: Mapped[int] = mapped_column(primary_key=True)

    numero_protocolo: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    data_atendimento: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    assistido_id: Mapped[int] = mapped_column(ForeignKey("assistidos.id"), nullable=False, index=True)
    equipe_id: Mapped[int | None] = mapped_column(ForeignKey("equipes.id"), nullable=True, index=True)
    area_juridica_id: Mapped[int | None] = mapped_column(
        ForeignKey("areas_juridicas.id"), nullable=True, index=True
    )

    cliente_texto_original: Mapped[str] = mapped_column(String(200), nullable=False)
    equipe_texto_original: Mapped[str | None] = mapped_column(String(200), nullable=True)
    area_texto_original: Mapped[str | None] = mapped_column(String(120), nullable=True)

    situacao: Mapped[SituacaoAtendimento] = mapped_column(
        SAEnum(
            SituacaoAtendimento,
            native_enum=False,
            create_constraint=False,   # evita ALTER inválido no SQLite
            length=30,
            validate_strings=True,
        ),
        nullable=False,
        default=SituacaoAtendimento.ATIVO,
    )
    motivo_arquivamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    numero_processo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    vara: Mapped[str | None] = mapped_column(String(120), nullable=True)
    assunto: Mapped[str | None] = mapped_column(Text, nullable=True)
    endereco_pasta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parte_contrariada: Mapped[str | None] = mapped_column(String(200), nullable=True)

    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    origem: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    assistido: Mapped["Assistido"] = relationship(back_populates="atendimentos")
    equipe: Mapped["Equipe | None"] = relationship()
    area_juridica: Mapped["AreaJuridica | None"] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Atendimento {self.numero_protocolo or self.id} {self.data_atendimento}>"