"""Engine, SessionLocal e dependency get_db.

SQLite local, acessado exclusivamente pelo backend.
Não é compartilhado em rede (conforme seção 3.2 do documento).
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings


def _make_engine() -> Engine:
    url = settings.database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, future=True)

    # Habilita FOREIGN KEY no SQLite (desligado por padrão)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk_pragma(dbapi_conn, _):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()