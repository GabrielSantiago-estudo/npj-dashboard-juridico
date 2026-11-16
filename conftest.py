"""Garante que a raiz do projeto esteja no sys.path ao rodar pytest.

Funciona em conjunto com pytest.ini (pythonpath = .), mas também
resolve o caso de invocações parciais (pytest tests/test_x.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))