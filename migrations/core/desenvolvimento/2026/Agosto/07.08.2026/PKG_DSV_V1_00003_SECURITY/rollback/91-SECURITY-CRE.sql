-- =====================================================
-- Rollback: PKG_DSV_V1_00003_SECURITY
-- Arquivo: rollback/91-SECURITY-CRE.sql
-- Data: 07/08/2026
-- Descrição: Reversão de 01-SECURITY-CRE.sql
-- =====================================================

DROP FUNCTION IF EXISTS security.user_has_permission(UUID, VARCHAR, UUID);
DROP TABLE IF EXISTS security.log_events CASCADE;
DROP TABLE IF EXISTS security.login_audit CASCADE;
DROP TABLE IF EXISTS security.api_keys CASCADE;
DROP TABLE IF EXISTS security.sessions CASCADE;
DROP TABLE IF EXISTS security.user_roles CASCADE;
DROP TABLE IF EXISTS security.role_permissions CASCADE;
DROP TABLE IF EXISTS security.permissions CASCADE;
DROP TABLE IF EXISTS security.roles CASCADE;
DROP FUNCTION IF EXISTS security.update_updated_at_column();
DROP SCHEMA IF EXISTS security CASCADE;

UPDATE superadmin.migrations
SET
    status = 'rolled_back',
    updated_at = NOW(),
    notes = COALESCE(notes, '') || ' | ROLLBACK APLICADO'
WHERE package_name = 'PKG_DSV_V1_00003_SECURITY'
  AND file_name = '01-SECURITY-CRE.sql'
  AND environment = 'desenvolvimento';

-- =====================================================
-- Status: Rollback aplicado com sucesso
-- =====================================================
