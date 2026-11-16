"""Testes da Fase 1 — autenticação e proteção de rotas.

Usa TestClient contra o banco real (seed já criou o admin).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_health_publico(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_admin_valido(client: TestClient) -> None:
    r = client.post(
        "/login",
        data={"username": "admin", "password": "admin123", "next": "/"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"
    # cookie de sessão emitido
    assert any("npj_session" in c for c in r.headers.get_list("set-cookie"))


def test_login_senha_errada(client: TestClient) -> None:
    r = client.post(
        "/login",
        data={"username": "admin", "password": "errada"},
        follow_redirects=False,
    )
    assert r.status_code == 401


def test_login_usuario_inexistente(client: TestClient) -> None:
    r = client.post(
        "/login",
        data={"username": "fantasma", "password": "x"},
        follow_redirects=False,
    )
    assert r.status_code == 401


def test_rota_protegida_sem_login_redireciona(client: TestClient) -> None:
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_dashboard_sem_login_redireciona(client: TestClient) -> None:
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_fluxo_login_dashboard_logout(client: TestClient) -> None:
    # login
    r = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert r.status_code == 303

    # dashboard autenticado: HTML (Fase 2b), com nome completo e botão Sair
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Administrador do NPJ" in r.text
    assert "Painel" in r.text
    assert "Sair" in r.text

    # logout
    r = client.post("/logout", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]

    # após logout, dashboard bloqueia
    r = client.get("/dashboard", follow_redirects=False)
    assert r.status_code == 303


def test_open_redirect_bloqueado(client: TestClient) -> None:
    r = client.post(
        "/login",
        data={"username": "admin", "password": "admin123", "next": "https://evil.example"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert r.headers["location"] == "/"