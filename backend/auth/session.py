"""Helpers de sessão (login/logout/flash)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import Request

if TYPE_CHECKING:
    from backend.models import Usuario

SESSION_USER_ID = "user_id"
SESSION_USERNAME = "username"
SESSION_FLASH = "flash"


def login_session(request: Request, usuario: "Usuario") -> None:
    request.session[SESSION_USER_ID] = usuario.id
    request.session[SESSION_USERNAME] = usuario.username


def logout_session(request: Request) -> None:
    request.session.clear()


def get_session_user_id(request: Request) -> int | None:
    return request.session.get(SESSION_USER_ID)


def get_session_username(request: Request) -> str | None:
    return request.session.get(SESSION_USERNAME)


def flash(request: Request, tipo: str, mensagem: str) -> None:
    """Adiciona uma mensagem flash à sessão.

    Será exibida na próxima página renderizada e removida em seguida.
    Tipos: ``sucesso``, ``erro``, ``aviso``, ``info``.
    """
    session = request.session
    if SESSION_FLASH not in session:
        session[SESSION_FLASH] = []
    session[SESSION_FLASH].append({"tipo": tipo, "mensagem": mensagem})