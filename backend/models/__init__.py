"""Importa todos os modelos para que o Alembic os enxergue."""
from backend.models.area_juridica import AreaJuridica
from backend.models.assistido import Assistido
from backend.models.atendimento import Atendimento, SituacaoAtendimento
from backend.models.audit_log import AuditLog
from backend.models.backup import Backup
from backend.models.equipe import Equipe
from backend.models.usuario import Usuario

__all__ = [
    "AreaJuridica",
    "Assistido",
    "Atendimento",
    "SituacaoAtendimento",
    "AuditLog",
    "Backup",
    "Equipe",
    "Usuario",
]