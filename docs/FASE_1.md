# Fase 1 - Autenticacao e Auditoria

## O que foi entregue
- Hash Argon2 (`argon2-cffi`) e verificacao de senha.
- Sessao via cookie assinado (Starlette `SessionMiddleware` + `itsdangerous`).
- Login/logout com auditoria em `audit_logs`.
- Protecao de rotas por dependency (`exigir_login`).
- Tela de login e layout base institucional (azul-marinho/branco/cinza).
- Redirect pos-login com protecao contra open redirect.
- Testes pytest: login valido, senha errada, usuario inexistente,
  rota protegida, fluxo completo login->dashboard->logout, open redirect.

## Fluxo
1. `GET /login` -> formulario.
2. `POST /login` (username, password, next) -> valida credencial.
   - Falha -> 401 + auditoria resultado="falha".
   - Sucesso -> sessao criada, `ultimo_login` atualizado, auditoria
     resultado="sucesso", redirect 303 para `next` (ou "/").
3. `GET /` e `/dashboard` exigem `exigir_login`.
   - Sem sessao -> `LoginRequired` -> handler redireciona para `/login?next=...`.
4. `POST /logout` -> limpa sessao, auditoria, redirect para `/login`.

## Seguranca
- Senha nunca e logada.
- Open redirect bloqueado em `_next_seguro`.
- Cookie `same_site=lax`; `https_only=False` apenas para HTTP local.
- Secret key vem do `.env` (nao hardcoded).

## Arquivos criados/alterados
- `backend/templating.py` (novo)
- `backend/auth/{__init__,security,session,dependencies}.py`
- `backend/services/{__init__,audit}.py`
- `backend/schemas/{__init__,auth}.py`
- `backend/routes/{__init__,auth}.py`
- `backend/main.py` (sessao + protecao + rotas)
- `frontend/templates/{base,login}.html`
- `frontend/static/css/npj.css`
- `tests/test_auth.py`
- `pytest.ini`, `conftest.py`

## Proximo
Fase 2 - CRUD de atendimentos.