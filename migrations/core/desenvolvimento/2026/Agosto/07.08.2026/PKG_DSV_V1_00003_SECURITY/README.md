# Migration: PKG_DSV_V1_00003_SECURITY

## Informações Gerais
- **Pacote**: `PKG_DSV_V1_00003_SECURITY`
- **Arquivo**: `01-SECURITY-CRE.sql`
- **Rollback**: `rollback/91-SECURITY-CRE.sql`
- **Data**: 07/08/2026
- **Ambiente**: Desenvolvimento
- **Banco**: GH (trilha core)
- **Versão**: 1.0.0

## Objetivo
Criar o schema `security` com RBAC, sessões, API keys e auditoria mínima do GhostWritter.

## Problema Identificado
- Necessidade de autorização por company (PF/PJ) antes do domínio da obra
- Sessions e API keys fora do schema `core`

## Solução Implementada
- RBAC: `roles`, `permissions`, `role_permissions`, `user_roles`
- `sessions`, `api_keys`, `login_audit`, `log_events`
- Seed de roles/permissions e função `user_has_permission`

## Scripts Executados
- `01-SECURITY-CRE.sql`
- `rollback/91-SECURITY-CRE.sql`

## Dependências
- `PKG_DSV_V1_00001_SUPERADMIN`
- `PKG_DSV_V1_00002_CORE` (`core.users`, `core.companies`, `core.workspaces`)

## Observações Importantes
- `user_roles.company_id` ancora o papel no tenant PF/PJ
- `log_events.project_id` é UUID sem FK neste pacote (obra criada em PLATFORM)
- Seguir `docs/MIGRATIONS_MASTER_REFERENCE.md`

## Status
- Pronto para deploy em desenvolvimento

## Próximos Passos
- Aplicar `PKG_DSV_V1_00004_PLATFORM`
