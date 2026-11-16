"""Hash e verificação de senhas com Argon2 (sem passlib)."""
from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

_hasher = PasswordHasher()


def hash_senha(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    try:
        return _hasher.verify(hash_armazenado, senha)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception:
        return False


def precisa_rehash(hash_armazenado: str) -> bool:
    try:
        return _hasher.check_needs_rehash(hash_armazenado)
    except Exception:
        return False