"""Rotas FastAPI."""
from backend.routes.atendimentos import router as atendimentos_router
from backend.routes.auth import router as auth_router
from backend.routes.backups import router as backups_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.importacao import router as importacao_router

__all__ = [
    "atendimentos_router",
    "auth_router",
    "backups_router",
    "dashboard_router",
    "importacao_router",
]