"""Testes da Fase 5 — backup e restauração."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from backend.config import settings
from backend.database.session import SessionLocal
from backend.main import app
from backend.models import Assistido, Atendimento, Backup
from backend.services import backup as backup_svc


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture()
def client():
    c = TestClient(app)
    r = c.post("/login", data={"username": "admin", "password": "admin123"},
               follow_redirects=False)
    assert r.status_code == 303
    return c


@pytest.fixture(autouse=True)
def limpar_backups():
    pasta = settings.resolve_path(settings.backup_dir)
    antes = set(pasta.glob("npj_backup_*.db")) if pasta.exists() else set()
    yield
    if pasta.exists():
        depois = set(pasta.glob("npj_backup_*.db"))
        for arq in depois - antes:
            arq.unlink(missing_ok=True)


def test_criar_backup_gera_arquivo(db):
    b = backup_svc.criar_backup(db, tipo="teste")
    assert Path(b.caminho).exists()
    assert b.tamanho_bytes > 0
    assert b.integridade_ok is True
    db.execute(delete(Backup).where(Backup.id == b.id))
    db.commit()


def test_verificar_integridade_db_valido(db):
    b = backup_svc.criar_backup(db, tipo="teste")
    assert backup_svc.verificar_integridade(b.caminho) is True
    db.execute(delete(Backup).where(Backup.id == b.id))
    db.commit()


def test_verificar_integridade_arquivo_invalido(tmp_path):
    arq = tmp_path / "lixo.db"
    arq.write_bytes(b"isto nao e um sqlite")
    assert backup_svc.verificar_integridade(arq) is False


def test_listar_backups(db):
    antes = len(backup_svc.listar_backups(db))
    b = backup_svc.criar_backup(db, tipo="teste")
    depois = backup_svc.listar_backups(db)
    assert len(depois) == antes + 1
    db.execute(delete(Backup).where(Backup.id == b.id))
    db.commit()


def test_restaurar_backup_cria_pre_restore(db):
    """Após restaurar, o banco volta ao estado anterior. O `pre_restore`
    é criado antes e retornado como dict (primitivo) para evitar
    ObjectDeletedError."""
    from datetime import date

    b = backup_svc.criar_backup(db, tipo="teste")
    b_id = b.id  # primitivo

    # Insere atendimento DEPOIS do backup (deve sumir na restauração)
    ass = Assistido(nome_original="RESTORE_TESTE", nome_normalizado="restore_teste")
    db.add(ass)
    db.flush()
    at = Atendimento(
        numero_protocolo="RESTORE_TESTE_1",
        data_atendimento=date(2024, 6, 1),
        assistido_id=ass.id,
        cliente_texto_original=ass.nome_original,
        area_texto_original="Cível",
        situacao="Ativo",
        origem="manual",
    )
    db.add(at)
    db.commit()

    # Restaura: retorna dict (não ORM)
    resultado = backup_svc.restaurar_backup(db, b_id)

    assert resultado["backup_restaurado_id"] == b_id
    assert resultado["pre_restore_id"] != b_id
    assert resultado["pre_restore_id"] > 0

    # Sessão está expirada; forçamos reload
    db.expire_all()

    # Atendimento de teste NÃO deve existir (banco voltou ao estado pré-teste)
    existe = db.scalar(
        select(Atendimento).where(Atendimento.numero_protocolo == "RESTORE_TESTE_1")
    )
    assert existe is None

    # Limpa registros de backup usando primitivos (não toca ORM antigo)
    db.execute(delete(Backup).where(Backup.id.in_(
        [resultado["backup_restaurado_id"], resultado["pre_restore_id"]]
    )))
    db.commit()


def test_restaurar_backup_inexistente_falha(db):
    with pytest.raises(ValueError):
        backup_svc.restaurar_backup(db, 999999)


def test_tela_backups_requer_login():
    c = TestClient(app)
    r = c.get("/admin/backups", follow_redirects=False)
    assert r.status_code == 303
    assert "/login" in r.headers["location"]


def test_tela_backups_abre(client):
    r = client.get("/admin/backups")
    assert r.status_code == 200
    assert "Backups" in r.text
    assert "Criar backup agora" in r.text


def test_criar_backup_via_http(client, db):
    r = client.post("/admin/backups/criar", follow_redirects=False)
    assert r.status_code == 303
    b = db.scalar(
        select(Backup).where(Backup.tipo == "manual").order_by(Backup.id.desc())
    )
    assert b is not None
    db.execute(delete(Backup).where(Backup.id == b.id))
    db.commit()


def test_download_backup(client, db):
    b = backup_svc.criar_backup(db, tipo="teste")
    b_id = b.id
    r = client.get(f"/admin/backups/{b_id}/download", follow_redirects=False)
    assert r.status_code == 200
    assert len(r.content) > 0
    db.execute(delete(Backup).where(Backup.id == b_id))
    db.commit()