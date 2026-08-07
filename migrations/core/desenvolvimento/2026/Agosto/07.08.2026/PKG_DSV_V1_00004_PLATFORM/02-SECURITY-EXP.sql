-- =====================================================
-- Migration: PKG_DSV_V1_00004_PLATFORM
-- Arquivo: 02-SECURITY-EXP.sql
-- Data: 07/08/2026
-- Banco: GH (trilha core)
-- Descrição: Expansão security.log_events — FK project_id → platform.projects.
-- =====================================================

-- =====================================================
-- OBJETIVO: Fechar FK de auditoria para projetos da obra
--           (arquivo separado — um schema por arquivo).
-- =====================================================

\o migration_PKG_DSV_V1_00004_PLATFORM_02_SECURITY_EXP_2026-08-07.log
SELECT 'MIGRATION INICIADA: PKG_DSV_V1_00004_PLATFORM / 02-SECURITY-EXP - ' || NOW() AS log_entry;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_schema = 'security'
          AND constraint_name = 'fk_log_events_project'
    ) THEN
        ALTER TABLE security.log_events
            ADD CONSTRAINT fk_log_events_project
            FOREIGN KEY (project_id) REFERENCES platform.projects(id) ON DELETE SET NULL;
    END IF;
END $$;

SELECT superadmin.log_migration_step('PKG_DSV_V1_00004_PLATFORM', 'INFO', 'FK security.log_events.project_id → platform.projects');

INSERT INTO superadmin.migrations (
    package_name,
    file_name,
    environment,
    notes,
    checksum
) VALUES (
    'PKG_DSV_V1_00004_PLATFORM',
    '02-SECURITY-EXP.sql',
    'desenvolvimento',
    'EXP security: FK log_events.project_id → platform.projects',
    encode(sha256('PKG_DSV_V1_00004_PLATFORM'::bytea), 'hex')
);

DO $$
DECLARE
    v_count INTEGER;
    v_success_count INTEGER := 0;
    v_total_checks INTEGER := 0;
BEGIN
    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM information_schema.table_constraints
    WHERE constraint_schema = 'security' AND constraint_name = 'fk_log_events_project';
    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE 'FK fk_log_events_project OK';
    ELSE
        RAISE NOTICE 'FALHA - FK fk_log_events_project';
    END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migrations
    WHERE package_name = 'PKG_DSV_V1_00004_PLATFORM' AND file_name = '02-SECURITY-EXP.sql';
    IF v_count > 0 THEN v_success_count := v_success_count + 1; RAISE NOTICE 'Historico OK';
    ELSE RAISE NOTICE 'FALHA - historico'; END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migration_logs ml
    JOIN superadmin.migrations m ON ml.migration_id = m.id
    WHERE m.package_name = 'PKG_DSV_V1_00004_PLATFORM';
    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE 'Logs registrados: % entradas', v_count;
    ELSE
        RAISE NOTICE 'FALHA - Nenhum log registrado na migration_logs';
    END IF;

    RAISE NOTICE 'RESUMO DA VALIDACAO: % / %', v_success_count, v_total_checks;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'ERRO CRITICO NA VALIDACAO: %', SQLERRM;
END $$;

SELECT 'MIGRATION CONCLUIDA: PKG_DSV_V1_00004_PLATFORM / 02-SECURITY-EXP - ' || NOW() AS log_entry;
\o

-- =====================================================
-- Status: Migration aplicada com sucesso
-- =====================================================
