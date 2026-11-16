"""Testes HTTP da Fase 2b — fluxo completo via rotas."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.database.session import SessionLocal
from backend.main import app
from backend.models import Atendimento

PREFIXO = "HTTP_TEST_"


@pytest.fixture()
def client() -> TestClient:
    c = TestClient(app)
    # login
    r = c.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    yield c
    db = SessionLocal()
    db.execute(delete(Atendimento).where(Atendimento.numero_protocolo.like(f"{PREFIXO}%")))
    db.commit()
    db.close()


def _form(**over) -> dict:
    base = {
        "numero_protocolo": f"{PREFIXO}0001",
        "data_atendimento": "2024-03-15",
        "assistido_nome": "Cliente HTTP",
        "assistido_cpf": "",
        "equipe_nome": "Equipe HTTP",
        "area_nome": "Cível",
        "situacao": "Ativo",
        "motivo_arquivamento": "",
        "numero_processo": "",
        "vara": "",
        "assunto": "Teste HTTP",
        "endereco_pasta": "",
        "parte_contrariada": "",
        "confirmar_duplicidade": "",
    }
    base.update(over)
    return base


def test_lista_sem_login_redireciona():
    c = TestClient(app)
    r = c.get("/atendimentos", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_lista_autenticada(client):
    r = client.get("/atendimentos")
    assert r.status_code == 200
    assert "Atendimentos" in r.text


def test_form_novo_abre(client):
    r = client.get("/atendimentos/novo")
    assert r.status_code == 200
    assert "Novo atendimento" in r.text


def test_criar_redireciona_para_detalhe(client):
    r = client.post("/atendimentos/novo", data=_form(), follow_redirects=False)
    assert r.status_code == 303
    assert "/atendimentos/" in r.headers["location"]


def test_criar_com_cpf_invalido_mostra_erro(client):
    r = client.post("/atendimentos/novo", data=_form(assistido_cpf="123.456.789-00"))
    assert r.status_code == 400
    assert "CPF inválido" in r.text or "cpf" in r.text.lower()


def test_criar_com_data_antes_2006_mostra_erro(client):
    r = client.post("/atendimentos/novo", data=_form(data_atendimento="2005-01-01"))
    assert r.status_code == 400


def test_criar_arquivado_sem_motivo_mostra_erro(client):
    r = client.post(
        "/atendimentos/novo",
        data=_form(situacao="Arquivado", motivo_arquivamento=""),
    )
    assert r.status_code == 400


def test_fluxo_criar_editar_arquivar(client):
    # criar
    r = client.post("/atendimentos/novo", data=_form(), follow_redirects=False)
    assert r.status_code == 303
    location = r.headers["location"]
    atendimento_id = int(location.rsplit("/", 1)[1])

    # detalhe
    r = client.get(f"/atendimentos/{atendimento_id}")
    assert r.status_code == 200
    assert "Cliente HTTP" in r.text

    # editar
    r = client.get(f"/atendimentos/{atendimento_id}/editar")
    assert r.status_code == 200

    r = client.post(
        f"/atendimentos/{atendimento_id}/editar",
        data=_form(assunto="Editado via HTTP", situacao="Concluído"),
        follow_redirects=False,
    )
    assert r.status_code == 303

    r = client.get(f"/atendimentos/{atendimento_id}")
    assert "Editado via HTTP" in r.text
    assert "Concluído" in r.text

    # arquivar
    r = client.post(f"/atendimentos/{atendimento_id}/arquivar", follow_redirects=False)
    assert r.status_code == 303
    assert "/atendimentos" in r.headers["location"]


def test_duplicidade_exige_confirmacao(client):
    # primeiro
    r = client.post("/atendimentos/novo", data=_form(), follow_redirects=False)
    assert r.status_code == 303

    # segundo com mesmo protocolo, sem confirmar
    r = client.post(
        "/atendimentos/novo",
        data=_form(numero_protocolo=f"{PREFIXO}0001"),
        follow_redirects=False,
    )
    assert r.status_code == 409
    assert "duplicidade" in r.text.lower()

    # confirmando, passa
    r = client.post(
        "/atendimentos/novo",
        data=_form(
            numero_protocolo=f"{PREFIXO}0001",
            confirmar_duplicidade="1",
        ),
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_historico_assistido(client):
    r = client.post("/atendimentos/novo", data=_form(), follow_redirects=False)
    assert r.status_code == 303
    location = r.headers["location"]
    atendimento_id = int(location.rsplit("/", 1)[1])

    # pega o assistido_id via detalhe (link histórico aparece no HTML)
    r = client.get(f"/atendimentos/{atendimento_id}")
    assert "histórico" in r.text.lower() or "historico" in r.text.lower() or "/historico" in r.text