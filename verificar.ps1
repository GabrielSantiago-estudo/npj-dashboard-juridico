# =============================================================================
# verificar.ps1 - Verificacao integral do estado do projeto NPJ
#
# Uso:
#   .\verificar.ps1              (verifica tudo, incluindo pytest)
#   .\verificar.ps1 -SkipPytest  (verificacao rapida, sem rodar testes)
#
# Se der erro de politica de execucao, rode antes:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# =============================================================================
param([switch]$SkipPytest)

$ErrorActionPreference = "Continue"
$script:falhas = 0
$script:verificacoes = 0

function OK([string]$msg) { $script:verificacoes++; Write-Host "  [OK]   $msg" -ForegroundColor Green }
function FALHA([string]$msg) { $script:falhas++; $script:verificacoes++; Write-Host "  [FAIL] $msg" -ForegroundColor Red }
function AVISO([string]$msg) { Write-Host "  [AVISO] $msg" -ForegroundColor Yellow }
function Titulo([string]$msg) { Write-Host ""; Write-Host "=== $msg ===" -ForegroundColor Cyan }

if (-not (Test-Path "backend") -or -not (Test-Path "frontend")) {
    Write-Host "ERRO: rode este script a partir da raiz NPJ_SISTEMA/" -ForegroundColor Red
    exit 2
}

# =============================================================================
Titulo "1. AMBIENTE"
# =============================================================================
try { $pyVer = python --version 2>&1; OK "Python: $pyVer" } catch { FALHA "Python nao encontrado no PATH" }
if (Test-Path ".venv\Scripts\Activate.ps1") { OK "Virtualenv .venv existe" } else { AVISO ".venv nao encontrado" }
if (Test-Path ".env") { OK ".env presente" } else { FALHA ".env ausente (copie de .env.example)" }
if (Test-Path "pytest.ini") { OK "pytest.ini presente" } else { FALHA "pytest.ini ausente" }
if (Test-Path "conftest.py") { OK "conftest.py presente" } else { FALHA "conftest.py ausente" }

# =============================================================================
Titulo "2. ESTRUTURA DE PASTAS"
# =============================================================================
$pastas = @(
    "backend", "backend\auth", "backend\database", "backend\models",
    "backend\routes", "backend\schemas", "backend\services",
    "frontend\templates", "frontend\templates\atendimentos",
    "frontend\templates\assistidos", "frontend\templates\importacao",
    "frontend\templates\admin",
    "frontend\static\css", "frontend\static\js", "frontend\static\img",
    "data", "data\backups", "imports", "imports\_staging", "exports", "logs",
    "powerbi", "tests", "docs", "scripts", "alembic", "alembic\versions"
)
foreach ($p in $pastas) {
    if (Test-Path $p) { OK "pasta: $p" } else { FALHA "pasta ausente: $p" }
}

# =============================================================================
Titulo "3. ARQUIVOS-CHAVE POR FASE"
# =============================================================================
function Verificar-Arquivo([string]$caminho, [int]$minBytes = 50) {
    if (-not (Test-Path $caminho)) { FALHA "ausente: $caminho"; return }
    $tam = (Get-Item $caminho).Length
    if ($caminho -match '__init__\.py$') { $minBytes = 10 }
    if ($tam -lt $minBytes) { FALHA "vazio/truncado ($tam bytes): $caminho" }
    else { OK "$caminho ($tam bytes)" }
}

Write-Host "`n  --- Fase 0: Fundacao ---" -ForegroundColor DarkCyan
$fase0 = @(
    "requirements.txt", ".env.example", ".gitignore",
    "backend\__init__.py", "backend\main.py", "backend\config.py",
    "backend\database\__init__.py", "backend\database\base.py", "backend\database\session.py",
    "backend\models\__init__.py", "backend\models\usuario.py", "backend\models\assistido.py",
    "backend\models\equipe.py", "backend\models\area_juridica.py",
    "backend\models\atendimento.py", "backend\models\audit_log.py", "backend\models\backup.py",
    "alembic.ini", "alembic\env.py", "alembic\script.py.mako",
    "scripts\__init__.py", "scripts\gerar_planilha_ficticia.py", "scripts\seed_banco.py",
    "imports\NPJ_Historico_FICTICIO_2006_2025.xlsx", "data\npj.db"
)
foreach ($a in $fase0) { Verificar-Arquivo $a }

Write-Host "`n  --- Fase 1: Auth + Auditoria ---" -ForegroundColor DarkCyan
$fase1 = @(
    "backend\templating.py",
    "backend\auth\__init__.py", "backend\auth\security.py",
    "backend\auth\session.py", "backend\auth\dependencies.py",
    "backend\services\__init__.py", "backend\services\audit.py",
    "backend\schemas\__init__.py", "backend\schemas\auth.py",
    "backend\routes\__init__.py", "backend\routes\auth.py",
    "frontend\templates\base.html", "frontend\templates\login.html",
    "frontend\static\css\npj.css",
    "tests\test_auth.py", "docs\FASE_1.md"
)
foreach ($a in $fase1) { Verificar-Arquivo $a }

Write-Host "`n  --- Fase 2a: Backend do CRUD ---" -ForegroundColor DarkCyan
$fase2a = @(
    "backend\schemas\common.py", "backend\schemas\atendimento.py",
    "backend\services\assistido.py", "backend\services\atendimento.py",
    "tests\test_atendimentos.py", "docs\FASE_2A.md"
)
foreach ($a in $fase2a) { Verificar-Arquivo $a }

Write-Host "`n  --- Fase 2b: Interface do CRUD ---" -ForegroundColor DarkCyan
$fase2b = @(
    "backend\routes\atendimentos.py",
    "frontend\templates\dashboard.html",
    "frontend\templates\atendimentos\lista.html",
    "frontend\templates\atendimentos\form.html",
    "frontend\templates\atendimentos\detalhe.html",
    "frontend\templates\assistidos\historico.html",
    "tests\test_atendimentos_http.py", "docs\FASE_2B.md"
)
foreach ($a in $fase2b) { Verificar-Arquivo $a }

Write-Host "`n  --- Fase 3: ETL + Excel Operacional ---" -ForegroundColor DarkCyan
$fase3 = @(
    "backend\schemas\etl.py",
    "backend\services\etl_import.py", "backend\services\excel_export.py",
    "backend\routes\importacao.py",
    "frontend\templates\importacao\upload.html",
    "frontend\templates\importacao\preview.html",
    "frontend\templates\importacao\relatorio.html",
    "tests\test_etl.py", "tests\test_importacao_http.py",
    "docs\FASE_3.md"
)
foreach ($a in $fase3) { Verificar-Arquivo $a }

Write-Host "`n  --- Fase 4: Dashboard Analitico ---" -ForegroundColor DarkCyan
$fase4 = @(
    "backend\schemas\dashboard.py",
    "backend\services\dashboard.py",
    "backend\routes\dashboard.py",
    "frontend\static\js\dashboard.js",
    "tests\test_dashboard.py",
    "docs\FASE_4.md"
)
foreach ($a in $fase4) { Verificar-Arquivo $a }

Write-Host "`n  --- Fase 5: Backup e Restauracao ---" -ForegroundColor DarkCyan
$fase5 = @(
    "backend\schemas\backup.py",
    "backend\services\backup.py",
    "backend\routes\backups.py",
    "frontend\templates\admin\backups.html",
    "tests\test_backup.py",
    "docs\FASE_5.md"
)
foreach ($a in $fase5) { Verificar-Arquivo $a }

Write-Host "`n  --- Fase 6: Cleanup Power BI ---" -ForegroundColor DarkCyan
$fase6 = @(
    "powerbi\README.md",
    "docs\FASE_6.md"
)
foreach ($a in $fase6) { Verificar-Arquivo $a }

$migracoes = Get-ChildItem "alembic\versions\*.py" -ErrorAction SilentlyContinue
if ($migracoes.Count -ge 1) { OK "migracao alembic: $($migracoes[0].Name)" }
else { FALHA "nenhuma migracao em alembic\versions" }

# =============================================================================
Titulo "4. SINTAXE PYTHON (compileall)"
# =============================================================================
$saida = python -m compileall -q backend scripts tests 2>&1
if ($LASTEXITCODE -eq 0) { OK "todos os .py compilam sem erro" }
else { FALHA "erro de sintaxe"; Write-Host $saida -ForegroundColor Red }

# =============================================================================
Titulo "5. IMPORTS CRITICOS"
# =============================================================================
$imports = @(
    "from backend.config import settings; print('ok')",
    "import backend.models; print('ok')",
    "from backend.database.session import SessionLocal, get_db; print('ok')",
    "from backend.auth.security import hash_senha, verificar_senha; print('ok')",
    "from backend.auth.dependencies import exigir_login, LoginRequired; print('ok')",
    "from backend.services import audit, assistido, atendimento, etl_import, excel_export; print('ok')",
    "from backend.services import dashboard, backup; print('ok')",
    "from backend.services.atendimento import criar, atualizar, arquivar, listar, AtendimentoError; print('ok')",
    "from backend.services.etl_import import processar_planilha, confirmar_importacao; print('ok')",
    "from backend.services.excel_export import gerar_excel_operacional, regenerar_apos_commit; print('ok')",
    "from backend.services.dashboard import calcular_dashboard; print('ok')",
    "from backend.services.backup import criar_backup, restaurar_backup, verificar_integridade; print('ok')",
    "from backend.schemas import AtendimentoFormulario, AtendimentoFiltros, LoginRequest, PreviewImportacao, RelatorioImportacao; print('ok')",
    "from backend.schemas import DashboardData, FiltrosDashboard; print('ok')",
    "from backend.schemas import BackupRead, RestauracaoResultado; print('ok')",
    "from backend.routes import auth_router, atendimentos_router, importacao_router, dashboard_router, backups_router; print('ok')",
    "from backend.main import app; print('ok')"
)
foreach ($imp in $imports) {
    $saida = python -c $imp 2>&1
    if ($LASTEXITCODE -eq 0) { OK "import: $($imp.Split(';')[0])" }
    else { FALHA "import falhou: $($imp.Split(';')[0])"; Write-Host "         $saida" -ForegroundColor Red }
}

# =============================================================================
Titulo "6. BANCO DE DADOS"
# =============================================================================
$tabelas = python -c "import backend.models; from backend.database.base import Base; print(','.join(sorted(Base.metadata.tables.keys())))" 2>&1
$esperadas = @("areas_juridicas","assistidos","atendimentos","audit_logs","backups","equipes","usuarios")
$ok = $true
foreach ($t in $esperadas) {
    if ($tabelas -notmatch $t) { $ok = $false; FALHA "tabela ausente: $t" }
}
if ($ok) { OK "7 tabelas registradas: $tabelas" }

$admin = python -c "from backend.database.session import SessionLocal; from backend.models import Usuario; from sqlalchemy import select; db=SessionLocal(); u=db.scalar(select(Usuario).where(Usuario.username=='admin')); print('admin OK' if u else 'SEM admin'); db.close()" 2>&1
if ($admin -match "admin OK") { OK "usuario admin existe" } else { FALHA "usuario admin ausente" }

$verify = python -c "from backend.database.session import SessionLocal; from backend.models import Usuario; from sqlalchemy import select; from argon2 import PasswordHasher; db=SessionLocal(); u=db.scalar(select(Usuario).where(Usuario.username=='admin')); print('hash OK' if u and PasswordHasher().verify(u.senha_hash,'admin123') else 'hash FALHA'); db.close()" 2>&1
if ($verify -match "hash OK") { OK "hash do admin verifica (admin123)" } else { FALHA "hash do admin NAO verifica" }

$contagens = python -c "from backend.database.session import SessionLocal; from backend.models import Atendimento, Assistido, AuditLog; from sqlalchemy import select, func; db=SessionLocal(); a=db.scalar(select(func.count()).select_from(Atendimento)); s=db.scalar(select(func.count()).select_from(Assistido)); l=db.scalar(select(func.count()).select_from(AuditLog)); print(f'{a}|{s}|{l}'); db.close()" 2>&1
Write-Host "         atendimentos/assistidos/audit_logs: $contagens"
$parts = $contagens.Split("|")
if ([int]$parts[0] -gt 0) { OK "ha atendimentos no banco" } else { FALHA "nenhum atendimento no banco" }
if ([int]$parts[1] -gt 0) { OK "ha assistidos no banco" } else { FALHA "nenhum assistido no banco" }

# =============================================================================
Titulo "7. PLANILHA FICTICIA E EXCEL OPERACIONAL"
# =============================================================================
$planilha = "imports\NPJ_Historico_FICTICIO_2006_2025.xlsx"
if (Test-Path $planilha) {
    $tam = (Get-Item $planilha).Length
    OK "planilha ficticia: $tam bytes"
    $linhas = python -c "import pandas as pd; df=pd.read_excel(r'$planilha', dtype=object); print(len(df))" 2>&1
    if ($linhas -match "^\d+") { OK "planilha tem $linhas linhas" }
    else { FALHA "nao foi possivel ler a planilha" }
} else { FALHA "planilha ficticia ausente" }

$excelOp = "data\NPJ_Operacional.xlsx"
if (Test-Path $excelOp) {
    $tam = (Get-Item $excelOp).Length
    OK "Excel operacional existe: $tam bytes"
    $abas = python -c "from openpyxl import load_workbook; wb=load_workbook(r'$excelOp'); print(','.join(wb.sheetnames))" 2>&1
    $esperadasAbas = @("Atendimentos","Assistidos","Equipes","Areas","Resumo")
    $okAbas = $true
    foreach ($a in $esperadasAbas) {
        if ($abas -notmatch $a) { $okAbas = $false; FALHA "aba ausente no Excel: $a" }
    }
    if ($okAbas) { OK "Excel tem as 5 abas esperadas" }
} else {
    AVISO "Excel operacional ainda nao foi gerado (rode /admin/excel/regenerar ou importe a planilha)"
}

# =============================================================================
Titulo "8. ALEMBIC (migracao aplicada)"
# =============================================================================
$alembicAtual = (alembic current 2>$null | Out-String).Trim()
if ($LASTEXITCODE -eq 0 -and $alembicAtual -match "[a-f0-9]{12}") { OK "migracao aplicada: $alembicAtual" }
else { FALHA "alembic current falhou ou sem migracao aplicada"; Write-Host "         $alembicAtual" -ForegroundColor Red }

# =============================================================================
Titulo "9. TESTES PYTEST"
# =============================================================================
if ($SkipPytest) { AVISO "pytest pulado (-SkipPytest)" }
else {
    Write-Host "  Rodando pytest (pode levar alguns segundos)..." -ForegroundColor Gray
    $saida = pytest tests/ -q 2>&1
    $txt = ($saida | Out-String)
    if ($LASTEXITCODE -eq 0) {
        if ($txt -match "(\d+) passed") { OK "pytest: $($Matches[1]) testes passaram" }
        else { OK "pytest retornou 0" }
    } else {
        FALHA "pytest retornou codigo $LASTEXITCODE"
        $saida | Where-Object { $_ -match "FAILED|ERROR" } | ForEach-Object { Write-Host "         $_" -ForegroundColor Red }
    }
}

# =============================================================================
Titulo "10. NOMENCLATURA NPJ (sem NAD/NID)"
# =============================================================================
$exts = @("*.py", "*.html", "*.css", "*.js", "*.md", "*.ini", "*.txt")
$suspeitos = @()
foreach ($ext in $exts) {
    $arquivos = Get-ChildItem -Path . -Filter $ext -Recurse -ErrorAction SilentlyContinue |
        Where-Object {
            $_.FullName -notmatch "\\\.venv\\" -and
            $_.FullName -notmatch "\\\.git\\" -and
            $_.FullName -notmatch "\\__pycache__\\" -and
            $_.FullName -notmatch "\\\.pytest_cache\\" -and
            $_.FullName -notmatch "\\alembic\\versions\\"
        }
    foreach ($arq in $arquivos) {
        $hits = Select-String -Path $arq.FullName -Pattern "\b(NAD|NID)\b" -ErrorAction SilentlyContinue
        if ($hits) { $suspeitos += $hits }
    }
}
if ($suspeitos.Count -eq 0) { OK "nenhuma ocorrencia de NAD/NID no codigo/docs" }
else {
    FALHA "$($suspeitos.Count) ocorrencia(s) de NAD/NID:"
    foreach ($s in $suspeitos) { Write-Host "         $($s.Path):$($s.LineNumber) -> $($s.Line.Trim())" -ForegroundColor Red }
}

# =============================================================================
Titulo "11. TEMPLATES SEM MENCAO A POWER BI (guarda de regressao)"
# =============================================================================
$templatesDir = "frontend\templates"
if (Test-Path $templatesDir) {
    $tplsComBi = @()
    $arqTpls = Get-ChildItem -Path $templatesDir -Filter "*.html" -Recurse -ErrorAction SilentlyContinue
    foreach ($tpl in $arqTpls) {
        $hits = Select-String -Path $tpl.FullName -Pattern "Power BI|PowerBI" -ErrorAction SilentlyContinue
        if ($hits) { $tplsComBi += $hits }
    }
    if ($tplsComBi.Count -eq 0) {
        OK "nenhum template em frontend/templates menciona Power BI"
    } else {
        FALHA "$($tplsComBi.Count) template(s) ainda mencionam Power BI:"
        foreach ($h in $tplsComBi) {
            Write-Host "         $($h.Path):$($h.LineNumber) -> $($h.Line.Trim())" -ForegroundColor Red
        }
    }
} else {
    AVISO "pasta frontend/templates nao encontrada"
}

# =============================================================================
Titulo "RESUMO"
# =============================================================================
Write-Host ""
if ($script:falhas -eq 0) {
    Write-Host "  TUDO OK - $($script:verificacoes) verificacoes passaram" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  $($script:falhas) FALHA(S) de $($script:verificacoes) verificacoes" -ForegroundColor Red
    exit 1
}