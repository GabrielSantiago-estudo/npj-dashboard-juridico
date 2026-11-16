# NPJ — Sistema de Gestão

Protótipo local do sistema do **Núcleo de Prática Jurídica (NPJ)**.

## Requisitos
- Windows 10/11
- Python 3.11+

## Instalação
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python -m scripts.gerar_planilha_ficticia
python -m scripts.seed_banco
uvicorn backend.main:app --reload