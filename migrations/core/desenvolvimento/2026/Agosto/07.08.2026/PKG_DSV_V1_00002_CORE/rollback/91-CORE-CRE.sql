-- =====================================================
-- Rollback: PKG_DSV_V1_00002_CORE
-- Arquivo: rollback/91-CORE-CRE.sql
-- Data: 07/08/2026
-- Descrição: Reversão de 01-CORE-CRE.sql
-- =====================================================

DROP TABLE IF EXISTS core.company_ai_config CASCADE;
DROP TABLE IF EXISTS core.workspace_members CASCADE;
DROP TABLE IF EXISTS core.workspaces CASCADE;
DROP TABLE IF EXISTS core.companies CASCADE;
DROP TABLE IF EXISTS core.users CASCADE;

DROP FUNCTION IF EXISTS core.update_updated_at_column();

DROP TYPE IF EXISTS core.workspace_member_role_enum;
DROP TYPE IF EXISTS core.workspace_kind_enum;
DROP TYPE IF EXISTS core.company_status_enum;
DROP TYPE IF EXISTS core.document_type_enum;
DROP TYPE IF EXISTS core.account_kind_enum;
DROP TYPE IF EXISTS core.user_status_enum;

DROP SCHEMA IF EXISTS core CASCADE;

UPDATE superadmin.migrations
SET
    status = 'rolled_back',
    updated_at = NOW(),
    notes = COALESCE(notes, '') || ' | ROLLBACK APLICADO'
WHERE package_name = 'PKG_DSV_V1_00002_CORE'
  AND file_name = '01-CORE-CRE.sql'
  AND environment = 'desenvolvimento';

-- =====================================================
-- Status: Rollback aplicado com sucesso
-- =====================================================
