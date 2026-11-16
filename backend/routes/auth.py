"""Rotas de autenticação: /login (GET/POST) e /logout (POST)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.security import verificar_senha
from backend.auth.session import (
    get_session_user_id,
    login_session,
    logout_session,
)
from backend.database.session import get_db
from backend.models import Usuario
from backend.services.audit import registrar_operacao
from backend.templating import templates

router = APIRouter(tags=["auth"])


def _next_seguro(valor: str | None) -> str:
    """Evita open redirect: só aceita caminhos locais começando com '/'."""
    if not valor:
        return "/"
    if not valor.startswith("/") or valor.startswith("//"):
        return "/"
    return valor


@router.get("/login", response_class=HTMLResponse)
def tela_login(request: Request, next: str = "/"):
    # Se já está logado, manda direto para o destino
    if get_session_user_id(request) is not None:
        return RedirectResponse(url=_next_seguro(next), status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"erro": None, "next": _next_seguro(next)}
    )


@router.post("/login", response_class=HTMLResponse)
def autenticar(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str, Form()] = "/",
):
    destino = _next_seguro(next)
    usuario = db.scalar(select(Usuario).where(Usuario.username == username))

    if usuario is None or not usuario.ativo or not verificar_senha(password, usuario.senha_hash):
        registrar_operacao(
            db,
            operacao="login",
            resultado="falha",
            usuario=usuario,
            detalhe=f"username={username}",
            request=request,
        )
        return templates.TemplateResponse(
            request,
            "login.html",
            {"erro": "Usuário ou senha inválidos.", "next": destino},
            status_code=401,
        )

    login_session(request, usuario)
    usuario.ultimo_login = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()

    registrar_operacao(
        db, operacao="login", resultado="sucesso", usuario=usuario, request=request
    )
    return RedirectResponse(url=destino, status_code=303)


@router.post("/logout")
def sair(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
):
    uid = get_session_user_id(request)
    usuario = db.scalar(select(Usuario).where(Usuario.id == uid)) if uid else None
    logout_session(request)
    if usuario is not None:
        registrar_operacao(
            db, operacao="logout", resultado="sucesso", usuario=usuario, request=request
        )
    return RedirectResponse(url="/login", status_code=303)