# Migration: PKG_DSV_V1_00002_CORE

## Informações Gerais
- **Pacote**: `PKG_DSV_V1_00002_CORE`
- **Arquivo**: `01-CORE-CRE.sql`
- **Rollback**: `rollback/91-CORE-CRE.sql`
- **Data**: 07/08/2026
- **Ambiente**: Desenvolvimento
- **Banco**: GH (trilha core)
- **Versão**: 1.0.0

## Objetivo
Criar o schema `core` com contas PF/PJ (`companies`), usuários, workspaces (escritório) e configuração de IA por tenant.

## Problema Identificado
- Necessidade de tenant leve com suporte a pessoa física e jurídica desde o bootstrap
- Workspace colaborativo separado da obra (`platform.projects`)

## Solução Implementada
- ENUMs: `account_kind` (pf/pj), `document_type` (cpf/cnpj), status, roles de membro
- Tabelas: `users`, `companies`, `workspaces`, `workspace_members`, `company_ai_config`
- FKs, índices e triggers `updated_at`

## Scripts Executados
- `01-CORE-CRE.sql`
- `rollback/91-CORE-CRE.sql`

## Dependências
- `PKG_DSV_V1_00001_SUPERADMIN`

## Observações Importantes
- PF: `account_kind = pf`, documento CPF opcional no MVP
- PJ: `account_kind = pj`, documento CNPJ opcional no MVP
- Obra fica em `platform` (próximo pacote SECURITY, depois PLATFORM)
- Seguir `docs/MIGRATIONS_MASTER_REFERENCE.md`

## Status
- Pronto para deploy em desenvolvimento

## Próximos Passos
- Aplicar `PKG_DSV_V1_00003_SECURITY`
