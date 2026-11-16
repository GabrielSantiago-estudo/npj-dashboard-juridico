"""Dependências de autenticação para rotas FastAPI.

- `usuario_atual`: retorna o Usuario logado ou None.
- `exigir_login`:  levanta LoginRequired (handler global redireciona para /login).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.session import get_session_user_id
from backend.database.session import get_db
from backend.models import Usuario


class LoginRequired(Exception):
    """Levantada por rotas protegidas quando não há usuário autenticado."""

    def __init__(self, next_url: str | None = None) -> None:
        self.next_url = next_url


def usuario_atual(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> Usuario | None:
    uid = get_session_user_id(request)
    if uid is None:
        return None
    return db.scalar(select(Usuario).where(Usuario.id == uid, Usuario.ativo.is_(True)))


def exigir_login(
    request: Request,
    usuario: Annotated[Usuario | None, Depends(usuario_atual)],
) -> Usuario:
    if usuario is None:
        raise LoginRequired(next_url=request.url.path)
    return usuario