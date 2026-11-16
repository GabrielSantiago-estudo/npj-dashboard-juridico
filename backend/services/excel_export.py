"""Gera o Excel operacional (data/NPJ_Operacional.xlsx) com ListObjects."""
from __future__ import annotations

import logging
import os
from datetime import date as _date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.config import settings
from backend.models import AreaJuridica, Assistido, Atendimento, Equipe

log = logging.getLogger(__name__)


def _add_table(ws, nome_tabela: str, headers: list[str], rows: list[list]) -> None:
    for col_idx, h in enumerate(headers, start=1):
        ws.cell(row=1, column=col_idx, value=h)
    for row_idx, row in enumerate(rows, start=2):
        for col_idx, val in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=val)

    if not rows:
        return

    ref = f"A1:{get_column_letter(len(headers))}{len(rows) + 1}"
    table = Table(displayName=nome_tabela, ref=ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showRowStripes=True, showColumnStripes=False
    )
    ws.add_table(table)


def gerar_excel_operacional(db: Session, caminho: str | Path | None = None) -> Path:
    destino = Path(caminho or settings.resolve_path(settings.excel_operacional_path))
    destino.parent.mkdir(parents=True, exist_ok=True)

    wb = Workbook()

    # ---- Atendimentos ----
    ws = wb.active
    ws.title = "Atendimentos"
    headers = [
        "ID", "Data", "Protocolo", "Assistido", "CPF",
        "Area", "Equipe", "Situacao", "Motivo",
        "Processo", "Vara", "Assunto", "Endereco da Pasta",
        "Parte Contrariada", "Ativo", "Origem",
    ]
    atendimentos = list(
        db.scalars(
            select(Atendimento)
            .options(
                joinedload(Atendimento.assistido),
                joinedload(Atendimento.area_juridica),
                joinedload(Atendimento.equipe),
            )
            .order_by(Atendimento.data_atendimento.desc(), Atendimento.id.desc())
        )
    )
    rows = [
        [
            a.id,
            a.data_atendimento.isoformat() if a.data_atendimento else "",
            a.numero_protocolo or "",
            a.assistido.nome_original if a.assistido else "",
            (a.assistido.cpf if a.assistido else "") or "",
            a.area_juridica.nome if a.area_juridica else "",
            a.equipe.nome if a.equipe else "",
            a.situacao.value if a.situacao else "",
            a.motivo_arquivamento or "",
            a.numero_processo or "",
            a.vara or "",
            a.assunto or "",
            a.endereco_pasta or "",
            a.parte_contrariada or "",
            "Sim" if a.ativo else "Nao",
            a.origem or "",
        ]
        for a in atendimentos
    ]
    _add_table(ws, "Atendimentos", headers, rows)

    # ---- Assistidos ----
    ws = wb.create_sheet("Assistidos")
    headers = ["ID", "Nome", "Nome Normalizado", "CPF", "Total de Atendimentos"]
    assistidos = list(db.scalars(select(Assistido).order_by(Assistido.nome_original)))
    contagem = dict(
        db.execute(
            select(Atendimento.assistido_id, func.count())
            .where(Atendimento.ativo.is_(True))
            .group_by(Atendimento.assistido_id)
        ).all()
    )
    rows = [
        [a.id, a.nome_original, a.nome_normalizado, a.cpf or "", contagem.get(a.id, 0)]
        for a in assistidos
    ]
    _add_table(ws, "Assistidos", headers, rows)

    # ---- Equipes ----
    ws = wb.create_sheet("Equipes")
    equipes = list(db.scalars(select(Equipe).order_by(Equipe.nome)))
    _add_table(ws, "Equipes", ["ID", "Nome"], [[e.id, e.nome] for e in equipes])

    # ---- Areas ----
    ws = wb.create_sheet("Areas")
    areas = list(db.scalars(select(AreaJuridica).order_by(AreaJuridica.nome)))
    _add_table(ws, "Areas", ["ID", "Nome"], [[a.id, a.nome] for a in areas])

    # ---- Resumo ----
    ws = wb.create_sheet("Resumo")
    ativos = sum(1 for a in atendimentos if a.ativo)
    arquivados = len(atendimentos) - ativos
    kpis = [
        ["Indicador", "Valor"],
        ["Total de atendimentos (ativos)", ativos],
        ["Total de atendimentos (arquivados)", arquivados],
        ["Total de atendimentos (todos)", len(atendimentos)],
        ["Total de assistidos", len(assistidos)],
        ["Total de equipes", len(equipes)],
        ["Total de areas juridicas", len(areas)],
        ["Gerado em", _date.today().isoformat()],
    ]
    for row_idx, row in enumerate(kpis, start=1):
        for col_idx, val in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=val)

    # ---- Escrita atômica ----
    tmp = destino.with_suffix(".xlsx.tmp")
    wb.save(tmp)
    try:
        os.replace(tmp, destino)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise

    return destino


def regenerar_apos_commit(db: Session) -> None:
    """Best-effort: falha ao gerar Excel não perde a operação no banco."""
    try:
        gerar_excel_operacional(db)
    except Exception as e:
        log.warning("Falha ao regenerar Excel operacional: %s", e)