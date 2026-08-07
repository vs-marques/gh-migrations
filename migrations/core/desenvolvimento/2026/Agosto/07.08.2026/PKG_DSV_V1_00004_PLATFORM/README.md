# Migration: PKG_DSV_V1_00004_PLATFORM

## Informações Gerais
- **Pacote**: `PKG_DSV_V1_00004_PLATFORM`
- **Arquivos**: `01-PLATFORM-CRE.sql`, `02-SECURITY-EXP.sql`
- **Rollbacks**: `rollback/91-PLATFORM-CRE.sql`, `rollback/92-SECURITY-EXP.sql`
- **Data**: 07/08/2026
- **Ambiente**: Desenvolvimento
- **Banco**: GH (trilha core)
- **Versão**: 1.0.0

## Objetivo
Criar o schema `platform` com a estrutura inicial da obra GhostWritter: projeto, catálogo, faíscas, narrativa, mural e feed.

## Problema Identificado
- Domínio literário ainda sem tabelas canônicas
- Necessidade de grafo (entidades/mural) + feed de consequências

## Solução Implementada
| Grupo | Tabelas |
|-------|---------|
| Projeto | `projects`, `project_members` |
| Catálogo | `entities`, `entity_relations` |
| Faísca | `sparks`, `spark_mentions`, `spark_entity_links` |
| Narrativa | `chapters`, `chapter_revisions`, `spark_chapter_links` |
| Mural | `mural_nodes`, `mural_edges` |
| Feed | `feed_events` |

FK de auditoria em arquivo separado (`02-SECURITY-EXP.sql`): `security.log_events.project_id` → `platform.projects`.

## Scripts Executados
- `01-PLATFORM-CRE.sql`
- `02-SECURITY-EXP.sql`
- `rollback/92-SECURITY-EXP.sql` / `rollback/91-PLATFORM-CRE.sql`

## Dependências
- `PKG_DSV_V1_00001_SUPERADMIN`
- `PKG_DSV_V1_00002_CORE`
- `PKG_DSV_V1_00003_SECURITY`

## Observações Importantes
- Unidade canônica: `platform.projects` sob `core.workspaces`
- Um arquivo = um schema (`01` = platform, `02` = security EXP)
- Seguir `docs/MIGRATIONS_MASTER_REFERENCE.md`

## Status
- Pronto para deploy em desenvolvimento

## Próximos Passos
- Aplicar a sequência 00001→00004 em DSV
- Espelhar HMG/PRD quando houver ambiente
