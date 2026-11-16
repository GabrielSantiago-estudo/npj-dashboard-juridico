"""Schemas e utilitários comuns (validações reutilizáveis)."""
from __future__ import annotations

import re
import unicodedata


def normalizar_nome(nome: str) -> str:
    """Normaliza nome para busca/deduplicação."""
    nome = " ".join(nome.split())
    sem_acento = (
        unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode("ascii")
    )
    return sem_acento.lower()


def limpar_cpf(cpf: str | None) -> str | None:
    """Remove pontuação do CPF. Retorna None se vazio."""
    if not cpf:
        return None
    digitos = re.sub(r"\D", "", cpf)
    return digitos or None


def validar_cpf(cpf: str) -> bool:
    """Valida CPF pelo algoritmo oficial dos dígitos verificadores."""
    cpf = re.sub(r"\D", "", cpf)
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * ((i + 1) - j) for j in range(i))
        digito = (soma * 10 % 11) % 10
        if int(cpf[i]) != digito:
            return False
    return True