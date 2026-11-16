"""Popula o banco com dados LIMPOS (sem as sujeiras propositais).

Diferente da planilha fictícia (que é suja de propósito, para o ETL),
este seed cria registros já normalizados — para que a Fase 2 (CRUD)
tenha dados coerentes desde o início.

O usuário admin inicial é criado aqui, com senha forte e hash Argon2.
"""
from __future__ import annotations

import random
from datetime import date

from argon2 import PasswordHasher
from sqlalchemy import select

from backend.database.session import SessionLocal
from backend.models import (
    AreaJuridica,
    Assistido,
    Atendimento,
    Equipe,
    SituacaoAtendimento,
    Usuario,
)

random.seed(7)

NOMES = [
    "Maria Silva", "João Pereira", "Ana Souza", "Carlos Oliveira", "Fernanda Lima",
    "Roberto Almeida", "Patrícia Costa", "Lucas Ferreira", "Juliana Rodrigues",
    "Marcos Santos", "Camila Barbosa", "Rafael Martins", "Beatriz Rocha",
]

AREAS = ["Cível", "Família", "Trabalhista", "Consumidor", "Previdenciário", "Criminal"]
EQUIPES = ["Equipe A - 2023/1", "Equipe B - 2023/2", "Equipe C - 2024/1", "Equipe D - 2025/1"]

ASSUNTOS = {
    "Cível": "Indenização por danos morais",
    "Família": "Divórcio consensual",
    "Trabalhista": "Verbas rescisórias",
    "Consumidor": "Cobrança indevida",
    "Previdenciário": "Aposentadoria por idade",
    "Criminal": "Ameaça",
}


def _get_or_create(db, model, nome: str):
    obj = db.scalar(select(model).where(model.nome == nome))
    if obj:
        return obj
    obj = model(nome=nome)
    db.add(obj)
    db.flush()
    return obj


def seed() -> None:
    db = SessionLocal()
    try:
        # Usuário admin inicial
        if not db.scalar(select(Usuario).where(Usuario.username == "admin")):
            db.add(
                Usuario(
                    username="admin",
                    nome_completo="Administrador do NPJ",
                    email="admin@npj.local",
                    senha_hash=PasswordHasher().hash("admin123"),
                    ativo=True,
                    is_seed=True,
                )
            )
            print("[OK] Usuario 'admin' criado (senha: admin123). TROQUE em produção.")
        else:
            print("[SKIP] Usuario 'admin' já existe.")

        # Áreas
        areas = {a: _get_or_create(db, AreaJuridica, a) for a in AREAS}
        equipes = {e: _get_or_create(db, Equipe, e) for e in EQUIPES}

        # Atendimentos limpos
        existentes = db.scalar(select(Atendimento).limit(1))
        if existentes:
            print("[SKIP] Atendimentos já existem — seed idempotente.")
        else:
            for i in range(60):
                nome = random.choice(NOMES)
                assistido = db.scalar(
                    select(Assistido).where(Assistido.nome_normalizado == nome.lower())
                )
                if not assistido:
                    assistido = Assistido(nome_original=nome, nome_normalizado=nome.lower())
                    db.add(assistido)
                    db.flush()

                area_nome = random.choice(AREAS)
                ano = random.randint(2018, 2025)
                d = date(ano, random.randint(1, 12), random.randint(1, 28))

                db.add(
                    Atendimento(
                        numero_protocolo=f"NPJ-SEED-{i+1:04d}",
                        data_atendimento=d,
                        assistido_id=assistido.id,
                        cliente_texto_original=assistido.nome_original,
                        equipe_id=random.choice(list(equipes.values())).id,
                        equipe_texto_original=random.choice(EQUIPES),
                        area_juridica_id=areas[area_nome].id,
                        area_texto_original=area_nome,
                        situacao=SituacaoAtendimento.ATIVO,
                        assunto=ASSUNTOS[area_nome],
                        vara="1ª Vara Cível",
                        origem="seed",
                    )
                )
            print("[OK] 60 atendimentos de seed criados.")

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()