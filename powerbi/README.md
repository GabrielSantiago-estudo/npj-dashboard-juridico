# Pasta `powerbi/` — reservada

## Status

Pasta **vazia de propósito**. Faz parte da estrutura original do projeto
(prevista na Fase 0) e é mantida como **placeholder** para uso futuro,
caso a faculdade decida usar Power BI externamente.

## Decisão do projeto

O escopo do NPJ **NÃO inclui** integração com Power BI. Os dashboards
analíticos vivem **exclusivamente dentro do sistema** (Fase 4 — Chart.js).

Ver `docs/FASE_6.md` para o histórico completo dessa decisão.

## O que NÃO fazer

- Não é necessário instalar Power BI Desktop.
- Não há arquivo `.pbix` no escopo.
- O Excel operacional (`data/NPJ_Operacional.xlsx`) é gerado como
  **snapshot exportável** — pode ser aberto por qualquer ferramenta
  (Excel, LibreOffice, Power BI, Google Sheets), mas não é fonte
  oficial de dashboards do sistema.