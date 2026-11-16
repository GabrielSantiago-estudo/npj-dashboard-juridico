"""Ponto de entrada da aplicação NPJ."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from backend.auth.dependencies import LoginRequired, exigir_login
from backend.config import settings
import backend.models  # noqa: F401
from backend.models import Usuario
from backend.routes import (
    atendimentos_router,
    auth_router,
    backups_router,
    dashboard_router,
    importacao_router,
)
from backend.services import backup as backup_svc
from backend.templating import STATIC_DIR


@asynccontextmanager
async def lifespan(app: FastAPI):
    backup_svc.iniciar_backup_automatico()
    yield
    backup_svc.parar_backup_automatico()


app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    lifespan=lifespan,
)


class NoCacheStaticFiles(StaticFiles):
    def file_response(self, *args, **kwargs):
        resp = super().file_response(*args, **kwargs)
        resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        resp.headers["Pragma"] = "no-cache"
        resp.headers["Expires"] = "0"
        return resp


app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="npj_session",
    max_age=settings.session_max_age_seconds,
    same_site="lax",
    https_only=False,
)
app.mount("/static", NoCacheStaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(atendimentos_router)
app.include_router(importacao_router)
app.include_router(backups_router)


@app.exception_handler(LoginRequired)
async def _handler_login_required(request: Request, exc: LoginRequired):
    destino = exc.next_url or "/"
    return RedirectResponse(url=f"/login?next={destino}", status_code=303)


@app.get("/health", tags=["infra"])
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}


@app.get("/")
def raiz(usuario: Annotated[Usuario, Depends(exigir_login)]):
    return RedirectResponse(url="/dashboard", status_code=303)