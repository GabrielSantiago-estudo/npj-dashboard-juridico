# Fase 2b — Interface do CRUD de Atendimentos

## Entregue
- Dashboard HTML (substitui o JSON de placeholder da Fase 1).
- Listagem com busca textual e filtros combináveis (período, ano, semestre,
  área, situação, incluir arquivados) + paginação (20 por página).
- Formulário de criação/edição com validação visual (erros do Pydantic
  formatados como lista).
- Confirmação explícita em caso de duplicidade (protocolo igual ou
  mesmo assistido/data/área).
- Detalhe do atendimento com todos os campos, link para histórico do
  assistido, botão de arquivamento (exclusão lógica).
- Histórico do assistido (todos os atendimentos, incluindo arquivados).
- Navegação na topbar (Painel · Atendimentos · Novo).
- CSS: cards de estatística, tabela, formulário, badges de situação,
  paginação, alertas.
- Testes HTTP: proteção, listagem, criação, validações (CPF, data,
  arquivamento sem motivo), duplicidade, edição, arquivamento e histórico.

## Fluxo
1. `/dashboard` → cartões + últimos 5 atendimentos.
2. `/atendimentos` → lista com filtros + paginação.
3. `/atendimentos/novo` → formulário; POST cria ou pede confirmação
   em caso de duplicidade.
4. `/atendimentos/{id}` → detalhe + editar + arquivar.
5. `/assistidos/{id}/historico` → todos os atendimentos do assistido.

## Próximo
Fase 3 — ETL da planilha histórica e geração do Excel operacional.