-- =====================================================
-- Rollback: PKG_DSV_V1_00004_PLATFORM
-- Arquivo: rollback/92-SECURITY-EXP.sql
-- Data: 07/08/2026
-- Descrição: Reversão de 02-SECURITY-EXP.sql
-- =====================================================

ALTER TABLE IF EXISTS security.log_events
    DROP CONSTRAINT IF EXISTS fk_log_events_project;

UPDATE superadmin.migrations
SET
    status = 'rolled_back',
    updated_at = NOW(),
    notes = COALESCE(notes, '') || ' | ROLLBACK APLICADO'
WHERE package_name = 'PKG_DSV_V1_00004_PLATFORM'
  AND file_name = '02-SECURITY-EXP.sql'
  AND environment = 'desenvolvimento';

-- =====================================================
-- Status: Rollback aplicado com sucesso
-- =====================================================
