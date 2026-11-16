"""Serviço de backup e restauração do banco SQLite."""
from __future__ import annotations

import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Backup

log = logging.getLogger(__name__)

_AUTO_THREAD: threading.Thread | None = None
_AUTO_STOP = threading.Event()


def _db_path() -> Path:
    url = settings.database_url
    if url.startswith("sqlite:///"):
        rel = url[len("sqlite:///"):]
        return settings.resolve_path(rel)
    raise ValueError(f"Backup só é suportado para SQLite. DATABASE_URL: {url}")


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _pasta_backup() -> Path:
    pasta = settings.resolve_path(settings.backup_dir)
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def verificar_integridade(caminho: Path | str) -> bool:
    try:
        conn = sqlite3.connect(str(caminho))
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            return bool(result) and result[0] == "ok"
        finally:
            conn.close()
    except Exception as e:
        log.warning("Falha ao verificar integridade de %s: %s", caminho, e)
        return False


def criar_backup(db: Session, tipo: str = "manual") -> Backup:
    db_path = _db_path()
    if not db_path.exists():
        raise FileNotFoundError(f"Banco não encontrado: {db_path}")

    destino = _pasta_backup() / f"npj_backup_{_timestamp()}_{tipo}.db"

    src = sqlite3.connect(str(db_path))
    try:
        dst = sqlite3.connect(str(destino))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    tamanho = destino.stat().st_size
    integridade_ok = verificar_integridade(destino)

    backup = Backup(
        caminho=str(destino),
        tamanho_bytes=tamanho,
        tipo=tipo,
        integridade_ok=integridade_ok,
    )
    db.add(backup)
    db.commit()
    db.refresh(backup)
    return backup


def listar_backups(db: Session) -> list[Backup]:
    return list(db.scalars(
        select(Backup).order_by(Backup.criado_em.desc(), Backup.id.desc())
    ))


def buscar_backup(db: Session, backup_id: int) -> Backup | None:
    return db.get(Backup, backup_id)


def restaurar_backup(db: Session, backup_id: int) -> dict:
    """Restaura o backup `backup_id`.

    IMPORTANTE: após a restauração, o arquivo `npj.db` é SOBRESCRITO
    com o conteúdo do backup. Registros criados DEPOIS do backup
    (incluindo o próprio `pre_restore`) deixam de existir no banco.

    Por isso, retornamos um **dict com dados primitivos** (não objetos ORM),
    para que o caller possa usar os IDs sem sofrer `ObjectDeletedError`.
    """
    backup = db.get(Backup, backup_id)
    if backup is None:
        raise ValueError("Backup não encontrado.")

    origem = Path(backup.caminho)
    if not origem.exists():
        raise FileNotFoundError(f"Arquivo de backup não existe: {origem}")

    if not verificar_integridade(origem):
        raise ValueError("Backup corrompido (falha na verificação).")

    # 1) Snapshot do estado atual (proteção)
    pre = criar_backup(db, tipo="pre_restore")
    pre_id = pre.id  # primitivo ANTES de sobrescrever o banco
    pre_caminho = pre.caminho
    pre_tamanho = pre.tamanho_bytes

    # 2) Restaura: sobrescreve npj.db com o conteúdo do backup escolhido
    db_path = _db_path()
    src = sqlite3.connect(str(origem))
    try:
        dst = sqlite3.connect(str(db_path))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    # 3) Sessão está inconsistente após a troca do banco.
    #    Expiramos tudo para forçar recarregamento nas próximas consultas.
    db.expire_all()

    log.info("Backup %s restaurado. Pre-restore: %s", backup_id, pre_id)

    return {
        "backup_restaurado_id": backup_id,
        "pre_restore_id": pre_id,
        "pre_restore_caminho": pre_caminho,
        "pre_restore_tamanho_bytes": pre_tamanho,
    }


def _loop_backup(intervalo_horas: int) -> None:
    log.info("Thread de backup automático iniciada (intervalo=%dh)", intervalo_horas)
    while not _AUTO_STOP.wait(intervalo_horas * 3600):
        try:
            from backend.database.session import SessionLocal
            db = SessionLocal()
            try:
                b = criar_backup(db, tipo="automatico")
                log.info("Backup automático criado: %s", b.caminho)
            finally:
                db.close()
        except Exception as e:
            log.warning("Falha no backup automático: %s", e)
    log.info("Thread de backup automático encerrada.")


def iniciar_backup_automatico() -> None:
    global _AUTO_THREAD
    if not settings.backup_auto_enabled:
        return
    if _AUTO_THREAD is not None and _AUTO_THREAD.is_alive():
        return
    _AUTO_STOP.clear()
    _AUTO_THREAD = threading.Thread(
        target=_loop_backup,
        args=(settings.backup_auto_interval_hours,),
        daemon=True,
        name="npj-backup-auto",
    )
    _AUTO_THREAD.start()


def parar_backup_automatico() -> None:
    _AUTO_STOP.set()