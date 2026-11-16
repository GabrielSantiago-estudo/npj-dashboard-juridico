"""Testes da Fase 2a — serviços de atendimento e assistido."""
from __future__ import annotations

from datetime import date, timedelta
from fastapi.testclient import TestClient

import pytest
from sqlalchemy import delete

from backend.database.session import SessionLocal
from backend.main import app
from backend.models import Atendimento, SituacaoAtendimento
from backend.schemas.atendimento import AtendimentoFiltros, AtendimentoFormulario
from backend.services import assistido as assistido_svc
from backend.services import atendimento as atendimento_svc

PREFIXO = "TEST_ATEND_"


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


def _dados(**over) -> AtendimentoFormulario:
    base = dict(
        numero_protocolo=f"{PREFIXO}0001",
        data_atendimento=date(2024, 3, 15),
        assistido_nome="Joana Teste",
        assistido_cpf=None,
        equipe_nome="Equipe Teste",
        area_nome="Cível",
        situacao=SituacaoAtendimento.ATIVO,
        motivo_arquivamento=None,
        numero_processo=None,
        vara=None,
        assunto="Caso de teste",
        endereco_pasta=None,
        parte_contrariada=None,
    )
    base.update(over)
    return AtendimentoFormulario(**base)


def test_buscar_ou_criar_assistido_cria_uma_vez(db):
    a1 = assistido_svc.buscar_ou_criar(db, "  Maria   Teste  ")
    a2 = assistido_svc.buscar_ou_criar(db, "maria teste")
    a3 = assistido_svc.buscar_ou_criar(db, "MARIA TESTE")
    assert a1.id == a2.id == a3.id
    assert a1.nome_original == "Maria Teste"
    assert a1.nome_normalizado == "maria teste"


def test_buscar_ou_criar_assistido_acento_insensivel(db):
    a1 = assistido_svc.buscar_ou_criar(db, "José Ávila")
    a2 = assistido_svc.buscar_ou_criar(db, "Jose Avila")
    assert a1.id == a2.id


def test_buscar_ou_criar_assistido_cpf_distingue(db):
    a1 = assistido_svc.buscar_ou_criar(db, "João Teste", cpf="11144477735")
    a2 = assistido_svc.buscar_ou_criar(db, "João Teste", cpf=None)
    assert a1.id != a2.id


def test_criar_atendimento_simples(db):
    atendimento, dupes = atendimento_svc.criar(db, _dados())
    db.commit()
    assert atendimento.id is not None
    assert atendimento.cliente_texto_original == "Joana Teste"
    assert atendimento.area_texto_original == "Cível"
    assert atendimento.situacao == SituacaoAtendimento.ATIVO
    assert dupes == []


def test_criar_atendimento_com_motivo_limpo_quando_ativo(db):
    atendimento, _ = atendimento_svc.criar(
        db, _dados(situacao=SituacaoAtendimento.ATIVO, motivo_arquivamento="ignorar")
    )
    db.commit()
    assert atendimento.motivo_arquivamento is None


def test_criar_atendimento_arquivado_exige_motivo():
    with pytest.raises(ValueError):
        _dados(situacao=SituacaoAtendimento.ARQUIVADO, motivo_arquivamento=None)


def test_criar_atendimento_cpf_invalido():
    with pytest.raises(ValueError):
        _dados(assistido_cpf="123.456.789-00")


def test_criar_atendimento_data_futura():
    futuro = date.today() + timedelta(days=1)
    with pytest.raises(ValueError):
        _dados(data_atendimento=futuro)


def test_criar_atendimento_data_antes_2006():
    with pytest.raises(ValueError):
        _dados(data_atendimento=date(2005, 12, 31))


def test_duplicidade_protocolo_igual(db):
    a1, _ = atendimento_svc.criar(db, _dados(numero_protocolo=f"{PREFIXO}DUP"))
    db.commit()
    a2, dupes = atendimento_svc.criar(
        db,
        _dados(
            numero_protocolo=f"{PREFIXO}DUP",
            data_atendimento=date(2024, 5, 20),
            area_nome="Família",
        ),
    )
    db.commit()
    assert len(dupes) == 1
    assert dupes[0].id == a1.id


def test_duplicidade_mesmo_assistido_data_area(db):
    a1, _ = atendimento_svc.criar(db, _dados(numero_protocolo=f"{PREFIXO}D1"))
    db.commit()
    a2, dupes = atendimento_svc.criar(db, _dados(numero_protocolo=f"{PREFIXO}D2"))
    db.commit()
    assert len(dupes) == 1
    assert dupes[0].id == a1.id


def test_sem_duplicidade_quando_muda_area(db):
    a1, _ = atendimento_svc.criar(db, _dados(numero_protocolo=f"{PREFIXO}N1"))
    db.commit()
    _, dupes = atendimento_svc.criar(
        db, _dados(numero_protocolo=f"{PREFIXO}N2", area_nome="Trabalhista")
    )
    db.commit()
    assert dupes == []


def test_atualizar_atendimento(db):
    atendimento, _ = atendimento_svc.criar(db, _dados())
    db.commit()
    atualizado, _ = atendimento_svc.atualizar(
        db,
        atendimento.id,
        _dados(assunto="Assunto atualizado", situacao=SituacaoAtendimento.CONCLUIDO),
    )
    db.commit()
    assert atualizado.assunto == "Assunto atualizado"
    assert atualizado.situacao == SituacaoAtendimento.CONCLUIDO


def test_atualizar_inexistente_falha(db):
    with pytest.raises(atendimento_svc.AtendimentoError):
        atendimento_svc.atualizar(db, 999999, _dados())


def test_arquivar(db):
    atendimento, _ = atendimento_svc.criar(db, _dados())
    db.commit()
    atendimento_svc.arquivar(db, atendimento.id)
    db.commit()
    assert atendimento_svc.buscar_por_id(db, atendimento.id) is None
    arquivado = atendimento_svc.buscar_por_id(
        db, atendimento.id, incluir_arquivados=True
    )
    assert arquivado is not None
    assert arquivado.ativo is False


def test_arquivar_duas_vezes_falha(db):
    atendimento, _ = atendimento_svc.criar(db, _dados())
    db.commit()
    atendimento_svc.arquivar(db, atendimento.id)
    db.commit()
    with pytest.raises(atendimento_svc.AtendimentoError):
        atendimento_svc.arquivar(db, atendimento.id)


def test_listar_com_filtros(db):
    atendimento_svc.criar(
        db, _dados(numero_protocolo=f"{PREFIXO}L1", area_nome="Cível")
    )
    atendimento_svc.criar(
        db,
        _dados(
            numero_protocolo=f"{PREFIXO}L2",
            area_nome="Família",
            data_atendimento=date(2023, 8, 10),
        ),
    )
    db.commit()

    from backend.models import AreaJuridica
    from sqlalchemy import select

    area_civel = db.scalar(select(AreaJuridica).where(AreaJuridica.nome == "Cível"))
    itens, total, _ = atendimento_svc.listar(
        db, AtendimentoFiltros(area_id=area_civel.id)
    )
    assert total >= 1

    itens, total, _ = atendimento_svc.listar(db, AtendimentoFiltros(ano=2024))
    assert total >= 1
    assert all(i.data_atendimento.year == 2024 for i in itens)


def test_listar_exclui_arquivados_por_padrao(db):
    a, _ = atendimento_svc.criar(db, _dados(numero_protocolo=f"{PREFIXO}EX"))
    db.commit()
    atendimento_svc.arquivar(db, a.id)
    db.commit()

    _, total_sem, _ = atendimento_svc.listar(
        db, AtendimentoFiltros(q=f"{PREFIXO}EX")
    )
    assert total_sem == 0

    _, total_com, _ = atendimento_svc.listar(
        db, AtendimentoFiltros(q=f"{PREFIXO}EX", incluir_arquivados=True)
    )
    assert total_com == 1


def test_historico_do_assistido(db):
    a1, _ = atendimento_svc.criar(
        db,
        _dados(numero_protocolo=f"{PREFIXO}H1", data_atendimento=date(2023, 1, 10)),
    )
    db.commit()
    a2, _ = atendimento_svc.criar(
        db,
        _dados(numero_protocolo=f"{PREFIXO}H2", data_atendimento=date(2024, 6, 5)),
    )
    db.commit()

    hist = assistido_svc.historico(db, a1.assistido_id)
    assert len(hist) >= 2
    assert hist[0].data_atendimento >= hist[1].data_atendimento

# ---------- Auto-preenchimento --------------------------------------------

def test_gerar_proximo_protocolo_formato(db):
    """Protocolo deve seguir o formato NPJ-YYYY-NNNN (4 dígitos)."""
    from datetime import date as _d
    ano = _d.today().year
    p = atendimento_svc.gerar_proximo_protocolo(db)
    assert p.startswith(f"NPJ-{ano}-")
    suffix = p.split("-")[-1]
    assert suffix.isdigit()
    assert len(suffix) == 4


def test_gerar_proximo_protocolo_incrementa(db):
    """Após existir um protocolo NNNN no ano, o próximo deve ser NNNN+1."""
    ano = date.today().year
    p1 = atendimento_svc.gerar_proximo_protocolo(db)
    atendimento_svc.criar(
        db,
        _dados(numero_protocolo=p1, data_atendimento=date(ano, 1, 15)),
    )
    db.flush()

    p2 = atendimento_svc.gerar_proximo_protocolo(db)
    assert p1 != p2
    assert int(p2.split("-")[-1]) == int(p1.split("-")[-1]) + 1

    db.rollback()  # descarta o registro criado no teste


def test_gerar_proximo_processo_formato(db):
    """Processo deve seguir o formato CNJ NNNNNNN-01.YYYY.8.26.100."""
    ano = date.today().year
    p = atendimento_svc.gerar_proximo_processo(db)
    assert f".{ano}.8.26." in p
    assert "-" in p
    prefixo = p.split("-")[0]
    assert prefixo.isdigit()
    assert len(prefixo) == 7


def test_form_novo_preenche_campos_automaticamente(client):
    """GET /atendimentos/novo deve retornar form com campos já preenchidos."""
    r = client.get("/atendimentos/novo")
    assert r.status_code == 200

    ano = date.today().year
    assert f"NPJ-{ano}-" in r.text
    assert date.today().isoformat() in r.text
    assert "Ativo" in r.text

@pytest.fixture()
def client():
    """TestClient autenticado como admin.

    Disponibilizado aqui para que testes pontuais que precisem de HTTP
    possam usa-lo sem depender de test_atendimentos_http.py.
    """
    c = TestClient(app)
    r = c.post("/login", data={"username": "admin", "password": "admin123"},
               follow_redirects=False)
    assert r.status_code == 303
    return c