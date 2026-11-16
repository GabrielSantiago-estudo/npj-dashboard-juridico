"""Rotas HTTP de importação da planilha histórica."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from backend.auth.dependencies import exigir_login
from backend.auth.session import flash
from backend.config import settings
from backend.database.session import get_db
from backend.models import Usuario
from backend.services import etl_import, excel_export
from backend.services.audit import registrar_operacao
from backend.templating import templates

router = APIRouter(tags=["importacao"])


@router.get("/importacao", response_class=HTMLResponse)
def tela_upload(
    request: Request,
    usuario: Annotated[Usuario, Depends(exigir_login)],
):
    return templates.TemplateResponse(
        request, "importacao/upload.html", {"usuario": usuario}
    )


@router.post("/importacao/upload", response_class=HTMLResponse)
async def receber_arquivo(
    request: Request,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
    arquivo: Annotated[UploadFile, File(...)],
):
    if not arquivo.filename or not arquivo.filename.lower().endswith((".xlsx", ".xls")):
        return templates.TemplateResponse(
            request, "importacao/upload.html",
            {"usuario": usuario, "erro": "Envie um arquivo .xlsx"},
            status_code=400,
        )

    token = uuid.uuid4().hex
    staging = settings.resolve_path("./imports/_staging")
    staging.mkdir(parents=True, exist_ok=True)
    destino = staging / f"{token}.xlsx"
    destino.write_bytes(await arquivo.read())

    try:
        preview = etl_import.processar_planilha(destino, arquivo.filename)
    except Exception as e:
        return templates.TemplateResponse(
            request, "importacao/upload.html",
            {"usuario": usuario, "erro": f"Erro ao processar planilha: {e}"},
            status_code=400,
        )

    preview.token = token
    etl_import.salvar_preview(preview)

    registrar_operacao(
        db, operacao="upload_importacao", usuario=usuario,
        detalhe=f"arquivo={arquivo.filename} linhas={len(preview.linhas)}",
        request=request,
    )

    return RedirectResponse(url=f"/importacao/preview/{token}", status_code=303)


@router.get("/importacao/preview/{token}", response_class=HTMLResponse)
def mostrar_preview(
    request: Request,
    token: str,
    usuario: Annotated[Usuario, Depends(exigir_login)],
):
    preview = etl_import.carregar_preview(token)
    if preview is None:
        return RedirectResponse(url="/importacao", status_code=303)
    return templates.TemplateResponse(
        request, "importacao/preview.html",
        {"usuario": usuario, "preview": preview},
    )


@router.post("/importacao/confirmar/{token}")
def confirmar(
    request: Request,
    token: str,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    preview = etl_import.carregar_preview(token)
    if preview is None:
        return RedirectResponse(url="/importacao", status_code=303)

    try:
        relatorio = etl_import.confirmar_importacao(db, preview)
    except Exception as e:
        return templates.TemplateResponse(
            request, "importacao/preview.html",
            {"usuario": usuario, "preview": preview,
             "erro": f"Erro na importação: {e}"},
            status_code=500,
        )

    etl_import.salvar_relatorio_final(token, relatorio)

    registrar_operacao(
        db, operacao="importar_historico", usuario=usuario,
        detalhe=f"importados={relatorio.importados} revisao={relatorio.precisa_revisao}",
        request=request,
    )

    excel_export.regenerar_apos_commit(db)

    return RedirectResponse(url=f"/importacao/relatorio/{token}", status_code=303)


@router.get("/importacao/relatorio/{token}", response_class=HTMLResponse)
def mostrar_relatorio(
    request: Request,
    token: str,
    usuario: Annotated[Usuario, Depends(exigir_login)],
):
    relatorio = etl_import.carregar_relatorio_final(token)
    if relatorio is None:
        return RedirectResponse(url="/importacao", status_code=303)
    return templates.TemplateResponse(
        request, "importacao/relatorio.html",
        {"usuario": usuario, "relatorio": relatorio, "token": token},
    )


@router.post("/admin/excel/regenerar")
def regenerar_excel(
    request: Request,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        excel_export.gerar_excel_operacional(db)
        registrar_operacao(
            db, operacao="regenerar_excel", usuario=usuario, request=request,
        )
    except Exception:
        pass
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/admin/excel/download")
def download_excel(
    usuario: Annotated[Usuario, Depends(exigir_login)],
):
    caminho = Path(settings.resolve_path(settings.excel_operacional_path))
    if not caminho.exists():
        return RedirectResponse(url="/dashboard", status_code=303)
    return FileResponse(
        caminho,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="NPJ_Operacional.xlsx",
    )