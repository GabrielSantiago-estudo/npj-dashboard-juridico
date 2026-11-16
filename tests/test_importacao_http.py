"""Testes HTTP da Fase 3b — fluxo completo de importação."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.config import settings
from backend.database.session import SessionLocal
from backend.main import app
from backend.models import Atendimento


@pytest.fixture()
def client():
    c = TestClient(app)
    r = c.post("/login", data={"username": "admin", "password": "admin123"}, follow_redirects=False)
    assert r.status_code == 303
    yield c


def test_upload_sem_arquivo_retorna_erro(client):
    r = client.post("/importacao/upload")
    assert r.status_code in (400, 422)


def test_upload_tipo_invalido(client):
    r = client.post(
        "/importacao/upload",
        files={"arquivo": ("teste.csv", b"a,b,c", "text/csv")},
    )
    assert r.status_code == 400


def test_upload_xlsx_processa_e_redireciona(client):
    planilha = settings.resolve_path(settings.excel_historico_ficticio_path)
    assert planilha.exists(), f"Planilha fictícia não encontrada: {planilha}"

    with open(planilha, "rb") as f:
        r = client.post(
            "/importacao/upload",
            files={
                "arquivo": (
                    "NPJ_Historico_FICTICIO_2006_2025.xlsx",
                    f.read(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            follow_redirects=False,
        )
    assert r.status_code == 303
    assert "/importacao/preview/" in r.headers["location"]


def test_fluxo_completo_importacao(client):
    planilha = settings.resolve_path(settings.excel_historico_ficticio_path)

    with open(planilha, "rb") as f:
        r = client.post(
            "/importacao/upload",
            files={
                "arquivo": (
                    "hist.xlsx",
                    f.read(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
            follow_redirects=False,
        )

    assert r.status_code == 303
    token = r.headers["location"].rsplit("/", 1)[1]

    r = client.get(f"/importacao/preview/{token}")
    assert r.status_code == 200
    assert "Pré-visualização" in r.text

    r = client.post(f"/importacao/confirmar/{token}", follow_redirects=False)
    assert r.status_code == 303
    assert "/importacao/relatorio/" in r.headers["location"]

    r = client.get(f"/importacao/relatorio/{token}")
    assert r.status_code == 200
    assert "Importação concluída" in r.text


def test_excel_operacional_existe_apos_importacao(client):
    planilha = settings.resolve_path(settings.excel_historico_ficticio_path)
    with open(planilha, "rb") as f:
        r = client.post(
            "/importacao/upload",
            files={"arquivo": ("hist.xlsx", f.read(),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            follow_redirects=False,
        )
    token = r.headers["location"].rsplit("/", 1)[1]
    client.post(f"/importacao/confirmar/{token}", follow_redirects=False)

    excel_path = settings.resolve_path(settings.excel_operacional_path)
    assert excel_path.exists()
    assert excel_path.stat().st_size > 1000


def test_download_excel_apos_geracao(client):
    planilha = settings.resolve_path(settings.excel_historico_ficticio_path)
    with open(planilha, "rb") as f:
        r = client.post(
            "/importacao/upload",
            files={"arquivo": ("hist.xlsx", f.read(),
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            follow_redirects=False,
        )
    token = r.headers["location"].rsplit("/", 1)[1]
    client.post(f"/importacao/confirmar/{token}", follow_redirects=False)

    r = client.get("/admin/excel/download", follow_redirects=False)
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers["content-type"]
    assert len(r.content) > 1000