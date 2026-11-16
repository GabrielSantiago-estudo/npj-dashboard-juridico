"""Serviço de ETL: extrai, transforma e carrega a planilha histórica."""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Atendimento, SituacaoAtendimento
from backend.schemas.common import normalizar_nome
from backend.schemas.etl import (
    LinhaImportada,
    PreviewImportacao,
    RelatorioImportacao,
)
from backend.services import assistido as assistido_service
from backend.services import atendimento as atendimento_service

log = logging.getLogger(__name__)

COLUNAS_ESPERADAS = [
    "DATA",
    "NUMERO DE PROTOCOLO",
    "CLIENTE",
    "EQUIPE",
    "SITUACAO",
    "MOTIVO DO ARQUIVAMENTO/INDEFERIMENTO",
    "PROCESSO",
    "VARA",
    "AREA",
    "ASSUNTO",
    "ENDERECO DAS PASTAS",
    "PARTE CONTRARIADA",
]

AREAS_CANONICAS = {
    "civel": "Cível",
    "familia": "Família",
    "trabalhista": "Trabalhista",
    "consumidor": "Consumidor",
    "previdenciario": "Previdenciário",
    "criminal": "Criminal",
}

SITUACOES_CANONICAS = {
    "ativo": SituacaoAtendimento.ATIVO,
    "arquivado": SituacaoAtendimento.ARQUIVADO,
    "indeferido": SituacaoAtendimento.INDEFERIDO,
    "concluido": SituacaoAtendimento.CONCLUIDO,
}


# ---------------------------------------------------------------------------
# Helpers de normalização
# ---------------------------------------------------------------------------

def _texto(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return str(v).strip()


def _validar_data(d: date) -> tuple[date | None, str | None]:
    if d.year < 2006:
        return None, f"data anterior a 2006: {d.isoformat()}"
    if d > date.today():
        return d, f"data futura ({d.isoformat()}) — revisar"
    return d, None


def _normalizar_data(v: Any) -> tuple[date | None, str | None]:
    if isinstance(v, (datetime, date)):
        d = v.date() if isinstance(v, datetime) else v
        return _validar_data(d)

    s = _texto(v)
    if not s:
        return None, "data vazia"

    # Serial Excel
    try:
        numero = float(s.replace(",", "."))
        if 30000 <= numero <= 50000:
            d = date(1899, 12, 30) + timedelta(days=int(numero))
            return _validar_data(d)
    except (ValueError, TypeError):
        pass

    # dd/mm/yyyy ou mm/dd/yyyy
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})$", s)
    if m:
        a, b, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        ano = c if c > 100 else 2000 + c
        try:
            d = date(ano, b, a)
            if 1 <= b <= 12:
                return _validar_data(d)
        except ValueError:
            pass
        try:
            d = date(ano, a, b)
            return _validar_data(d)
        except ValueError:
            return None, f"data inválida: {s}"

    return None, f"formato de data não reconhecido: {s}"


def _normalizar_area(v: Any) -> tuple[str, str | None]:
    s = _texto(v)
    if not s:
        return "", "área vazia"
    chave = normalizar_nome(s).replace(".", "").strip()
    if chave in AREAS_CANONICAS:
        canonica = AREAS_CANONICAS[chave]
        return canonica, (None if canonica == s else f"área normalizada: '{s}' -> '{canonica}'")
    for prefixo, canonica in AREAS_CANONICAS.items():
        if chave.startswith(prefixo[:4]):
            return canonica, f"área normalizada: '{s}' -> '{canonica}'"
    return s, f"área não reconhecida: '{s}'"


def _normalizar_situacao(v: Any) -> tuple[SituacaoAtendimento, str | None]:
    s = _texto(v)
    if not s:
        return SituacaoAtendimento.ATIVO, "situação vazia — assumido 'Ativo'"
    chave = normalizar_nome(s)
    if chave in SITUACOES_CANONICAS:
        canonica = SITUACOES_CANONICAS[chave]
        if canonica.value == s:
            return canonica, None
        return canonica, f"situação normalizada: '{s}' -> '{canonica.value}'"
    return SituacaoAtendimento.ATIVO, f"situação desconhecida '{s}' — assumido 'Ativo'"


def _normalizar_nome_cliente(v: Any) -> tuple[str, str | None]:
    s = _texto(v)
    if not s:
        return "", "cliente vazio"
    limpo = " ".join(s.split())
    aviso = None
    if limpo != s:
        aviso = f"nome ajustado (espaços): '{s}' -> '{limpo}'"
    if limpo.isupper() and len(limpo) > 3:
        limpo = limpo.title()
        aviso = f"nome em caixa alta: '{s}' -> '{limpo}'"
    return limpo, aviso


# ---------------------------------------------------------------------------
# Transformação de uma linha
# ---------------------------------------------------------------------------

def _transformar_linha(numero_linha: int, row: dict) -> LinhaImportada:
    original = {c: _texto(row.get(c)) for c in COLUNAS_ESPERADAS}
    avisos: list[str] = []
    normalizado: dict = {}

    if not any(original.values()):
        return LinhaImportada(
            numero_linha=numero_linha, original=original, normalizado={},
            status="vazio", avisos=["linha em branco"],
        )

    data, aviso = _normalizar_data(row.get("DATA"))
    if aviso:
        avisos.append(aviso)
    normalizado["data_atendimento"] = data.isoformat() if data else None

    nome, aviso = _normalizar_nome_cliente(row.get("CLIENTE"))
    if aviso:
        avisos.append(aviso)
    normalizado["assistido_nome"] = nome

    area, aviso = _normalizar_area(row.get("AREA"))
    if aviso:
        avisos.append(aviso)
    normalizado["area_nome"] = area

    situacao, aviso = _normalizar_situacao(row.get("SITUACAO"))
    if aviso:
        avisos.append(aviso)
    normalizado["situacao"] = situacao.value

    protocolo = _texto(row.get("NUMERO DE PROTOCOLO"))
    if not protocolo:
        avisos.append("protocolo vazio")
    normalizado["numero_protocolo"] = protocolo or None

    motivo = _texto(row.get("MOTIVO DO ARQUIVAMENTO/INDEFERIMENTO"))
    if situacao in (SituacaoAtendimento.ARQUIVADO, SituacaoAtendimento.INDEFERIDO):
        if not motivo:
            avisos.append("motivo obrigatório ausente para arquivado/indeferido")
    elif motivo:
        avisos.append("motivo preenchido mas situação não é arquivado/indeferido — limpo")
        motivo = ""
    normalizado["motivo_arquivamento"] = motivo or None

    normalizado["equipe_nome"] = _texto(row.get("EQUIPE")) or None
    normalizado["numero_processo"] = _texto(row.get("PROCESSO")) or None
    normalizado["vara"] = _texto(row.get("VARA")) or None
    normalizado["assunto"] = _texto(row.get("ASSUNTO")) or None
    normalizado["endereco_pasta"] = _texto(row.get("ENDERECO DAS PASTAS")) or None
    normalizado["parte_contrariada"] = _texto(row.get("PARTE CONTRARIADA")) or None

    if data is None:
        status = "inconsistente"
    elif avisos:
        status = "tratado"
    else:
        status = "ok"

    return LinhaImportada(
        numero_linha=numero_linha,
        original=original,
        normalizado=normalizado,
        status=status,
        avisos=avisos,
    )


# ---------------------------------------------------------------------------
# Processamento
# ---------------------------------------------------------------------------

def processar_planilha(caminho: str | Path, arquivo_nome: str) -> PreviewImportacao:
    df = pd.read_excel(caminho, dtype=object, engine="openpyxl")

    faltando = [c for c in COLUNAS_ESPERADAS if c not in df.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes na planilha: {faltando}")

    linhas: list[LinhaImportada] = []
    for idx, row in df.iterrows():
        linhas.append(_transformar_linha(idx + 2, row.to_dict()))

    # Duplicidades dentro do arquivo
    protocolos: dict[str, list[LinhaImportada]] = {}
    chaves_ad: dict[tuple, list[LinhaImportada]] = {}
    for ln in linhas:
        if ln.status == "vazio":
            continue
        prot = ln.normalizado.get("numero_protocolo")
        if prot:
            protocolos.setdefault(prot, []).append(ln)
        chave = (
            normalizar_nome(ln.normalizado.get("assistido_nome") or ""),
            ln.normalizado.get("data_atendimento"),
            ln.normalizado.get("area_nome"),
        )
        if all(chave):
            chaves_ad.setdefault(chave, []).append(ln)

    vistos_dup: set[int] = set()
    for grupo in list(protocolos.values()) + list(chaves_ad.values()):
        if len(grupo) > 1:
            for ln in grupo:
                if ln.numero_linha not in vistos_dup:
                    vistos_dup.add(ln.numero_linha)
                    ln.status = "duplicado"
                    ln.avisos.append("possível duplicidade (protocolo ou mesmo assistido+data+área)")

    rel = RelatorioImportacao(
        total_linhas=len(linhas),
        linhas_vazias=sum(1 for l in linhas if l.status == "vazio"),
        linhas_ok=sum(1 for l in linhas if l.status == "ok"),
        linhas_tratadas=sum(1 for l in linhas if l.status == "tratado"),
        linhas_inconsistentes=sum(1 for l in linhas if l.status == "inconsistente"),
        linhas_duplicadas=sum(1 for l in linhas if l.status == "duplicado"),
    )
    rel.precisa_revisao = rel.linhas_inconsistentes + rel.linhas_duplicadas

    return PreviewImportacao(
        token=uuid.uuid4().hex, arquivo_nome=arquivo_nome, linhas=linhas, relatorio=rel
    )


def salvar_preview(preview: PreviewImportacao) -> None:
    staging = settings.resolve_path("./imports/_staging")
    staging.mkdir(parents=True, exist_ok=True)
    caminho = staging / f"{preview.token}.json"
    caminho.write_text(preview.model_dump_json(indent=2), encoding="utf-8")


def carregar_preview(token: str) -> PreviewImportacao | None:
    staging = settings.resolve_path("./imports/_staging")
    caminho = staging / f"{token}.json"
    if not caminho.exists():
        return None
    return PreviewImportacao.model_validate_json(caminho.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Confirmação (carga transacional)
# ---------------------------------------------------------------------------

def confirmar_importacao(db: Session, preview: PreviewImportacao) -> RelatorioImportacao:
    rel = preview.relatorio.model_copy()
    assistidos_vistos: set[int] = set()

    try:
        for ln in preview.linhas:
            if ln.status == "vazio":
                continue
            n = ln.normalizado
            if n.get("data_atendimento") is None:
                continue
            nome = n.get("assistido_nome")
            if not nome:
                continue

            ass = assistido_service.buscar_ou_criar(db, nome, cpf=None)
            if ass.id not in assistidos_vistos:
                assistidos_vistos.add(ass.id)
                rel.assistidos_criados += 1
            else:
                rel.assistidos_reutilizados += 1

            area = atendimento_service._obter_ou_criar_area(db, n["area_nome"])
            equipe = atendimento_service._obter_ou_criar_equipe(db, n.get("equipe_nome"))

            origem = "importado" if ln.status == "ok" else "importado_revisao"

            db.add(
                Atendimento(
                    numero_protocolo=n.get("numero_protocolo"),
                    data_atendimento=date.fromisoformat(n["data_atendimento"]),
                    assistido_id=ass.id,
                    cliente_texto_original=ass.nome_original,
                    equipe_id=equipe.id if equipe else None,
                    equipe_texto_original=equipe.nome if equipe else None,
                    area_juridica_id=area.id,
                    area_texto_original=area.nome,
                    situacao=SituacaoAtendimento(n["situacao"]),
                    motivo_arquivamento=n.get("motivo_arquivamento"),
                    numero_processo=n.get("numero_processo"),
                    vara=n.get("vara"),
                    assunto=n.get("assunto"),
                    endereco_pasta=n.get("endereco_pasta"),
                    parte_contrariada=n.get("parte_contrariada"),
                    origem=origem,
                    ativo=True,
                )
            )
            rel.importados += 1

        db.commit()
    except Exception:
        db.rollback()
        raise

    return rel


def salvar_relatorio_final(token: str, relatorio: RelatorioImportacao) -> None:
    staging = settings.resolve_path("./imports/_staging")
    (staging / f"{token}_relatorio.json").write_text(
        relatorio.model_dump_json(indent=2), encoding="utf-8"
    )


def carregar_relatorio_final(token: str) -> RelatorioImportacao | None:
    staging = settings.resolve_path("./imports/_staging")
    caminho = staging / f"{token}_relatorio.json"
    if not caminho.exists():
        return None
    return RelatorioImportacao.model_validate_json(caminho.read_text(encoding="utf-8"))