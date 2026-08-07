# Migration template: PKG_DSV_V1_00001_BOOTSTRAP

## Informações Gerais
- **Pacote**: `PKG_DSV_V1_XXXXX_SCHEMA`
- **Arquivo**: `[NUMERO]-[SCHEMA]-[AÇÃO].sql`
- **Rollback**: `rollback/9[NUMERO]-[SCHEMA]-[AÇÃO].sql`
- **Ambiente**: desenvolvimento
- **Banco**: GH (trilha core)

## Objetivo
Template — copiar e preencher conforme `docs/MIGRATIONS_MASTER_REFERENCE.md`.

## Dependências
- Consultar ordem canônica: SUPERADMIN → CORE → SECURITY → PLATFORM

## Checklist
- [ ] Cabeçalho completo + spool `\o`
- [ ] Um arquivo = um schema
- [ ] INSERT em `superadmin.migrations` (package_name, file_name, environment, notes, checksum)
- [ ] `log_migration_step` com 3 parâmetros
- [ ] Validação final com JOIN em `migration_logs`
- [ ] Rollback atualiza `status = 'rolled_back'`
- [ ] README no formato da referência
