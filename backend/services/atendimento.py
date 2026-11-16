"""Serviço de Atendimento: criação, atualização, arquivamento e listagem."""
from __future__ import annotations

from datetime import date
from math import ceil

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from backend.models import AreaJuridica, Atendimento, Equipe, SituacaoAtendimento
from backend.schemas.atendimento import AtendimentoFiltros, AtendimentoFormulario
from backend.services import assistido as assistido_service


class AtendimentoError(Exception):
    """Erro de negócio do atendimento."""


# ---------------------------------------------------------------------------
# Geradores de auto-preenchimento
# ---------------------------------------------------------------------------

def gerar_proximo_protocolo(db: Session) -> str:
    """Gera o próximo protocolo no formato ``NPJ-YYYY-NNNN``.

    Baseia-se no maior número sequencial já registrado **para o ano atual**.
    Se não houver registros no ano atual, começa em ``0001``.
    """
    ano_atual = date.today().year
    prefixo = f"NPJ-{ano_atual}-"

    protocolos = db.scalars(
        select(Atendimento.numero_protocolo).where(
            Atendimento.numero_protocolo.like(f"{prefixo}%")
        )
    ).all()

    max_seq = 0
    for p in protocolos:
        if not p:
            continue
        try:
            seq = int(p[len(prefixo):])
            if seq > max_seq:
                max_seq = seq
        except (ValueError, TypeError):
            continue

    return f"{prefixo}{max_seq + 1:04d}"


def gerar_proximo_processo(db: Session) -> str:
    """Gera o próximo número de processo no formato CNJ básico.

    Formato: ``NNNNNNN-01.YYYY.8.26.100``
    - ``NNNNNNN``: sequencial de 7 dígitos (max + 1 do ano atual)
    - ``01``: segmento (fixo)
    - ``YYYY``: ano atual
    - ``8.26``: TJSP
    - ``100``: tribunal (fixo)

    Baseia-se no maior sequencial de processos do ano atual que sigam o padrão.
    """
    ano_atual = date.today().year

    processos = db.scalars(
        select(Atendimento.numero_processo).where(
            Atendimento.numero_processo.isnot(None),
            Atendimento.numero_processo.like(f"%-%.{ano_atual}.8.26.%"),
        )
    ).all()

    max_seq = 0
    for p in processos:
        if not p or "-" not in p:
            continue
        try:
            seq = int(p.split("-")[0])
            if seq > max_seq:
                max_seq = seq
        except (ValueError, IndexError):
            continue

    return f"{max_seq + 1:07d}-01.{ano_atual}.8.26.100"


# ---------------------------------------------------------------------------
# Helpers internos (existentes)
# ---------------------------------------------------------------------------

def _obter_ou_criar_area(db: Session, nome: str) -> AreaJuridica:
    nome = " ".join(nome.split())
    existente = db.scalar(
        select(AreaJuridica).where(func.lower(AreaJuridica.nome) == nome.lower())
    )
    if existente:
        return existente
    nova = AreaJuridica(nome=nome)
    db.add(nova)
    db.flush()
    return nova


def _obter_ou_criar_equipe(db: Session, nome: str | None) -> Equipe | None:
    if not nome:
        return None
    nome = " ".join(nome.split())
    if not nome:
        return None
    existente = db.scalar(
        select(Equipe).where(func.lower(Equipe.nome) == nome.lower())
    )
    if existente:
        return existente
    nova = Equipe(nome=nome)
    db.add(nova)
    db.flush()
    return nova


def detectar_duplicidade(
    db: Session,
    *,
    assistido_id: int,
    data_atendimento: date,
    area_juridica_id: int,
    numero_protocolo: str | None,
    excluir_id: int | None = None,
) -> list[Atendimento]:
    condicoes = []
    if numero_protocolo:
        condicoes.append(Atendimento.numero_protocolo == numero_protocolo)
    condicoes.append(
        and_(
            Atendimento.assistido_id == assistido_id,
            Atendimento.data_atendimento == data_atendimento,
            Atendimento.area_juridica_id == area_juridica_id,
        )
    )

    stmt = select(Atendimento).where(
        Atendimento.ativo.is_(True),
        or_(*condicoes),
    )
    if excluir_id is not None:
        stmt = stmt.where(Atendimento.id != excluir_id)
    return list(db.scalars(stmt))


def _aplicar_dados(
    db: Session,
    atendimento: Atendimento,
    dados: AtendimentoFormulario,
) -> None:
    assistido = assistido_service.buscar_ou_criar(
        db, dados.assistido_nome, dados.assistido_cpf
    )
    equipe = _obter_ou_criar_equipe(db, dados.equipe_nome)
    area = _obter_ou_criar_area(db, dados.area_nome)

    atendimento.numero_protocolo = (dados.numero_protocolo or "").strip() or None
    atendimento.data_atendimento = dados.data_atendimento
    atendimento.assistido_id = assistido.id
    atendimento.cliente_texto_original = assistido.nome_original
    atendimento.equipe_id = equipe.id if equipe else None
    atendimento.equipe_texto_original = equipe.nome if equipe else None
    atendimento.area_juridica_id = area.id
    atendimento.area_texto_original = area.nome
    atendimento.situacao = dados.situacao
    atendimento.motivo_arquivamento = dados.motivo_arquivamento
    atendimento.numero_processo = (dados.numero_processo or "").strip() or None
    atendimento.vara = (dados.vara or "").strip() or None
    atendimento.assunto = (dados.assunto or "").strip() or None
    atendimento.endereco_pasta = (dados.endereco_pasta or "").strip() or None
    atendimento.parte_contrariada = (dados.parte_contrariada or "").strip() or None


def criar(
    db: Session,
    dados: AtendimentoFormulario,
    *,
    origem: str = "manual",
) -> tuple[Atendimento, list[Atendimento]]:
    atendimento = Atendimento(origem=origem)
    _aplicar_dados(db, atendimento, dados)

    dupes = detectar_duplicidade(
        db,
        assistido_id=atendimento.assistido_id,
        data_atendimento=atendimento.data_atendimento,
        area_juridica_id=atendimento.area_juridica_id,
        numero_protocolo=atendimento.numero_protocolo,
    )

    db.add(atendimento)
    db.flush()
    return atendimento, dupes


def atualizar(
    db: Session,
    atendimento_id: int,
    dados: AtendimentoFormulario,
) -> tuple[Atendimento, list[Atendimento]]:
    atendimento = db.get(Atendimento, atendimento_id)
    if atendimento is None or not atendimento.ativo:
        raise AtendimentoError("Atendimento não encontrado ou já arquivado.")

    _aplicar_dados(db, atendimento, dados)

    dupes = detectar_duplicidade(
        db,
        assistido_id=atendimento.assistido_id,
        data_atendimento=atendimento.data_atendimento,
        area_juridica_id=atendimento.area_juridica_id,
        numero_protocolo=atendimento.numero_protocolo,
        excluir_id=atendimento.id,
    )

    db.flush()
    return atendimento, dupes


def arquivar(db: Session, atendimento_id: int) -> Atendimento:
    atendimento = db.get(Atendimento, atendimento_id)
    if atendimento is None:
        raise AtendimentoError("Atendimento não encontrado.")
    if not atendimento.ativo:
        raise AtendimentoError("Atendimento já está arquivado.")
    atendimento.ativo = False
    db.flush()
    return atendimento


def buscar_por_id(
    db: Session,
    atendimento_id: int,
    *,
    incluir_arquivados: bool = False,
) -> Atendimento | None:
    stmt = (
        select(Atendimento)
        .options(
            joinedload(Atendimento.assistido),
            joinedload(Atendimento.area_juridica),
            joinedload(Atendimento.equipe),
        )
        .where(Atendimento.id == atendimento_id)
    )
    if not incluir_arquivados:
        stmt = stmt.where(Atendimento.ativo.is_(True))
    return db.scalar(stmt)


def _aplicar_filtros(stmt, filtros: AtendimentoFiltros):
    if not filtros.incluir_arquivados:
        stmt = stmt.where(Atendimento.ativo.is_(True))

    if filtros.q:
        termo = f"%{filtros.q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Atendimento.cliente_texto_original).like(termo),
                func.lower(Atendimento.numero_protocolo).like(termo),
                func.lower(Atendimento.numero_processo).like(termo),
                func.lower(Atendimento.assunto).like(termo),
            )
        )
    if filtros.data_inicio:
        stmt = stmt.where(Atendimento.data_atendimento >= filtros.data_inicio)
    if filtros.data_fim:
        stmt = stmt.where(Atendimento.data_atendimento <= filtros.data_fim)
    if filtros.ano:
        stmt = stmt.where(
            func.strftime("%Y", Atendimento.data_atendimento) == str(filtros.ano)
        )
    if filtros.semestre in (1, 2):
        meses = range(1, 7) if filtros.semestre == 1 else range(7, 13)
        stmt = stmt.where(
            func.strftime("%m", Atendimento.data_atendimento).in_(
                [f"{m:02d}" for m in meses]
            )
        )
    if filtros.area_id:
        stmt = stmt.where(Atendimento.area_juridica_id == filtros.area_id)
    if filtros.equipe_id:
        stmt = stmt.where(Atendimento.equipe_id == filtros.equipe_id)
    if filtros.situacao:
        stmt = stmt.where(Atendimento.situacao == filtros.situacao)
    if filtros.assistido_id:
        stmt = stmt.where(Atendimento.assistido_id == filtros.assistido_id)

    return stmt


def listar(
    db: Session,
    filtros: AtendimentoFiltros,
    *,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Atendimento], int, int]:
    page = max(1, page)
    page_size = max(1, min(page_size, 100))

    base = _aplicar_filtros(select(Atendimento), filtros)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    total_paginas = max(1, ceil(total / page_size))

    stmt = (
        base
        .options(
            joinedload(Atendimento.assistido),
            joinedload(Atendimento.area_juridica),
            joinedload(Atendimento.equipe),
        )
        .order_by(Atendimento.data_atendimento.desc(), Atendimento.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    itens = list(db.scalars(stmt))
    return itens, total, total_paginas