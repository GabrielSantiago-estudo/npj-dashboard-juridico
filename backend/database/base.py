"""Base declarativa do SQLAlchemy.

Todos os modelos herdam de Base. Isso mantém a camada de dados
isolada e permite migração futura para PostgreSQL sem reescrever modelos.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa."""


class TimestampMixin:
    """Mixin opcional para carimbar criação/atualização."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )