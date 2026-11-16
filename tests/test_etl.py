"""Testes da Fase 3a — ETL e exportação para Excel."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from openpyxl import load_workbook
from sqlalchemy import delete, select

from backend.config import settings
from backend.database.session import SessionLocal
from backend.models import Atendimento
from backend.services import etl_import, excel_export
from backend.services.etl_import import (
    _normalizar_area,
    _normalizar_data,
    _normalizar_nome_cliente,
    _normalizar_situacao,
)

PREFIXO = "ETL_TEST_"


@pytest.fixture()
def db():
    session = SessionLocal()
    session.execute(
        delete(Atendimento).where(Atendimento.numero_protocolo.like(f"{PREFIXO}%"))
    )
    session.commit()
    try:
        yield session
    finally:
        session.execute(
            delete(Atendimento).where(Atendimento.numero_protocolo.like(f"{PREFIXO}%"))
        )
        session.commit()
        session.close()


# ---------- Datas ----------------------------------------------------------

def test_data_tipo_date():
    d, aviso = _normalizar_data(date(2024, 3, 15))
    assert d == date(2024, 3, 15)
    assert aviso is None


def test_data_dd_mm_yyyy_texto():
    d, aviso = _normalizar_data("15/03/2018")
    assert d == date(2018, 3, 15)
    assert aviso is None


def test_data_mm_dd_yyyy_texto_nao_ambiguo():
    d, aviso = _normalizar_data("03/15/2018")
    assert d == date(2018, 3, 15)
    assert aviso is None


def test_data_serial_excel():
    d, aviso = _normalizar_data(43174)  # 2018-03-15
    assert d == date(2018, 3, 15)
    assert aviso is None


def test_data_invalida_31_fevereiro():
    d, aviso = _normalizar_data("31/02/2019")
    assert d is None
    assert aviso is not None


def test_data_antes_2006():
    d, aviso = _normalizar_data(date(2005, 12, 31))
    assert d is None
    assert "2006" in (aviso or "")


# ---------- Áreas ----------------------------------------------------------

def test_area_variantes():
    for entrada, esperado in [
        ("civel", "Cível"), ("CÍVEL", "Cível"), ("CIVEL", "Cível"),
        ("cível", "Cível"), (" Cível ", "Cível"),
        ("familia", "Família"), ("TRABALHISTA", "Trabalhista"),
        ("consumidor", "Consumidor"),
    ]:
        canonica, _ = _normalizar_area(entrada)
        assert canonica == esperado, f"{entrada} -> {canonica}"


def test_area_desconhecida():
    canonica, aviso = _normalizar_area("Tributário")
    assert canonica == "Tributário"
    assert aviso is not None


# ---------- Situações ------------------------------------------------------

def test_situacao_variantes():
    for entrada, esperado in [
        ("ativo", "Ativo"), ("ATIVO", "Ativo"),
        ("arquivado", "Arquivado"), ("ARQUIVADO", "Arquivado"),
        ("indeferido", "Indeferido"), ("concluído", "Concluído"),
    ]:
        canonica, _ = _normalizar_situacao(entrada)
        assert canonica.value == esperado


# ---------- Nomes ----------------------------------------------------------

def test_nome_espacos_e_caixa():
    nome, aviso = _normalizar_nome_cliente("  JOSE   DA SILVA  ")
    assert nome == "Jose Da Silva"
    assert aviso is not None


def test_nome_normal():
    nome, aviso = _normalizar_nome_cliente("Maria Silva")
    assert nome == "Maria Silva"
    assert aviso is None


# ---------- Pipeline -------------------------------------------------------

def test_processar_planilha_ficticia():
    preview = etl_import.processar_planilha(
        settings.resolve_path(settings.excel_historico_ficticio_path),
        "NPJ_Historico_FICTICIO_2006_2025.xlsx",
    )
    assert preview.relatorio.total_linhas == 254
    assert preview.relatorio.linhas_vazias == 4
    assert preview.relatorio.linhas_duplicadas >= 1
    assert preview.relatorio.linhas_inconsistentes >= 1


def test_confirmar_importacao_cria_registros(db):
    preview = etl_import.processar_planilha(
        settings.resolve_path(settings.excel_historico_ficticio_path),
        "NPJ_Historico_FICTICIO_2006_2025.xlsx",
    )

    # Filtra linhas com protocolo e data válidos (para poder limpar depois)
    preview.linhas = [
        ln for ln in preview.linhas
        if ln.status in ("ok", "tratado")
        and ln.normalizado.get("numero_protocolo")
        and ln.normalizado.get("data_atendimento")
    ][:3]

    for ln in preview.linhas:
        ln.normalizado["numero_protocolo"] = f"{PREFIXO}{ln.normalizado['numero_protocolo']}"

    relatorio = etl_import.confirmar_importacao(db, preview)
    assert relatorio.importados == len(preview.linhas)

    importados = list(
        db.scalars(
            select(Atendimento).where(Atendimento.numero_protocolo.like(f"{PREFIXO}%"))
        )
    )
    assert len(importados) == relatorio.importados


# ---------- Excel ----------------------------------------------------------

def test_gerar_excel_operacional_cria_arquivo(db, tmp_path):
    destino = tmp_path / "test_operacional.xlsx"
    caminho = excel_export.gerar_excel_operacional(db, destino)
    assert caminho.exists()
    assert caminho.stat().st_size > 1000


def test_excel_tem_tabelas_estruturadas(db, tmp_path):
    destino = tmp_path / "test_tables.xlsx"
    excel_export.gerar_excel_operacional(db, destino)

    wb = load_workbook(destino)
    assert "Atendimentos" in wb.sheetnames
    assert "Assistidos" in wb.sheetnames
    assert "Equipes" in wb.sheetnames
    assert "Areas" in wb.sheetnames
    assert "Resumo" in wb.sheetnames

    ws = wb["Atendimentos"]
    if ws.max_row > 1:
        assert len(ws.tables) >= 1
        assert "Atendimentos" in list(ws.tables.keys())