# Fase 2a — Backend do CRUD de Atendimentos

## Entregue
- Schemas Pydantic: `AtendimentoFormulario`, `AtendimentoFiltros`.
- Validações: CPF, data (não futura, ≥ 2006), motivo obrigatório quando
  arquivado/indeferido, motivo limpo quando ativo.
- `assistido_service`: normalização, `buscar_ou_criar` idempotente, `historico`.
- `atendimento_service`: `criar`, `atualizar`, `arquivar`, `buscar_por_id`,
  `listar` (filtros + paginação), `detectar_duplicidade`.
- Testes pytest cobrindo criação, validações, duplicidade, atualização,
  arquivamento, filtros e histórico.

## Regras
- Duplicidade não bloqueia — retorna lista para o usuário confirmar.
- Exclusão é sempre lógica (`ativo=False`).
- Assistido deduplicado por nome normalizado + CPF.
- Área e equipe criadas on-the-fly se não existirem.

## Próximo
Fase 2b — rotas HTTP + templates + CSS + testes HTTP.