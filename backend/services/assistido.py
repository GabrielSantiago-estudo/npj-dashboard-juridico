"""Serviço de Assistido: normalização, busca e criação com deduplicação."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Assistido, Atendimento
from backend.schemas.common import limpar_cpf, normalizar_nome


def buscar_por_nome(db: Session, nome: str) -> list[Assistido]:
    alvo = normalizar_nome(nome)
    return list(
        db.scalars(
            select(Assistido)
            .where(Assistido.nome_normalizado.like(f"%{alvo}%"))
            .order_by(Assistido.nome_original)
            .limit(50)
        )
    )


def buscar_por_id(db: Session, assistido_id: int) -> Assistido | None:
    return db.scalar(select(Assistido).where(Assistido.id == assistido_id))


def buscar_ou_criar(db: Session, nome: str, cpf: str | None = None) -> Assistido:
    nome_limpo = " ".join(nome.split())
    nome_norm = normalizar_nome(nome_limpo)
    cpf_limpo = limpar_cpf(cpf)

    if cpf_limpo:
        existente = db.scalar(
            select(Assistido).where(
                Assistido.nome_normalizado == nome_norm,
                Assistido.cpf == cpf_limpo,
            )
        )
    else:
        existente = db.scalar(
            select(Assistido).where(
                Assistido.nome_normalizado == nome_norm,
                Assistido.cpf.is_(None),
            )
        )

    if existente:
        return existente

    novo = Assistido(
        nome_original=nome_limpo,
        nome_normalizado=nome_norm,
        cpf=cpf_limpo,
    )
    db.add(novo)
    db.flush()
    return novo


def historico(db: Session, assistido_id: int) -> list[Atendimento]:
    return list(
        db.scalars(
            select(Atendimento)
            .where(Atendimento.assistido_id == assistido_id)
            .order_by(Atendimento.data_atendimento.desc(), Atendimento.id.desc())
        )
    )