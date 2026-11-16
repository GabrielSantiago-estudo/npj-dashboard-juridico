# Fase 4 — Dashboard Analítico com Chart.js

## Entregue
- API `GET /api/dashboard/dados` que calcula indicadores direto do banco
- Serviço `dashboard.py` com queries (por ano, mês, área, equipe, situação)
- Filtros: ano, semestre, área jurídica (combináveis)
- Página `/dashboard` redesenhada com:
  - 3 KPIs (total ativo, assistidos únicos, média/mês)
  - 5 gráficos Chart.js:
    - Linha: evolução histórica por ano
    - Barras: atendimentos por mês (Jan–Dez)
    - Barras horizontais: por área jurídica
    - Barras horizontais: produtividade por equipe
    - Doughnut: situação dos atendimentos
- Filtros recalculam todos os gráficos via fetch + Chart.js
- 9 testes automatizados

## Cálculos
- `media_por_mes` = total_ativo / meses_distintos_com_dado_no_filtro
- `por_ano` preenche anos sem dado com 0 (linha contínua)
- `por_mes` sempre 12 labels (Jan–Dez), zeros quando não há dado

## Decisão sobre Power BI
- Power BI removido do escopo (decisão do projeto)
- Dashboards vivem apenas no sistema (HTML + Chart.js)
- `data/NPJ_Operacional.xlsx` continua sendo gerado como **snapshot exportável**
- Limpeza final de menções ao Power BI: Fase 6 (cleanup)

## Próximo
Fase 5 — Backup e restauração