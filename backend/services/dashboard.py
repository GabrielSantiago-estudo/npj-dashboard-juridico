"""Serviço de cálculo dos indicadores do dashboard."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import AreaJuridica, Atendimento, Equipe
from backend.schemas.dashboard import (
    DashboardData,
    FiltrosDashboard,
    GraficoDistribuicao,
    GraficoLinha,
    KPIs,
)

MESES_PT = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
            "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


def _aplicar_filtros(stmt, filtros: FiltrosDashboard):
    if filtros.ano:
        stmt = stmt.where(
            func.strftime("%Y", Atendimento.data_atendimento) == str(filtros.ano)
        )
    if filtros.semestre == 1:
        stmt = stmt.where(
            func.strftime("%m", Atendimento.data_atendimento).in_(
                [f"{m:02d}" for m in range(1, 7)]
            )
        )
    elif filtros.semestre == 2:
        stmt = stmt.where(
            func.strftime("%m", Atendimento.data_atendimento).in_(
                [f"{m:02d}" for m in range(7, 13)]
            )
        )
    if filtros.area_id:
        stmt = stmt.where(Atendimento.area_juridica_id == filtros.area_id)
    return stmt


def _situacao_valor(v) -> str:
    return v.value if hasattr(v, "value") else str(v)


def calcular_kpis(db: Session, filtros: FiltrosDashboard) -> KPIs:
    total = db.scalar(_aplicar_filtros(
        select(func.count()).select_from(Atendimento).where(Atendimento.ativo.is_(True)),
        filtros,
    )) or 0

    arquivados = db.scalar(_aplicar_filtros(
        select(func.count()).select_from(Atendimento).where(Atendimento.ativo.is_(False)),
        filtros,
    )) or 0

    assistidos = db.scalar(_aplicar_filtros(
        select(func.count(func.distinct(Atendimento.assistido_id))).select_from(Atendimento),
        filtros,
    )) or 0

    meses_distintos = db.scalar(_aplicar_filtros(
        select(func.count(func.distinct(
            func.strftime("%Y-%m", Atendimento.data_atendimento)
        ))).select_from(Atendimento).where(Atendimento.ativo.is_(True)),
        filtros,
    )) or 1

    return KPIs(
        total_atendimentos=total,
        total_assistidos=assistidos,
        total_arquivados=arquivados,
        media_por_mes=round(total / max(meses_distintos, 1), 1),
    )


def _por_ano(db: Session, filtros: FiltrosDashboard) -> GraficoLinha:
    stmt = _aplicar_filtros(
        select(
            func.strftime("%Y", Atendimento.data_atendimento).label("ano"),
            func.count().label("total"),
        ).select_from(Atendimento).where(Atendimento.ativo.is_(True)),
        filtros,
    ).group_by("ano").order_by("ano")

    rows = list(db.execute(stmt))
    if not rows:
        return GraficoLinha(labels=[], valores=[])

    dados = {int(r.ano): r.total for r in rows}
    ano_min, ano_max = min(dados), max(dados)
    labels = [str(a) for a in range(ano_min, ano_max + 1)]
    valores = [dados.get(a, 0) for a in range(ano_min, ano_max + 1)]
    return GraficoLinha(labels=labels, valores=valores)


def _por_mes(db: Session, filtros: FiltrosDashboard) -> GraficoLinha:
    stmt = _aplicar_filtros(
        select(
            func.strftime("%m", Atendimento.data_atendimento).label("mes"),
            func.count().label("total"),
        ).select_from(Atendimento).where(Atendimento.ativo.is_(True)),
        filtros,
    ).group_by("mes")

    rows = list(db.execute(stmt))
    dados = {int(r.mes): r.total for r in rows}
    valores = [dados.get(m, 0) for m in range(1, 13)]
    return GraficoLinha(labels=MESES_PT, valores=valores)


def _por_area(db: Session, filtros: FiltrosDashboard) -> GraficoDistribuicao:
    stmt = _aplicar_filtros(
        select(
            AreaJuridica.nome.label("area"),
            func.count(Atendimento.id).label("total"),
        )
        .select_from(Atendimento)
        .join(AreaJuridica, Atendimento.area_juridica_id == AreaJuridica.id)
        .where(Atendimento.ativo.is_(True)),
        filtros,
    ).group_by(AreaJuridica.nome).order_by(func.count(Atendimento.id).desc())

    rows = list(db.execute(stmt))
    return GraficoDistribuicao(
        labels=[r.area for r in rows],
        valores=[r.total for r in rows],
    )


def _por_equipe(db: Session, filtros: FiltrosDashboard) -> GraficoDistribuicao:
    stmt = _aplicar_filtros(
        select(
            Equipe.nome.label("equipe"),
            func.count(Atendimento.id).label("total"),
        )
        .select_from(Atendimento)
        .join(Equipe, Atendimento.equipe_id == Equipe.id)
        .where(Atendimento.ativo.is_(True)),
        filtros,
    ).group_by(Equipe.nome).order_by(func.count(Atendimento.id).desc())

    rows = list(db.execute(stmt))
    return GraficoDistribuicao(
        labels=[r.equipe for r in rows],
        valores=[r.total for r in rows],
    )


def _por_situacao(db: Session, filtros: FiltrosDashboard) -> GraficoDistribuicao:
    stmt = _aplicar_filtros(
        select(
            Atendimento.situacao.label("situacao"),
            func.count(Atendimento.id).label("total"),
        ).select_from(Atendimento),
        filtros,
    ).group_by(Atendimento.situacao)

    rows = list(db.execute(stmt))
    return GraficoDistribuicao(
        labels=[_situacao_valor(r.situacao) for r in rows],
        valores=[r.total for r in rows],
    )


def calcular_dashboard(db: Session, filtros: FiltrosDashboard) -> DashboardData:
    return DashboardData(
        kpis=calcular_kpis(db, filtros),
        por_ano=_por_ano(db, filtros),
        por_mes=_por_mes(db, filtros),
        por_area=_por_area(db, filtros),
        por_equipe=_por_equipe(db, filtros),
        por_situacao=_por_situacao(db, filtros),
    )