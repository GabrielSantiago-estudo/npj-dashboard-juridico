"""Servico de auditoria (secao 14).

Registra operacoes relevantes. Nao armazena senhas nem dados sensiveis.
Timestamps em UTC (func.now()); conversao para local na exibicao.
"""
from __future__ import annotations

from fastapi import Request
from sqlalchemy.orm import Session

from backend.models import AuditLog, Usuario


def registrar_operacao(
    db: Session,
    *,
    operacao: str,
    resultado: str = "sucesso",
    usuario: Usuario | None = None,
    entidade: str | None = None,
    entidade_id: int | None = None,
    detalhe: str | None = None,
    request: Request | None = None,
) -> AuditLog:
    ip = None
    if request is not None:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            ip = fwd.split(",")[0].strip()
        elif request.client:
            ip = request.client.host

    log = AuditLog(
        usuario_id=usuario.id if usuario else None,
        usuario_username=usuario.username if usuario else None,
        operacao=operacao,
        entidade=entidade,
        entidade_id=entidade_id,
        resultado=resultado,
        detalhe=detalhe,
        ip=ip,
    )
    db.add(log)
    db.commit()
    return log