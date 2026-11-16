"""Rotas do dashboard analítico (HTML + API JSON)."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.auth.dependencies import exigir_login
from backend.database.session import get_db
from backend.models import AreaJuridica, Atendimento, Usuario
from backend.schemas.dashboard import DashboardData, FiltrosDashboard
from backend.services import dashboard as dashboard_svc
from backend.templating import templates

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
def tela_dashboard(
    request: Request,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    areas = list(db.scalars(select(AreaJuridica).order_by(AreaJuridica.nome)))

    min_ano = db.scalar(
        select(func.min(func.strftime("%Y", Atendimento.data_atendimento)))
    )
    max_ano = db.scalar(
        select(func.max(func.strftime("%Y", Atendimento.data_atendimento)))
    )
    if min_ano and max_ano:
        anos = list(range(int(min_ano), int(max_ano) + 1))
    else:
        anos = [date.today().year]

    ultimos = list(
        db.scalars(
            select(Atendimento)
            .options(
                joinedload(Atendimento.assistido),
                joinedload(Atendimento.area_juridica),
            )
            .where(Atendimento.ativo.is_(True))
            .order_by(Atendimento.data_atendimento.desc(), Atendimento.id.desc())
            .limit(5)
        )
    )

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "usuario": usuario,
            "areas": areas,
            "anos_disponiveis": list(reversed(anos)),
            "ultimos": ultimos,
        },
    )


@router.get("/api/dashboard/dados", response_model=DashboardData)
def api_dashboard_dados(
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
    ano: Annotated[int | None, Query(ge=1900, le=2100)] = None,
    semestre: Annotated[int | None, Query(ge=1, le=2)] = None,
    area_id: Annotated[int | None, Query(ge=1)] = None,
) -> DashboardData:
    """Retorna todos os indicadores em JSON, respeitando os filtros.

    A validação de `ano`, `semestre` e `area_id` acontece no próprio FastAPI
    (via Query), garantindo HTTP 422 automaticamente para valores inválidos.
    """
    filtros = FiltrosDashboard(ano=ano, semestre=semestre, area_id=area_id)
    return dashboard_svc.calcular_dashboard(db, filtros)