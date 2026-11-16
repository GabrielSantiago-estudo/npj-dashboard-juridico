"""Schemas do dashboard analítico."""
from __future__ import annotations

from pydantic import BaseModel, Field


class FiltrosDashboard(BaseModel):
    """Filtros aplicáveis ao dashboard."""
    ano: int | None = None
    semestre: int | None = Field(None, ge=1, le=2)
    area_id: int | None = None


class KPIs(BaseModel):
    """Indicadores dos cartões."""
    total_atendimentos: int = 0
    total_assistidos: int = 0
    total_arquivados: int = 0
    media_por_mes: float = 0.0


class GraficoLinha(BaseModel):
    labels: list[str]
    valores: list[int]


class GraficoDistribuicao(BaseModel):
    labels: list[str]
    valores: list[int]


class DashboardData(BaseModel):
    kpis: KPIs
    por_ano: GraficoLinha
    por_mes: GraficoLinha
    por_area: GraficoDistribuicao
    por_equipe: GraficoDistribuicao
    por_situacao: GraficoDistribuicao