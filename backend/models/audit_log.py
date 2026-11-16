"""Registro de auditoria.

Cada operação relevante (login, cadastro, edição, exclusão, importação,
backup etc.) gera uma linha. Não armazena senhas nem dados sensíveis
desnecessários (seção 14).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True, index=True)
    usuario_username: Mapped[str | None] = mapped_column(String(80), nullable=True)

    operacao: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    entidade: Mapped[str | None] = mapped_column(String(60), nullable=True, index=True)
    entidade_id: Mapped[int | None] = mapped_column(nullable=True)

    resultado: Mapped[str] = mapped_column(String(20), nullable=False, default="sucesso")  # sucesso|falha
    detalhe: Mapped[str | None] = mapped_column(Text, nullable=True)

    ip: Mapped[str | None] = mapped_column(String(60), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False, index=True)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.operacao} {self.resultado}>"