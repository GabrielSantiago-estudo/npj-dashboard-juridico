"""Instância única de Jinja2Templates compartilhada pelas rotas."""
from __future__ import annotations

from pathlib import Path

from fastapi.templating import Jinja2Templates

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "frontend" / "templates"
STATIC_DIR = TEMPLATES_DIR.parent / "static"

TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "img").mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))