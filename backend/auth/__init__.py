"""Autenticação do NPJ."""
from backend.auth.dependencies import LoginRequired, exigir_login, usuario_atual
from backend.auth.security import hash_senha, verificar_senha
from backend.auth.session import (
    flash,
    get_session_user_id,
    get_session_username,
    login_session,
    logout_session,
)

__all__ = [
    "LoginRequired",
    "exigir_login",
    "usuario_atual",
    "hash_senha",
    "verificar_senha",
    "login_session",
    "logout_session",
    "get_session_user_id",
    "get_session_username",
    "flash",
]