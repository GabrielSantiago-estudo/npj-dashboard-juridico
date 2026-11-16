# Fase 3 — ETL + Excel Operacional (completa)

## Entregue

### Núcleo (3a)
- Serviço de ETL (`etl_import.py`): extração, transformação, carga transacional
- Serviço de exportação (`excel_export.py`): `NPJ_Operacional.xlsx` com 5 abas + ListObjects
- Rotas: upload → preview → confirm → relatório
- Rotas de Excel: regenerar (manual) e download
- 12 testes unitários

### Integração (3b)
- Link "Importar" na navbar
- `regenerar_apos_commit()` chamado após criar/editar/arquivar
- Card "Excel operacional" no dashboard (Regenerar + Baixar)
- 6 testes HTTP do fluxo completo
- `.gitignore` ignora `data/*.xlsx` e `imports/_staging/`
- `verificar.ps1` cobre a Fase 3

## Sincronização automática
- Após importação → Excel regenerado
- Após cadastro (CRUD) → Excel regenerado
- Após edição → Excel regenerado
- Após arquivamento → Excel regenerado
- Botão manual no dashboard (fallback)

## Onde ficam os arquivos
- Planilha histórica (input): `imports/NPJ_Historico_FICTICIO_2006_2025.xlsx`
- Staging temporário: `imports/_staging/<token>.xlsx` + `.json` (não versionado)
- Excel operacional (output): `data/NPJ_Operacional.xlsx` (não versionado)

## Nota sobre Power BI
O documento original previa integração com Power BI (Fase 6). Por decisão do projeto,
o Power BI foi **removido do escopo**. O Excel operacional continua sendo gerado,
mas passa a ser classificado como **snapshot exportável** (para auditoria externa
e backup histórico), não como fonte para Power BI. A limpeza de menções ao
Power BI ocorrerá na **Fase 6 (cleanup)**.

## Próximo
Fase 4 — dashboard analítico interno com Chart.js (dados em tempo real)