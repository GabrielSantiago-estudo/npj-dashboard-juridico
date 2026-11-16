# Fase 6 — Cleanup Power BI

## Motivo

A decisão de projeto foi **remover o Power BI do escopo**. Os dashboards
analíticos vivem exclusivamente dentro do sistema (Fase 4, Chart.js), sem
dependência externa.

Esta fase faz a limpeza final das menções, sem alterar funcionalidade.

## Princípios

1. **Não apagar docs históricos** — `FASE_3.md`, `FASE_4.md`, `FASE_5.md`
   permanecem como registro fiel do que foi decidido na época.
2. **Não remover pastas** — `powerbi/` continua existindo (vazia) como
   placeholder, documentada em `powerbi/README.md`.
3. **Não tocar em código** — rotas, services, models, testes e migrations
   ficam intactos.
4. **Substituição apenas do que é visível ao usuário** — templates HTML.

## O que foi alterado

| Arquivo | Antes | Depois |
|---|---|---|
| `frontend/templates/importacao/relatorio.html` | "Use-o como fonte no Power BI." | "Use-o como snapshot exportável." |
| `README.md` | Linha "Power BI Desktop (para a Fase 6)" | Removida |
| `powerbi/README.md` | (não existia) | Placeholder documentando a decisão |
| `verificar.ps1` | — | Nova seção 11 (guarda de regressão) |

## O que NÃO foi alterado (por design)

- `docs/FASE_3.md` — mantém a nota "Power BI removido do escopo" como
  registro histórico da decisão.
- `docs/FASE_4.md` — idem.
- `docs/FASE_5.md` — menciona "Próximo: Fase 6 — Cleanup Power BI" como
  registro do roadmap da época.
- Pasta `powerbi/` — mantida vazia (placeholder).
- Qualquer arquivo `.py` — zero mudança funcional.
- `.gitignore` — já não tinha referência (verificado no diagnóstico).

## Estado final do sistema

| Camada | Status |
|---|---|
| Banco (7 tabelas) | Inalterado |
| Autenticação + auditoria | Inalterado |
| CRUD de atendimentos | Inalterado |
| ETL + Excel operacional | Inalterado |
| Dashboard analítico (Chart.js) | Inalterado |
| Backup e restauração | Inalterado |

**Nenhum teste foi quebrado. Nenhuma funcionalidade foi removida.**

## Regra de ouro daqui pra frente

Se em algum momento surgir necessidade de Power BI **institucional**
(a faculdade decidir), o caminho é:

1. Criar `powerbi/NPJ_Dashboard.pbix`
2. Conectar ao Excel operacional (`data/NPJ_Operacional.xlsx`)
3. Seguir as boas práticas de BI

O sistema está preparado — apenas não faz parte do escopo entregue.