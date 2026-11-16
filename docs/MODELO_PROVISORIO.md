# Modelo de Dados — Provisório

> **Status:** provisório. Baseado nas 13 colunas informadas pelo NPJ,
> sem acesso à planilha histórica real. Será revisado quando ela chegar.

## Mapeamento das colunas originais

| Coluna original | Campo | Observação |
|---|---|---|
| DATA | data_atendimento | Normalizar formatos no ETL |
| NUMERO DE PROTOCOLO | numero_protocolo | Chave natural; duplicidade sinalizada |
| CLIENTE | assistido_id + cliente_texto_original | Entidade separada |
| EQUIPE | equipe_id + equipe_texto_original | Texto livre no protótipo |
| SITUACAO | situacao | Enum provisório |
| MOTIVO DO ARQUIVAMENTO/INDEFERIMENTO | motivo_arquivamento | — |
| PROCESSO | numero_processo | Pode ser vazio |
| VARA | vara | Texto livre |
| AREA | area_juridica_id + area_texto_original | Lista padronizada |
| ASSUNTO | assunto | Texto livre |
| ENDERECO DAS PASTAS | endereco_pasta | Localização física |
| PARTE CONTRARIADA | parte_contrariada | Dado de terceiro (LGPD) |

## Decisões provisórias
- Situação: Ativo, Arquivado, Indeferido, Concluído (validar).
- Equipe: texto livre; pode virar FK no futuro.
- Exclusão: sempre lógica (ativo=False).