# Fase 5 — Backup e Restauração

## Entregue
- Serviço `backup.py` com API oficial `sqlite3.Connection.backup()`
- Verificação automática de integridade (`PRAGMA integrity_check`) em todo backup
- Restauração protegida (cria backup `pre_restore` antes de sobrescrever)
- Thread de backup automático configurável via `.env`
- Tela `/admin/backups` com listagem, download e restauração
- Rotas HTTP: criar, restaurar, download
- Auditoria de todas as operações de backup
- 11 testes automatizados

## Fluxo de criação
1. `POST /admin/backups/criar`
2. `sqlite3.Connection.backup()` produz snapshot consistente
3. Verificação de integridade via `PRAGMA integrity_check`
4. Registro em `backups` (id, caminho, tamanho, tipo, integridade_ok)
5. Audit log

## Fluxo de restauração
1. `POST /admin/backups/{id}/restaurar`
2. Validação: arquivo existe + integridade OK
3. **Cria backup `pre_restore` do estado atual** (rollback possível)
4. Restaura via `sqlite3.Connection.backup()` (bidirecional)
5. Audit log registra o `pre_restore_id`

## Backup automático
- Configurável em `.env`:
  - `BACKUP_AUTO_ENABLED=true`
  - `BACKUP_AUTO_INTERVAL_HOURS=24` (padrão)
- Thread daemon iniciada no `lifespan` da aplicação
- Para na parada da aplicação

## Localização dos arquivos
- `data/backups/npj_backup_YYYYMMDD_HHMMSS_<tipo>.db`
- Tipos: `manual`, `automatico`, `pre_restore`

## O que NÃO fazer
- Não copiar o `npj.db` com aplicação rodando (usar o botão de backup)
- Não compartilhar backups em pasta de rede sem proteção
- Não apagar backups de `pre_restore` imediatamente após restauração

## Próximo
Fase 6 — Cleanup Power BI (remoção de menções e estruturas)