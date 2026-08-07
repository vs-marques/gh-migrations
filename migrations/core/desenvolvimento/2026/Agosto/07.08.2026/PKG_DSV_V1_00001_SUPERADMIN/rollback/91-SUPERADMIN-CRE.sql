-- =====================================================
-- Rollback: PKG_DSV_V1_00001_SUPERADMIN
-- Arquivo: rollback/91-SUPERADMIN-CRE.sql
-- Data: 07/08/2026
-- Descrição: Reversão de 01-SUPERADMIN-CRE.sql
-- =====================================================

-- ATENCAO: remove o historico de migrations. Use apenas em DSV limpo.

DROP SCHEMA IF EXISTS superadmin CASCADE;

-- Nao ha UPDATE em superadmin.migrations apos DROP SCHEMA CASCADE.
-- Se o schema ainda existir (rollback parcial), marcar status:

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_catalog.pg_namespace WHERE nspname = 'superadmin'
    ) THEN
        UPDATE superadmin.migrations
        SET
            status = 'rolled_back',
            updated_at = NOW(),
            notes = COALESCE(notes, '') || ' | ROLLBACK APLICADO'
        WHERE package_name = 'PKG_DSV_V1_00001_SUPERADMIN'
          AND file_name = '01-SUPERADMIN-CRE.sql'
          AND environment = 'desenvolvimento';
    END IF;
    RAISE NOTICE 'ROLLBACK PKG_DSV_V1_00001_SUPERADMIN aplicado';
END $$;

-- =====================================================
-- Status: Rollback aplicado com sucesso
-- =====================================================
