"""Schemas do módulo de backup."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class BackupRead(BaseModel):
    id: int
    caminho: str
    nome_arquivo: str
    tamanho_bytes: int
    tamanho_kb: float
    tipo: str
    integridade_ok: bool | None
    criado_em: datetime


class RestauracaoResultado(BaseModel):
    backup_restaurado_id: int
    backup_seguranca_id: int
    mensagem: str