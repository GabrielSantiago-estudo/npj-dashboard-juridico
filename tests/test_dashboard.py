"""Testes da Fase 4 — dashboard e API de indicadores."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client() -> TestClient:
    c = TestClient(app)
    r = c.post("/login", data={"username": "admin", "password": "admin123"},
               follow_redirects=False)
    assert r.status_code == 303
    return c


def test_api_sem_login_redireciona():
    c = TestClient(app)
    r = c.get("/api/dashboard/dados", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_api_estrutura(client):
    r = client.get("/api/dashboard/dados")
    assert r.status_code == 200
    data = r.json()
    for chave in ("kpis", "por_ano", "por_mes", "por_area", "por_equipe", "por_situacao"):
        assert chave in data
    kpis = data["kpis"]
    assert kpis["total_atendimentos"] >= 0
    assert kpis["total_assistidos"] >= 0
    assert kpis["total_arquivados"] >= 0
    assert kpis["media_por_mes"] >= 0


def test_por_mes_sempre_12_meses(client):
    data = client.get("/api/dashboard/dados").json()
    assert len(data["por_mes"]["labels"]) == 12
    assert data["por_mes"]["labels"][0] == "Jan"
    assert data["por_mes"]["labels"][-1] == "Dez"
    assert len(data["por_mes"]["valores"]) == 12


def test_filtro_ano_reduz_por_ano(client):
    data = client.get("/api/dashboard/dados?ano=2024").json()
    assert len(data["por_ano"]["labels"]) <= 1
    if data["por_ano"]["labels"]:
        assert data["por_ano"]["labels"][0] == "2024"


def test_filtro_semestre_valido(client):
    r = client.get("/api/dashboard/dados?semestre=1")
    assert r.status_code == 200
    r = client.get("/api/dashboard/dados?semestre=2")
    assert r.status_code == 200


def test_filtro_semestre_invalido_retorna_422(client):
    r = client.get("/api/dashboard/dados?semestre=3")
    assert r.status_code == 422


def test_filtros_combinados(client):
    r = client.get("/api/dashboard/dados?ano=2024&semestre=1")
    assert r.status_code == 200
    data = r.json()
    assert "kpis" in data


def test_graficos_situacao_retornam_labels_validos(client):
    data = client.get("/api/dashboard/dados").json()
    situacoes_validas = {"Ativo", "Arquivado", "Indeferido", "Concluído"}
    for label in data["por_situacao"]["labels"]:
        assert label in situacoes_validas


def test_dashboard_html_carrega(client):
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert "Painel analítico" in r.text
    assert "chart-ano" in r.text
    assert "chart-mes" in r.text
    assert "chart-area" in r.text
    assert "chart-equipe" in r.text
    assert "chart-situacao" in r.text