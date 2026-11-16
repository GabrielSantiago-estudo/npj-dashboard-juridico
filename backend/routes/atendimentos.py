"""Rotas HTTP de atendimentos e histórico de assistido."""
from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth.dependencies import exigir_login
from backend.auth.session import flash
from backend.database.session import get_db
from backend.models import AreaJuridica, Assistido, SituacaoAtendimento, Usuario
from backend.schemas.atendimento import AtendimentoFiltros, AtendimentoFormulario
from backend.services import assistido as assistido_svc
from backend.services import atendimento as atendimento_svc
from backend.services import excel_export
from backend.services.audit import registrar_operacao
from backend.templating import templates

router = APIRouter(tags=["atendimentos"])


def _parse_date(v: str | None) -> date | None:
    if not v:
        return None
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_int(v: str | None) -> int | None:
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _parse_situacao(v: str | None) -> SituacaoAtendimento | None:
    if not v:
        return None
    for s in SituacaoAtendimento:
        if s.value == v:
            return s
    return None


def _filtros_da_query(
    q: str = "",
    data_inicio: str = "",
    data_fim: str = "",
    ano: str = "",
    semestre: str = "",
    area_id: str = "",
    situacao: str = "",
    incluir_arquivados: str = "",
) -> AtendimentoFiltros:
    return AtendimentoFiltros(
        q=q.strip() or None,
        data_inicio=_parse_date(data_inicio),
        data_fim=_parse_date(data_fim),
        ano=_parse_int(ano),
        semestre=_parse_int(semestre) if _parse_int(semestre) in (1, 2) else None,
        area_id=_parse_int(area_id),
        situacao=_parse_situacao(situacao),
        incluir_arquivados=bool(incluir_arquivados),
    )


def _contexto_lista(db: Session) -> dict:
    areas = list(db.scalars(select(AreaJuridica).order_by(AreaJuridica.nome)))
    return {"areas": areas, "situacoes": list(SituacaoAtendimento)}


@router.get("/atendimentos", response_class=HTMLResponse)
def listar(
    request: Request,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
    q: str = "",
    data_inicio: str = "",
    data_fim: str = "",
    ano: str = "",
    semestre: str = "",
    area_id: str = "",
    situacao: str = "",
    incluir_arquivados: str = "",
    page: int = 1,
):
    filtros = _filtros_da_query(
        q, data_inicio, data_fim, ano, semestre, area_id, situacao, incluir_arquivados
    )
    itens, total, total_paginas = atendimento_svc.listar(db, filtros, page=page)

    ctx = _contexto_lista(db)
    ctx.update({
        "usuario": usuario,
        "itens": itens,
        "total": total,
        "page": page,
        "total_paginas": total_paginas,
        "filtros": {
            "q": q, "data_inicio": data_inicio, "data_fim": data_fim,
            "ano": ano, "semestre": semestre, "area_id": area_id,
            "situacao": situacao, "incluir_arquivados": incluir_arquivados,
        },
    })
    return templates.TemplateResponse(request, "atendimentos/lista.html", ctx)


def _coletar_form(
    numero_protocolo: str, data_atendimento: str, assistido_nome: str,
    assistido_cpf: str, equipe_nome: str, area_nome: str, situacao: str,
    motivo_arquivamento: str, numero_processo: str, vara: str, assunto: str,
    endereco_pasta: str, parte_contrariada: str,
) -> dict:
    return {
        "numero_protocolo": numero_protocolo or None,
        "data_atendimento": data_atendimento or None,
        "assistido_nome": assistido_nome,
        "assistido_cpf": assistido_cpf or None,
        "equipe_nome": equipe_nome or None,
        "area_nome": area_nome,
        "situacao": _parse_situacao(situacao) or SituacaoAtendimento.ATIVO,
        "motivo_arquivamento": motivo_arquivamento or None,
        "numero_processo": numero_processo or None,
        "vara": vara or None,
        "assunto": assunto or None,
        "endereco_pasta": endereco_pasta or None,
        "parte_contrariada": parte_contrariada or None,
    }


def _campos_vazios() -> dict:
    return {
        "numero_protocolo": "", "data_atendimento": "", "assistido_nome": "",
        "assistido_cpf": "", "equipe_nome": "", "area_nome": "",
        "situacao": SituacaoAtendimento.ATIVO.value, "motivo_arquivamento": "",
        "numero_processo": "", "vara": "", "assunto": "",
        "endereco_pasta": "", "parte_contrariada": "",
    }


def _campos_auto_preenchidos(db: Session) -> dict:
    """Retorna o dict de campos com auto-preenchimento aplicado.

    - ``numero_protocolo``: próximo sequencial do ano atual (``NPJ-YYYY-NNNN``)
    - ``numero_processo``: próximo CNJ (``NNNNNNN-01.YYYY.8.26.100``)
    - ``data_atendimento``: data atual
    - ``situacao``: sempre ``Ativo``
    """
    campos = _campos_vazios()
    campos["numero_protocolo"] = atendimento_svc.gerar_proximo_protocolo(db)
    campos["numero_processo"] = atendimento_svc.gerar_proximo_processo(db)
    campos["data_atendimento"] = date.today().isoformat()
    campos["situacao"] = SituacaoAtendimento.ATIVO.value
    return campos


@router.get("/atendimentos/novo", response_class=HTMLResponse)
def form_novo(
    request: Request,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    return templates.TemplateResponse(
        request, "atendimentos/form.html",
        {
            "usuario": usuario, "modo": "novo", "atendimento_id": None,
            "campos": _campos_auto_preenchidos(db),
            "erros": [], "duplicidades": [],
            "situacoes": list(SituacaoAtendimento),
        },
    )


@router.post("/atendimentos/novo", response_class=HTMLResponse)
def criar(
    request: Request,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
    numero_protocolo: Annotated[str, Form()] = "",
    data_atendimento: Annotated[str, Form()] = "",
    assistido_nome: Annotated[str, Form()] = "",
    assistido_cpf: Annotated[str, Form()] = "",
    equipe_nome: Annotated[str, Form()] = "",
    area_nome: Annotated[str, Form()] = "",
    situacao: Annotated[str, Form()] = "",
    motivo_arquivamento: Annotated[str, Form()] = "",
    numero_processo: Annotated[str, Form()] = "",
    vara: Annotated[str, Form()] = "",
    assunto: Annotated[str, Form()] = "",
    endereco_pasta: Annotated[str, Form()] = "",
    parte_contrariada: Annotated[str, Form()] = "",
    confirmar_duplicidade: Annotated[str, Form()] = "",
):
    campos = _coletar_form(
        numero_protocolo, data_atendimento, assistido_nome, assistido_cpf,
        equipe_nome, area_nome, situacao, motivo_arquivamento, numero_processo,
        vara, assunto, endereco_pasta, parte_contrariada,
    )
    try:
        dados = AtendimentoFormulario(**campos)
    except Exception as e:
        erros = []
        if hasattr(e, "errors"):
            for err in e.errors():
                campo = ".".join(str(x) for x in err["loc"])
                erros.append(f"{campo}: {err['msg']}")
        else:
            erros.append(str(e))
        return templates.TemplateResponse(
            request, "atendimentos/form.html",
            {"usuario": usuario, "modo": "novo", "atendimento_id": None,
             "campos": {**campos, "data_atendimento": data_atendimento,
                        "situacao": situacao or SituacaoAtendimento.ATIVO.value},
             "erros": erros, "duplicidades": [],
             "situacoes": list(SituacaoAtendimento)},
            status_code=400,
        )

    atendimento, dupes = atendimento_svc.criar(db, dados)
    db.commit()

    if dupes and not confirmar_duplicidade:
        return templates.TemplateResponse(
            request, "atendimentos/form.html",
            {"usuario": usuario, "modo": "novo", "atendimento_id": None,
             "campos": {**campos, "data_atendimento": data_atendimento,
                        "situacao": situacao or SituacaoAtendimento.ATIVO.value},
             "erros": [], "duplicidades": dupes,
             "situacoes": list(SituacaoAtendimento),
             "aviso_duplicidade": True},
            status_code=409,
        )

    registrar_operacao(
        db, operacao="criar_atendimento", usuario=usuario,
        entidade="atendimento", entidade_id=atendimento.id, request=request,
    )
    flash(request, "sucesso", f"Atendimento {atendimento.numero_protocolo or ('#' + str(atendimento.id))} cadastrado com sucesso.")
    excel_export.regenerar_apos_commit(db)
    return RedirectResponse(url=f"/atendimentos/{atendimento.id}", status_code=303)


@router.get("/atendimentos/{atendimento_id}", response_class=HTMLResponse)
def detalhe(
    request: Request,
    atendimento_id: int,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    atendimento = atendimento_svc.buscar_por_id(db, atendimento_id, incluir_arquivados=True)
    if atendimento is None:
        return RedirectResponse(url="/atendimentos?erro=nao_encontrado", status_code=303)
    return templates.TemplateResponse(
        request, "atendimentos/detalhe.html",
        {"usuario": usuario, "atendimento": atendimento},
    )


@router.get("/atendimentos/{atendimento_id}/editar", response_class=HTMLResponse)
def form_editar(
    request: Request,
    atendimento_id: int,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    atendimento = atendimento_svc.buscar_por_id(db, atendimento_id)
    if atendimento is None:
        return RedirectResponse(url="/atendimentos", status_code=303)

    campos = {
        "numero_protocolo": atendimento.numero_protocolo or "",
        "data_atendimento": atendimento.data_atendimento.isoformat(),
        "assistido_nome": atendimento.assistido.nome_original,
        "assistido_cpf": atendimento.assistido.cpf or "",
        "equipe_nome": atendimento.equipe.nome if atendimento.equipe else "",
        "area_nome": atendimento.area_juridica.nome if atendimento.area_juridica else "",
        "situacao": atendimento.situacao.value,
        "motivo_arquivamento": atendimento.motivo_arquivamento or "",
        "numero_processo": atendimento.numero_processo or "",
        "vara": atendimento.vara or "",
        "assunto": atendimento.assunto or "",
        "endereco_pasta": atendimento.endereco_pasta or "",
        "parte_contrariada": atendimento.parte_contrariada or "",
    }
    return templates.TemplateResponse(
        request, "atendimentos/form.html",
        {"usuario": usuario, "modo": "editar", "atendimento_id": atendimento.id,
         "campos": campos, "erros": [], "duplicidades": [],
         "situacoes": list(SituacaoAtendimento)},
    )


@router.post("/atendimentos/{atendimento_id}/editar", response_class=HTMLResponse)
def editar(
    request: Request,
    atendimento_id: int,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
    numero_protocolo: Annotated[str, Form()] = "",
    data_atendimento: Annotated[str, Form()] = "",
    assistido_nome: Annotated[str, Form()] = "",
    assistido_cpf: Annotated[str, Form()] = "",
    equipe_nome: Annotated[str, Form()] = "",
    area_nome: Annotated[str, Form()] = "",
    situacao: Annotated[str, Form()] = "",
    motivo_arquivamento: Annotated[str, Form()] = "",
    numero_processo: Annotated[str, Form()] = "",
    vara: Annotated[str, Form()] = "",
    assunto: Annotated[str, Form()] = "",
    endereco_pasta: Annotated[str, Form()] = "",
    parte_contrariada: Annotated[str, Form()] = "",
    confirmar_duplicidade: Annotated[str, Form()] = "",
):
    campos = _coletar_form(
        numero_protocolo, data_atendimento, assistido_nome, assistido_cpf,
        equipe_nome, area_nome, situacao, motivo_arquivamento, numero_processo,
        vara, assunto, endereco_pasta, parte_contrariada,
    )
    try:
        dados = AtendimentoFormulario(**campos)
    except Exception as e:
        erros = []
        if hasattr(e, "errors"):
            for err in e.errors():
                campo = ".".join(str(x) for x in err["loc"])
                erros.append(f"{campo}: {err['msg']}")
        else:
            erros.append(str(e))
        return templates.TemplateResponse(
            request, "atendimentos/form.html",
            {"usuario": usuario, "modo": "editar", "atendimento_id": atendimento_id,
             "campos": {**campos, "data_atendimento": data_atendimento,
                        "situacao": situacao or SituacaoAtendimento.ATIVO.value},
             "erros": erros, "duplicidades": [],
             "situacoes": list(SituacaoAtendimento)},
            status_code=400,
        )

    try:
        atendimento, dupes = atendimento_svc.atualizar(db, atendimento_id, dados)
        db.commit()
    except atendimento_svc.AtendimentoError:
        return RedirectResponse(url="/atendimentos", status_code=303)

    if dupes and not confirmar_duplicidade:
        return templates.TemplateResponse(
            request, "atendimentos/form.html",
            {"usuario": usuario, "modo": "editar", "atendimento_id": atendimento_id,
             "campos": {**campos, "data_atendimento": data_atendimento,
                        "situacao": situacao or SituacaoAtendimento.ATIVO.value},
             "erros": [], "duplicidades": dupes,
             "situacoes": list(SituacaoAtendimento),
             "aviso_duplicidade": True},
            status_code=409,
        )

    registrar_operacao(
        db, operacao="editar_atendimento", usuario=usuario,
        entidade="atendimento", entidade_id=atendimento.id, request=request,
    )
    flash(request, "sucesso", f"Atendimento {atendimento.numero_protocolo or ('#' + str(atendimento.id))} cadastrado com sucesso.")
    excel_export.regenerar_apos_commit(db)
    return RedirectResponse(url=f"/atendimentos/{atendimento.id}", status_code=303)


@router.post("/atendimentos/{atendimento_id}/arquivar")
def arquivar(
    request: Request,
    atendimento_id: int,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    try:
        atendimento_svc.arquivar(db, atendimento_id)
        db.commit()
        registrar_operacao(
            db, operacao="arquivar_atendimento", usuario=usuario,
            entidade="atendimento", entidade_id=atendimento_id, request=request,
        )
        flash(request, "info", "Atendimento arquivado.")
        excel_export.regenerar_apos_commit(db)
    except atendimento_svc.AtendimentoError:
        pass
    return RedirectResponse(url="/atendimentos", status_code=303)


@router.get("/assistidos/{assistido_id}/historico", response_class=HTMLResponse)
def historico(
    request: Request,
    assistido_id: int,
    usuario: Annotated[Usuario, Depends(exigir_login)],
    db: Annotated[Session, Depends(get_db)],
):
    assistido = assistido_svc.buscar_por_id(db, assistido_id)
    if assistido is None:
        return RedirectResponse(url="/atendimentos", status_code=303)
    atendimentos = assistido_svc.historico(db, assistido_id)
    return templates.TemplateResponse(
        request, "assistidos/historico.html",
        {"usuario": usuario, "assistido": assistido, "atendimentos": atendimentos},
    )