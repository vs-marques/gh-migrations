-- =====================================================
-- Migration: PKG_DSV_V1_00001_SUPERADMIN
-- Arquivo: 01-SUPERADMIN-CRE.sql
-- Data: 07/08/2026
-- Banco: GH (trilha core)
-- Descrição: Criação do schema superadmin e controle de migrations GhostWritter.
-- =====================================================

-- =====================================================
-- OBJETIVO: Criar o schema superadmin com tabelas migrations,
--           migration_logs, email_templates e função log_migration_step.
--           Pacote zero — executar antes de qualquer outro.
-- =====================================================

\o migration_PKG_DSV_V1_00001_SUPERADMIN_2026-08-07.log
SELECT 'MIGRATION INICIADA: PKG_DSV_V1_00001_SUPERADMIN - ' || NOW() AS log_entry;

-- Extensões em public (glue Postgres)
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE SCHEMA IF NOT EXISTS superadmin;
COMMENT ON SCHEMA superadmin IS 'Controle de migrations, templates de e-mail e operações de plataforma GhostWritter';

CREATE TABLE IF NOT EXISTS superadmin.migrations (
    id SERIAL PRIMARY KEY,
    package_name VARCHAR(100) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    environment VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    applied_at TIMESTAMP WITH TIME ZONE,
    applied_by VARCHAR(100),
    execution_time_ms INTEGER,
    checksum VARCHAR(64),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_migrations_package_file_env UNIQUE (package_name, file_name, environment)
);
COMMENT ON TABLE superadmin.migrations IS 'Controle de migrations aplicadas por ambiente';

CREATE TABLE IF NOT EXISTS superadmin.migration_logs (
    id SERIAL PRIMARY KEY,
    migration_id INTEGER NOT NULL,
    step_order INTEGER NOT NULL,
    step_description TEXT NOT NULL,
    log_level VARCHAR(20) NOT NULL DEFAULT 'INFO',
    log_message TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_migration_logs_migration
        FOREIGN KEY (migration_id) REFERENCES superadmin.migrations(id) ON DELETE CASCADE
);
COMMENT ON TABLE superadmin.migration_logs IS 'Logs detalhados de execução das migrations';

CREATE OR REPLACE FUNCTION superadmin.log_migration_step(
    p_package_name VARCHAR(100),
    p_log_level VARCHAR(20) DEFAULT 'INFO',
    p_message TEXT DEFAULT NULL
)
RETURNS VOID AS $$
DECLARE
    v_migration_id INTEGER;
BEGIN
    SELECT id INTO v_migration_id
    FROM superadmin.migrations
    WHERE package_name = p_package_name
    ORDER BY created_at DESC
    LIMIT 1;

    IF v_migration_id IS NULL THEN
        INSERT INTO superadmin.migrations (package_name, file_name, environment, status, notes)
        VALUES (p_package_name, 'TEMP_LOG', 'unknown', 'pending', 'Log temporário criado automaticamente')
        RETURNING id INTO v_migration_id;
    END IF;

    INSERT INTO superadmin.migration_logs (
        migration_id, step_order, step_description, log_level, log_message
    ) VALUES (
        v_migration_id,
        COALESCE((SELECT MAX(step_order) + 1 FROM superadmin.migration_logs WHERE migration_id = v_migration_id), 1),
        COALESCE(p_message, 'Step executado'),
        p_log_level,
        p_message
    );

    RAISE NOTICE '[%] %: %', p_log_level, p_package_name, p_message;
END;
$$ LANGUAGE plpgsql;
COMMENT ON FUNCTION superadmin.log_migration_step IS 'Registra steps de execução de migrations (3 parâmetros)';

CREATE OR REPLACE FUNCTION superadmin.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_migrations_updated_at ON superadmin.migrations;
CREATE TRIGGER trigger_migrations_updated_at
    BEFORE UPDATE ON superadmin.migrations
    FOR EACH ROW
    EXECUTE FUNCTION superadmin.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_migrations_package_name ON superadmin.migrations (package_name);
CREATE INDEX IF NOT EXISTS idx_migrations_environment ON superadmin.migrations (environment);
CREATE INDEX IF NOT EXISTS idx_migrations_status ON superadmin.migrations (status);
CREATE INDEX IF NOT EXISTS idx_migrations_applied_at ON superadmin.migrations (applied_at);
CREATE INDEX IF NOT EXISTS idx_migration_logs_migration_id ON superadmin.migration_logs (migration_id);
CREATE INDEX IF NOT EXISTS idx_migration_logs_timestamp ON superadmin.migration_logs (timestamp);

CREATE TABLE IF NOT EXISTS superadmin.email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT,
    locale VARCHAR(10) NOT NULL DEFAULT 'pt-BR',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_email_templates_code_locale UNIQUE (code, locale),
    CONSTRAINT chk_email_templates_code_not_empty CHECK (LENGTH(TRIM(code)) > 0)
);
COMMENT ON TABLE superadmin.email_templates IS 'Templates de e-mail transacionais GhostWritter';

DROP TRIGGER IF EXISTS trigger_email_templates_updated_at ON superadmin.email_templates;
CREATE TRIGGER trigger_email_templates_updated_at
    BEFORE UPDATE ON superadmin.email_templates
    FOR EACH ROW
    EXECUTE FUNCTION superadmin.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_email_templates_code ON superadmin.email_templates (code);
CREATE INDEX IF NOT EXISTS idx_email_templates_is_active ON superadmin.email_templates (is_active);

-- =============================================================================
-- REGISTRO OBRIGATÓRIO NA TABELA DE HISTÓRICO
-- =============================================================================
INSERT INTO superadmin.migrations (
    package_name,
    file_name,
    environment,
    notes,
    checksum
) VALUES (
    'PKG_DSV_V1_00001_SUPERADMIN',
    '01-SUPERADMIN-CRE.sql',
    'desenvolvimento',
    'Criação do schema superadmin: migrations, migration_logs, email_templates e log_migration_step',
    encode(sha256('PKG_DSV_V1_00001_SUPERADMIN'::bytea), 'hex')
);

SELECT superadmin.log_migration_step('PKG_DSV_V1_00001_SUPERADMIN', 'INFO', 'Extensões pgcrypto e uuid-ossp habilitadas');
SELECT superadmin.log_migration_step('PKG_DSV_V1_00001_SUPERADMIN', 'INFO', 'Schema superadmin criado');
SELECT superadmin.log_migration_step('PKG_DSV_V1_00001_SUPERADMIN', 'INFO', 'Tabelas migrations, migration_logs e email_templates criadas');
SELECT superadmin.log_migration_step('PKG_DSV_V1_00001_SUPERADMIN', 'INFO', 'Função log_migration_step e triggers criados');

-- =============================================================================
-- VALIDAÇÃO FINAL
-- =============================================================================
DO $$
DECLARE
    v_count INTEGER;
    v_success_count INTEGER := 0;
    v_total_checks INTEGER := 0;
BEGIN
    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM pg_catalog.pg_namespace WHERE nspname = 'superadmin';
    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE 'Schema superadmin existe';
    ELSE
        RAISE NOTICE 'FALHA - Schema superadmin nao existe';
    END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM pg_tables WHERE schemaname = 'superadmin' AND tablename = 'migrations';
    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE 'Tabela superadmin.migrations existe';
    ELSE
        RAISE NOTICE 'FALHA - Tabela migrations nao existe';
    END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM pg_tables WHERE schemaname = 'superadmin' AND tablename = 'migration_logs';
    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE 'Tabela superadmin.migration_logs existe';
    ELSE
        RAISE NOTICE 'FALHA - Tabela migration_logs nao existe';
    END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM pg_tables WHERE schemaname = 'superadmin' AND tablename = 'email_templates';
    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE 'Tabela superadmin.email_templates existe';
    ELSE
        RAISE NOTICE 'FALHA - Tabela email_templates nao existe';
    END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM pg_proc p
    JOIN pg_namespace n ON p.pronamespace = n.oid
    WHERE n.nspname = 'superadmin' AND p.proname = 'log_migration_step';
    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE 'Funcao log_migration_step existe';
    ELSE
        RAISE NOTICE 'FALHA - Funcao log_migration_step nao existe';
    END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migrations
    WHERE package_name = 'PKG_DSV_V1_00001_SUPERADMIN'
      AND file_name = '01-SUPERADMIN-CRE.sql';
    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE 'Registro no historico de migrations OK';
    ELSE
        RAISE NOTICE 'FALHA - Migration nao registrada no historico';
    END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migration_logs ml
    JOIN superadmin.migrations m ON ml.migration_id = m.id
    WHERE m.package_name = 'PKG_DSV_V1_00001_SUPERADMIN';
    IF v_count > 0 THEN
        v_success_count := v_success_count + 1;
        RAISE NOTICE 'Logs registrados: % entradas', v_count;
    ELSE
        RAISE NOTICE 'FALHA - Nenhum log registrado na migration_logs';
    END IF;

    RAISE NOTICE 'RESUMO DA VALIDACAO: % / %', v_success_count, v_total_checks;
    IF v_success_count = v_total_checks THEN
        RAISE NOTICE 'VALIDACAO CONCLUIDA COM SUCESSO TOTAL';
    ELSE
        RAISE NOTICE 'VALIDACAO CONCLUIDA COM FALHAS';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'ERRO CRITICO NA VALIDACAO: %', SQLERRM;
END $$;

SELECT 'MIGRATION CONCLUIDA: PKG_DSV_V1_00001_SUPERADMIN - ' || NOW() AS log_entry;
\o

-- =====================================================
-- Status: Migration aplicada com sucesso
-- =====================================================
