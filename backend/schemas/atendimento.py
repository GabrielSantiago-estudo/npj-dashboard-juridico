"""Schemas Pydantic do Atendimento."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.models.atendimento import SituacaoAtendimento
from backend.schemas.common import limpar_cpf, validar_cpf


class AtendimentoFormulario(BaseModel):
    """Dados de entrada do formulário (criação e edição)."""

    numero_protocolo: Annotated[str | None, Field(None, max_length=60)] = None
    data_atendimento: date
    assistido_nome: Annotated[str, Field(min_length=2, max_length=200)]
    assistido_cpf: Annotated[str | None, Field(None, max_length=20)] = None
    equipe_nome: Annotated[str | None, Field(None, max_length=120)] = None
    area_nome: Annotated[str, Field(min_length=2, max_length=80)]
    situacao: SituacaoAtendimento = SituacaoAtendimento.ATIVO
    motivo_arquivamento: Annotated[str | None, Field(None, max_length=2000)] = None
    numero_processo: Annotated[str | None, Field(None, max_length=60)] = None
    vara: Annotated[str | None, Field(None, max_length=120)] = None
    assunto: Annotated[str | None, Field(None, max_length=2000)] = None
    endereco_pasta: Annotated[str | None, Field(None, max_length=255)] = None
    parte_contrariada: Annotated[str | None, Field(None, max_length=200)] = None

    @field_validator("assistido_nome", "area_nome")
    @classmethod
    def _nao_vazio(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v:
            raise ValueError("Campo obrigatório não pode ser vazio.")
        return v

    @field_validator("assistido_cpf")
    @classmethod
    def _cpf_valido(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        if not validar_cpf(v):
            raise ValueError("CPF inválido.")
        return limpar_cpf(v)

    @field_validator("data_atendimento")
    @classmethod
    def _data_nao_futura(cls, v: date) -> date:
        from datetime import date as _d
        if v > _d.today():
            raise ValueError("Data do atendimento não pode ser futura.")
        if v.year < 2006:
            raise ValueError("Data anterior a 2006 (início do histórico do NPJ).")
        return v

    @model_validator(mode="after")
    def _motivo_coerente(self) -> "AtendimentoFormulario":
        exige_motivo = self.situacao in (
            SituacaoAtendimento.ARQUIVADO,
            SituacaoAtendimento.INDEFERIDO,
        )
        if exige_motivo and not (self.motivo_arquivamento or "").strip():
            raise ValueError(
                "Motivo é obrigatório quando a situação é Arquivado ou Indeferido."
            )
        if not exige_motivo:
            self.motivo_arquivamento = None
        return self


class AtendimentoFiltros(BaseModel):
    """Filtros combináveis da listagem."""

    q: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None
    ano: int | None = None
    semestre: int | None = Field(None, ge=1, le=2)
    area_id: int | None = None
    equipe_id: int | None = None
    situacao: SituacaoAtendimento | None = None
    assistido_id: int | None = None
    incluir_arquivados: bool = False