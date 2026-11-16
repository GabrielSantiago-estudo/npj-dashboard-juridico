"""Rotas HTTP de backup e restauração."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.auth.dependencies import exigir_login
from backend.auth.session import flash
from backend.database.session import get_db
from backend.models import Usuario
from backend.services import backup as backup_svc
from backend.services.audit import registrar_operacao
from backend.templating import templates

router = APIRouter(tags=["backups"])


@router.get("/admin/backups", response_class=HTMLResponse)
def listar(
    request: Request,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    backups = backup_svc.listar_backups(db)
    return templates.TemplateResponse(
        request, "admin/backups.html",
        {"usuario": usuario, "backups": backups},
    )


@router.post("/admin/backups/criar")
def criar(
    request: Request,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        b = backup_svc.criar_backup(db, tipo="manual")
        registrar_operacao(
            db, operacao="criar_backup", usuario=usuario,
            entidade="backup", entidade_id=b.id,
            detalhe=f"arquivo={Path(b.caminho).name} tamanho={b.tamanho_bytes}",
            request=request,
        )
        flash(request, "sucesso", "Backup criado com sucesso.")
    except Exception as e:
        registrar_operacao(
            db, operacao="criar_backup", resultado="falha", usuario=usuario,
            detalhe=str(e), request=request,
        )
        flash(request, "erro", f"Erro ao criar backup: {e}")
    return RedirectResponse(url="/admin/backups", status_code=303)


@router.post("/admin/backups/{backup_id}/restaurar")
def restaurar(
    request: Request,
    backup_id: int,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        resultado = backup_svc.restaurar_backup(db, backup_id)
        registrar_operacao(
            db, operacao="restaurar_backup", usuario=usuario,
            entidade="backup", entidade_id=backup_id,
            detalhe=f"pre_restore_id={resultado['pre_restore_id']}",
            request=request,
        )
    except Exception as e:
        registrar_operacao(
            db, operacao="restaurar_backup", resultado="falha", usuario=usuario,
            entidade="backup", entidade_id=backup_id, detalhe=str(e), request=request,
        )
        flash(request, "erro", f"Erro ao restaurar backup: {e}")
    return RedirectResponse(url="/admin/backups", status_code=303)


@router.get("/admin/backups/{backup_id}/download")
def download(
    backup_id: int,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    b = backup_svc.buscar_backup(db, backup_id)
    if b is None or not Path(b.caminho).exists():
        return RedirectResponse(url="/admin/backups", status_code=303)
    return FileResponse(
        b.caminho,
        media_type="application/octet-stream",
        filename=Path(b.caminho).name,
    )