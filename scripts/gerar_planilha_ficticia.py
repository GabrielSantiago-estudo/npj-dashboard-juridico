"""Gera a planilha histórica fictícia do NPJ (2006-2025).

Cria imports/NPJ_Historico_FICTICIO_2006_2025.xlsx com as 12 colunas
reais informadas pelo NPJ, incluindo ~15% de inconsistências propositais
para exercitar o ETL da Fase 3.

NUNCA substitui a planilha real. O nome do arquivo deixa explícito
que é FICTÍCIO (conforme seção 15 - LGPD).
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from backend.config import settings

random.seed(42)

COLUNAS = [
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

NOMES = [
    "Maria Silva", "João Pereira", "Ana Souza", "Carlos Oliveira", "Fernanda Lima",
    "Roberto Almeida", "Patrícia Costa", "Lucas Ferreira", "Juliana Rodrigues",
    "Marcos Santos", "Camila Barbosa", "Rafael Martins", "Beatriz Rocha",
    "Gustavo Ribeiro", "Larissa Carvalho", "Thiago Gomes", "Vanessa Araújo",
    "Diego Mendes", "Aline Nunes", "Bruno Castro", "Tatiane Dias", "Felipe Moreira",
    "Renata Cardoso", "André Teixeira", "Priscila Freitas", "Rodrigo Pinto",
    "Débora Correia", "Vinícius Lopes", "Simone Batista", "Eduardo Machado",
]

PARTES = [
    "Banco X S.A.", "Comércio Y Ltda.", "Indústria Z S.A.", "Supermercado W",
    "Construtora V", "Seguradora U", "Telefonia T", "Plano de Saúde S",
    "Locadora R", "Empresa Q", "Condomínio P", "Município de O",
]

EQUIPES = [
    "Equipe A - 2006/1", "Equipe A - 2006/2", "Equipe B - 2007/1",
    "Equipe B - 2007/2", "Equipe C - 2008/1", "Equipe C - 2008/2",
    "Equipe A - 2020/1", "Equipe B - 2020/2", "Equipe C - 2023/1",
    "Equipe D - 2023/2", "Equipe A - 2024/1", "Equipe B - 2025/1",
]

AREAS = ["Cível", "Família", "Trabalhista", "Consumidor", "Previdenciário", "Criminal"]
AREAS_VARIANTES = {
    "Cível": ["civel", "CÍVEL", "CIVEL", "cível", " Cível "],
    "Família": ["familia", "FAMÍLIA", "FAMILIA"],
    "Trabalhista": ["trabalhista", "TRABALHISTA", "Trab."],
    "Consumidor": ["consumidor", "CONSUMIDOR"],
    "Previdenciário": ["previdenciario", "PREVIDENCIÁRIO", "prev."],
    "Criminal": ["criminal", "CRIMINAL"],
}

SITUACOES = ["Ativo", "Arquivado", "Indeferido", "Concluído"]
SITUACOES_VARIANTES = ["arquivado", "ARQUIVADO", "ativo", "ATIVO", "indeferido", "concluído"]

ASSUNTOS = {
    "Cível": ["Indenização por danos morais", "Cobrança indevida", "Revisão de contrato", "Usucapião"],
    "Família": ["Divórcio consensual", "Pensão alimentícia", "Guarda compartilhada", "Reconhecimento de paternidade"],
    "Trabalhista": ["Verbas rescisórias", "Horas extras", "Assédio moral", "Acidente de trabalho"],
    "Consumidor": ["Produto com defeito", "Cobrança indevida", "Negativação indevida", "Troca de produto"],
    "Previdenciário": ["Aposentadoria por idade", "Auxílio-doença", "Revisão de benefício", "BPC/LOAS"],
    "Criminal": ["Furto simples", "Lesão corporal", "Ameaça", "Violência doméstica"],
}

VARA = {
    "Cível": ["1ª Vara Cível", "2ª Vara Cível", "3ª Vara Cível"],
    "Família": ["1ª Vara de Família", "2ª Vara de Família"],
    "Trabalhista": ["1ª Vara do Trabalho", "2ª Vara do Trabalho"],
    "Consumidor": ["Juizado Especial Cível", "1ª Vara do Consumidor"],
    "Previdenciário": ["Juizado Especial Federal", "1ª Vara Federal"],
    "Criminal": ["1ª Vara Criminal", "2ª Vara Criminal"],
}

MOTIVOS = [
    "Acordo entre as partes",
    "Desistência do assistido",
    "Falta de documentação",
    "Ausência de interesse jurídico",
    "Encaminhamento a outro órgão",
]


def _data_aleatoria(ano_min: int = 2006, ano_max: int = 2025) -> date:
    ano = random.randint(ano_min, ano_max)
    inicio = date(ano, 1, 1)
    fim = date(ano, 12, 31)
    return inicio + timedelta(days=random.randint(0, (fim - inicio).days))


def _sujeira_data(d: date) -> object:
    r = random.random()
    if r < 0.85:
        return d
    if r < 0.90:
        return d.strftime("%d/%m/%Y")
    if r < 0.94:
        return d.strftime("%m/%d/%Y")
    if r < 0.97:
        return (d - date(1899, 12, 30)).days
    return "31/02/2019"


def _sujeira_nome(nome: str) -> str:
    r = random.random()
    if r < 0.85:
        return nome
    if r < 0.92:
        return f"  {nome}  "
    if r < 0.97:
        return nome.upper()
    return nome.replace(" ", "  ")


def _sujeira_area(area: str) -> str:
    r = random.random()
    if r < 0.85:
        return area
    return random.choice(AREAS_VARIANTES[area])


def _sujeira_situacao(sit: str) -> str:
    r = random.random()
    if r < 0.88:
        return sit
    return random.choice(SITUACOES_VARIANTES)


def gerar_registros(n: int = 250) -> list[dict]:
    registros: list[dict] = []
    protocolos_usados: list[str] = []

    for _ in range(n):
        ano = random.randint(2006, 2025)
        d = _data_aleatoria(ano, ano)
        area = random.choices(AREAS, weights=[40, 25, 15, 10, 7, 3])[0]

        if random.random() < 0.04:
            protocolo = ""
        elif random.random() < 0.03 and protocolos_usados:
            protocolo = random.choice(protocolos_usados)
        else:
            protocolo = f"NPJ-{ano}-{random.randint(1, 9999):04d}"
        if protocolo:
            protocolos_usados.append(protocolo)

        situacao = random.choices(SITUACOES, weights=[45, 30, 10, 15])[0]
        motivo = ""
        if situacao in ("Arquivado", "Indeferido"):
            motivo = random.choice(MOTIVOS)
        elif random.random() < 0.03:
            motivo = random.choice(MOTIVOS)

        tem_processo = random.random() < 0.55
        processo = (
            f"{random.randint(1000000, 9999999)}-"
            f"{random.randint(10, 99)}.{ano}.8.26.{random.randint(100, 999)}"
            if tem_processo else ""
        )
        vara = random.choice(VARA[area]) if tem_processo else ""

        cliente = random.choice(NOMES)
        parte = random.choice(PARTES)

        registros.append(
            {
                "DATA": _sujeira_data(d),
                "NUMERO DE PROTOCOLO": protocolo,
                "CLIENTE": _sujeira_nome(cliente),
                "EQUIPE": random.choice(EQUIPES),
                "SITUACAO": _sujeira_situacao(situacao),
                "MOTIVO DO ARQUIVAMENTO/INDEFERIMENTO": motivo,
                "PROCESSO": processo,
                "VARA": vara,
                "AREA": _sujeira_area(area),
                "ASSUNTO": random.choice(ASSUNTOS[area]),
                "ENDERECO DAS PASTAS": f"Armário {random.randint(1,8)} / Pasta {random.randint(1,200):03d}",
                "PARTE CONTRARIADA": parte,
            }
        )

    # Linhas totalmente vazias propositais
    for _ in range(4):
        registros.append({c: "" for c in COLUNAS})

    random.shuffle(registros)
    return registros


def main() -> None:
    destino = Path(settings.excel_historico_ficticio_path)
    destino.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(gerar_registros(), columns=COLUNAS)

    # Preserva a sujeira exatamente como gerada (sem inferência de dtype do Pandas)
    for col in df.columns:
        df[col] = df[col].astype(object)

    df.to_excel(destino, index=False, sheet_name="Atendimentos", engine="openpyxl")

    print(f"[OK] Planilha ficticia gerada: {destino}")
    print(f"     Registros: {len(df)}")
    print(f"     Colunas:   {len(df.columns)}")


if __name__ == "__main__":
    main()