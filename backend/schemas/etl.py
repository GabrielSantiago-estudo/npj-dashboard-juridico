"""Schemas do processo de importação (ETL)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


StatusLinha = Literal["ok", "tratado", "inconsistente", "duplicado", "vazio"]


class LinhaImportada(BaseModel):
    numero_linha: int
    original: dict[str, str] = Field(default_factory=dict)
    normalizado: dict = Field(default_factory=dict)
    status: StatusLinha
    avisos: list[str] = Field(default_factory=list)


class RelatorioImportacao(BaseModel):
    total_linhas: int = 0
    linhas_vazias: int = 0
    linhas_ok: int = 0
    linhas_tratadas: int = 0
    linhas_inconsistentes: int = 0
    linhas_duplicadas: int = 0
    importados: int = 0
    assistidos_criados: int = 0
    assistidos_reutilizados: int = 0
    precisa_revisao: int = 0


class PreviewImportacao(BaseModel):
    token: str
    arquivo_nome: str
    linhas: list[LinhaImportada]
    relatorio: RelatorioImportacao