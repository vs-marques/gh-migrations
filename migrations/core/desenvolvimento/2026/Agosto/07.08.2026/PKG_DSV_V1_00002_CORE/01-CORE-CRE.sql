-- =====================================================
-- Migration: PKG_DSV_V1_00002_CORE
-- Arquivo: 01-CORE-CRE.sql
-- Data: 07/08/2026
-- Banco: GH (trilha core)
-- Descrição: Schema core — users, companies (PF/PJ), workspaces e config de IA.
-- =====================================================

-- =====================================================
-- OBJETIVO: Contas GhostWritter com suporte a PF e PJ,
--           workspaces (escritório/sala) e company_ai_config.
-- =====================================================

\o migration_PKG_DSV_V1_00002_CORE_2026-08-07.log
SELECT 'MIGRATION INICIADA: PKG_DSV_V1_00002_CORE - ' || NOW() AS log_entry;

CREATE SCHEMA IF NOT EXISTS core;
COMMENT ON SCHEMA core IS 'Contas GhostWritter: usuarios, empresas (PF/PJ), workspaces e config de IA';
SELECT superadmin.log_migration_step('PKG_DSV_V1_00002_CORE', 'INFO', 'Schema core criado ou ja existente');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'core' AND t.typname = 'user_status_enum') THEN
        CREATE TYPE core.user_status_enum AS ENUM ('ativo', 'inativo', 'pendente', 'cancelado', 'excluido');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'core' AND t.typname = 'account_kind_enum') THEN
        CREATE TYPE core.account_kind_enum AS ENUM ('pf', 'pj');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'core' AND t.typname = 'document_type_enum') THEN
        CREATE TYPE core.document_type_enum AS ENUM ('cpf', 'cnpj');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'core' AND t.typname = 'company_status_enum') THEN
        CREATE TYPE core.company_status_enum AS ENUM ('active', 'inactive', 'suspended');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'core' AND t.typname = 'workspace_kind_enum') THEN
        CREATE TYPE core.workspace_kind_enum AS ENUM ('personal', 'organization');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'core' AND t.typname = 'workspace_member_role_enum') THEN
        CREATE TYPE core.workspace_member_role_enum AS ENUM ('owner', 'admin', 'editor', 'reviewer', 'reader');
    END IF;
END $$;
SELECT superadmin.log_migration_step('PKG_DSV_V1_00002_CORE', 'INFO', 'ENUMs core criados');

CREATE OR REPLACE FUNCTION core.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- users
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    status core.user_status_enum NOT NULL DEFAULT 'ativo',
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    is_blocked BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    name VARCHAR(255),
    phone VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_users_username_not_empty CHECK (LENGTH(TRIM(username)) > 0),
    CONSTRAINT chk_users_email_valid CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT chk_users_password_not_empty CHECK (LENGTH(TRIM(hashed_password)) > 0)
);
COMMENT ON TABLE core.users IS 'Usuarios GhostWritter (pessoa fisica autenticavel)';

DROP TRIGGER IF EXISTS trigger_users_updated_at ON core.users;
CREATE TRIGGER trigger_users_updated_at
    BEFORE UPDATE ON core.users
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_users_username ON core.users (username);
CREATE INDEX IF NOT EXISTS idx_users_email ON core.users (email);
CREATE INDEX IF NOT EXISTS idx_users_status ON core.users (status);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON core.users (is_active);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00002_CORE', 'INFO', 'Tabela core.users criada');

-- -----------------------------------------------------------------------------
-- companies (PF / PJ)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_kind core.account_kind_enum NOT NULL,
    name VARCHAR(255) NOT NULL,
    legal_name VARCHAR(255),
    document VARCHAR(20),
    document_type core.document_type_enum,
    email VARCHAR(255),
    phone VARCHAR(20),
    status core.company_status_enum NOT NULL DEFAULT 'active',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    owner_user_id UUID,
    plan VARCHAR(50) NOT NULL DEFAULT 'free',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_companies_owner_user
        FOREIGN KEY (owner_user_id) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT chk_companies_name_not_empty CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_companies_document_kind_match CHECK (
        (account_kind = 'pf' AND (document_type IS NULL OR document_type = 'cpf'))
        OR (account_kind = 'pj' AND (document_type IS NULL OR document_type = 'cnpj'))
    ),
    CONSTRAINT chk_companies_plan_valid CHECK (plan IN ('free', 'pro', 'studio', 'enterprise'))
);
COMMENT ON TABLE core.companies IS 'Conta billing/tenant GhostWritter — PF (autor) ou PJ (escritorio/editora)';
COMMENT ON COLUMN core.companies.account_kind IS 'pf = pessoa fisica; pj = pessoa juridica';
COMMENT ON COLUMN core.companies.document IS 'CPF ou CNPJ normalizado (somente digitos)';

DROP TRIGGER IF EXISTS trigger_companies_updated_at ON core.companies;
CREATE TRIGGER trigger_companies_updated_at
    BEFORE UPDATE ON core.companies
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_document
    ON core.companies (document_type, document)
    WHERE document IS NOT NULL AND LENGTH(TRIM(document)) > 0;
CREATE INDEX IF NOT EXISTS idx_companies_account_kind ON core.companies (account_kind);
CREATE INDEX IF NOT EXISTS idx_companies_status ON core.companies (status);
CREATE INDEX IF NOT EXISTS idx_companies_owner_user_id ON core.companies (owner_user_id);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00002_CORE', 'INFO', 'Tabela core.companies (PF/PJ) criada');

-- -----------------------------------------------------------------------------
-- workspaces
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.workspaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    workspace_kind core.workspace_kind_enum NOT NULL DEFAULT 'personal',
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_workspaces_company
        FOREIGN KEY (company_id) REFERENCES core.companies(id) ON DELETE CASCADE,
    CONSTRAINT chk_workspaces_name_not_empty CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_workspaces_slug_format CHECK (slug ~* '^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'),
    CONSTRAINT uq_workspaces_company_slug UNIQUE (company_id, slug)
);
COMMENT ON TABLE core.workspaces IS 'Escritorio/sala de escrita — unidade colaborativa sob uma company';

DROP TRIGGER IF EXISTS trigger_workspaces_updated_at ON core.workspaces;
CREATE TRIGGER trigger_workspaces_updated_at
    BEFORE UPDATE ON core.workspaces
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_workspaces_company_id ON core.workspaces (company_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_kind ON core.workspaces (workspace_kind);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00002_CORE', 'INFO', 'Tabela core.workspaces criada');

-- -----------------------------------------------------------------------------
-- workspace_members
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.workspace_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role core.workspace_member_role_enum NOT NULL DEFAULT 'editor',
    invited_by UUID,
    joined_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_workspace_members_workspace
        FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_workspace_members_user
        FOREIGN KEY (user_id) REFERENCES core.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_workspace_members_invited_by
        FOREIGN KEY (invited_by) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT uq_workspace_members_workspace_user UNIQUE (workspace_id, user_id)
);
COMMENT ON TABLE core.workspace_members IS 'Membros do workspace com papel operacional';

DROP TRIGGER IF EXISTS trigger_workspace_members_updated_at ON core.workspace_members;
CREATE TRIGGER trigger_workspace_members_updated_at
    BEFORE UPDATE ON core.workspace_members
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_workspace_members_user_id ON core.workspace_members (user_id);
CREATE INDEX IF NOT EXISTS idx_workspace_members_role ON core.workspace_members (role);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00002_CORE', 'INFO', 'Tabela core.workspace_members criada');

-- -----------------------------------------------------------------------------
-- company_ai_config
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS core.company_ai_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    provider VARCHAR(50) NOT NULL DEFAULT 'openai',
    model_default VARCHAR(100),
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_company_ai_config_company
        FOREIGN KEY (company_id) REFERENCES core.companies(id) ON DELETE CASCADE,
    CONSTRAINT uq_company_ai_config_company UNIQUE (company_id)
);
COMMENT ON TABLE core.company_ai_config IS 'Configuracao de IA por company (tenant)';

DROP TRIGGER IF EXISTS trigger_company_ai_config_updated_at ON core.company_ai_config;
CREATE TRIGGER trigger_company_ai_config_updated_at
    BEFORE UPDATE ON core.company_ai_config
    FOR EACH ROW
    EXECUTE FUNCTION core.update_updated_at_column();

SELECT superadmin.log_migration_step('PKG_DSV_V1_00002_CORE', 'INFO', 'Tabela core.company_ai_config criada');

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
    'PKG_DSV_V1_00002_CORE',
    '01-CORE-CRE.sql',
    'desenvolvimento',
    'Schema core: users, companies PF/PJ, workspaces, workspace_members, company_ai_config',
    encode(sha256('PKG_DSV_V1_00002_CORE'::bytea), 'hex')
);

SELECT superadmin.log_migration_step('PKG_DSV_V1_00002_CORE', 'INFO', 'Registro no historico concluido');

-- =============================================================================
-- VALIDAÇÃO FINAL
-- =============================================================================
DO $$
DECLARE
    v_count INTEGER;
    v_success_count INTEGER := 0;
    v_total_checks INTEGER := 0;
    v_table TEXT;
BEGIN
    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM pg_catalog.pg_namespace WHERE nspname = 'core';
    IF v_count > 0 THEN v_success_count := v_success_count + 1; RAISE NOTICE 'Schema core OK';
    ELSE RAISE NOTICE 'FALHA - schema core'; END IF;

    FOREACH v_table IN ARRAY ARRAY['users', 'companies', 'workspaces', 'workspace_members', 'company_ai_config']
    LOOP
        v_total_checks := v_total_checks + 1;
        SELECT COUNT(*) INTO v_count FROM pg_tables WHERE schemaname = 'core' AND tablename = v_table;
        IF v_count > 0 THEN
            v_success_count := v_success_count + 1;
            RAISE NOTICE 'Tabela core.% OK', v_table;
        ELSE
            RAISE NOTICE 'FALHA - tabela core.%', v_table;
        END IF;
    END LOOP;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migrations
    WHERE package_name = 'PKG_DSV_V1_00002_CORE' AND file_name = '01-CORE-CRE.sql';
    IF v_count > 0 THEN v_success_count := v_success_count + 1; RAISE NOTICE 'Historico OK';
    ELSE RAISE NOTICE 'FALHA - historico'; END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migration_logs ml
    JOIN superadmin.migrations m ON ml.migration_id = m.id
    WHERE m.package_name = 'PKG_DSV_V1_00002_CORE';
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

SELECT 'MIGRATION CONCLUIDA: PKG_DSV_V1_00002_CORE - ' || NOW() AS log_entry;
\o

-- =====================================================
-- Status: Migration aplicada com sucesso
-- =====================================================
