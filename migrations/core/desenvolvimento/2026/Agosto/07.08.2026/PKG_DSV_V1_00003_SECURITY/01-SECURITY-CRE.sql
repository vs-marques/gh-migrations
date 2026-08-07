-- =====================================================
-- Migration: PKG_DSV_V1_00003_SECURITY
-- Arquivo: 01-SECURITY-CRE.sql
-- Data: 07/08/2026
-- Banco: GH (trilha core)
-- Descrição: Schema security — RBAC, sessions, API keys e auditoria.
-- =====================================================

-- =====================================================
-- OBJETIVO: Controle de acesso RBAC GhostWritter + sessions,
--           api_keys, login_audit e log_events (traces).
-- =====================================================

\o migration_PKG_DSV_V1_00003_SECURITY_2026-08-07.log
SELECT 'MIGRATION INICIADA: PKG_DSV_V1_00003_SECURITY - ' || NOW() AS log_entry;

CREATE SCHEMA IF NOT EXISTS security;
COMMENT ON SCHEMA security IS 'RBAC, sessoes, API keys e auditoria GhostWritter';
SELECT superadmin.log_migration_step('PKG_DSV_V1_00003_SECURITY', 'INFO', 'Schema security criado ou ja existente');

CREATE OR REPLACE FUNCTION security.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS security.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(50) UNIQUE NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_roles_name_not_empty CHECK (LENGTH(TRIM(name)) > 0)
);
COMMENT ON TABLE security.roles IS 'Papeis RBAC do sistema';

CREATE TABLE IF NOT EXISTS security.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_permissions_name_not_empty CHECK (LENGTH(TRIM(name)) > 0)
);
COMMENT ON TABLE security.permissions IS 'Permissoes atomicas do sistema';

CREATE TABLE IF NOT EXISTS security.role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL,
    permission_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_role_permissions_role FOREIGN KEY (role_id) REFERENCES security.roles(id) ON DELETE CASCADE,
    CONSTRAINT fk_role_permissions_permission FOREIGN KEY (permission_id) REFERENCES security.permissions(id) ON DELETE CASCADE,
    CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS security.user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    role_id UUID NOT NULL,
    company_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id) REFERENCES core.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_role FOREIGN KEY (role_id) REFERENCES security.roles(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_company FOREIGN KEY (company_id) REFERENCES core.companies(id) ON DELETE CASCADE,
    CONSTRAINT uq_user_role_company UNIQUE (user_id, role_id, company_id)
);
COMMENT ON TABLE security.user_roles IS 'Papel do usuario no contexto de uma company';

CREATE INDEX IF NOT EXISTS idx_roles_name ON security.roles (name);
CREATE INDEX IF NOT EXISTS idx_permissions_name ON security.permissions (name);
CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON security.role_permissions (role_id);
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON security.role_permissions (permission_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON security.user_roles (user_id);
CREATE INDEX IF NOT EXISTS idx_user_roles_company_id ON security.user_roles (company_id);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00003_SECURITY', 'INFO', 'Tabelas RBAC criadas');

CREATE TABLE IF NOT EXISTS security.sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    company_id UUID,
    workspace_id UUID,
    refresh_token_hash VARCHAR(255) NOT NULL,
    user_agent TEXT,
    ip_address INET,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES core.users(id) ON DELETE CASCADE,
    CONSTRAINT fk_sessions_company FOREIGN KEY (company_id) REFERENCES core.companies(id) ON DELETE SET NULL,
    CONSTRAINT fk_sessions_workspace FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE SET NULL
);
COMMENT ON TABLE security.sessions IS 'Sessoes autenticadas (JWT refresh / device)';

DROP TRIGGER IF EXISTS trigger_sessions_updated_at ON security.sessions;
CREATE TRIGGER trigger_sessions_updated_at
    BEFORE UPDATE ON security.sessions
    FOR EACH ROW
    EXECUTE FUNCTION security.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON security.sessions (user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON security.sessions (expires_at);

CREATE TABLE IF NOT EXISTS security.api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(32) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    scopes JSONB NOT NULL DEFAULT '[]'::jsonb,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_api_keys_company FOREIGN KEY (company_id) REFERENCES core.companies(id) ON DELETE CASCADE,
    CONSTRAINT fk_api_keys_created_by FOREIGN KEY (created_by) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT uq_api_keys_key_hash UNIQUE (key_hash)
);
COMMENT ON TABLE security.api_keys IS 'API keys por company';

DROP TRIGGER IF EXISTS trigger_api_keys_updated_at ON security.api_keys;
CREATE TRIGGER trigger_api_keys_updated_at
    BEFORE UPDATE ON security.api_keys
    FOR EACH ROW
    EXECUTE FUNCTION security.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_api_keys_company_id ON security.api_keys (company_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON security.api_keys (key_prefix);

CREATE TABLE IF NOT EXISTS security.login_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    email_attempt VARCHAR(255),
    success BOOLEAN NOT NULL,
    failure_reason VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_login_audit_user FOREIGN KEY (user_id) REFERENCES core.users(id) ON DELETE SET NULL
);
COMMENT ON TABLE security.login_audit IS 'Auditoria de tentativas de login';
CREATE INDEX IF NOT EXISTS idx_login_audit_user_id ON security.login_audit (user_id);
CREATE INDEX IF NOT EXISTS idx_login_audit_created_at ON security.login_audit (created_at);

CREATE TABLE IF NOT EXISTS security.log_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL DEFAULT 'info',
    actor_user_id UUID,
    company_id UUID,
    workspace_id UUID,
    project_id UUID,
    message TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_log_events_actor FOREIGN KEY (actor_user_id) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT fk_log_events_company FOREIGN KEY (company_id) REFERENCES core.companies(id) ON DELETE SET NULL,
    CONSTRAINT fk_log_events_workspace FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE SET NULL,
    CONSTRAINT chk_log_events_severity CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical'))
);
COMMENT ON TABLE security.log_events IS 'Traces e eventos de auditoria da plataforma';
CREATE INDEX IF NOT EXISTS idx_log_events_event_type ON security.log_events (event_type);
CREATE INDEX IF NOT EXISTS idx_log_events_created_at ON security.log_events (created_at);
CREATE INDEX IF NOT EXISTS idx_log_events_company_id ON security.log_events (company_id);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00003_SECURITY', 'INFO', 'Tabelas sessions, api_keys, login_audit e log_events criadas');

-- Seed minimo RBAC
INSERT INTO security.roles (name, description) VALUES
    ('superadmin', 'Acesso total GhostWritter'),
    ('company_admin', 'Administrador da company (PF/PJ)'),
    ('company_member', 'Membro da company'),
    ('api_user', 'Acesso via API')
ON CONFLICT (name) DO NOTHING;

INSERT INTO security.permissions (name, description) VALUES
    ('manage_users', 'Gerenciar usuarios'),
    ('view_users', 'Visualizar usuarios'),
    ('manage_company', 'Gerenciar company'),
    ('view_company', 'Visualizar company'),
    ('manage_workspaces', 'Gerenciar workspaces'),
    ('view_workspaces', 'Visualizar workspaces'),
    ('manage_projects', 'Gerenciar projetos/obras'),
    ('view_projects', 'Visualizar projetos/obras'),
    ('use_ai', 'Usar copiloto de IA'),
    ('manage_api_keys', 'Gerenciar API keys'),
    ('view_audit', 'Visualizar auditoria')
ON CONFLICT (name) DO NOTHING;

INSERT INTO security.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM security.roles r
CROSS JOIN security.permissions p
WHERE r.name = 'superadmin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO security.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM security.roles r
JOIN security.permissions p ON p.name IN (
    'manage_users', 'view_users', 'manage_company', 'view_company',
    'manage_workspaces', 'view_workspaces', 'manage_projects', 'view_projects',
    'use_ai', 'manage_api_keys', 'view_audit'
)
WHERE r.name = 'company_admin'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO security.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM security.roles r
JOIN security.permissions p ON p.name IN (
    'view_users', 'view_company', 'view_workspaces', 'view_projects', 'use_ai'
)
WHERE r.name = 'company_member'
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO security.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM security.roles r
JOIN security.permissions p ON p.name IN ('view_projects', 'use_ai')
WHERE r.name = 'api_user'
ON CONFLICT (role_id, permission_id) DO NOTHING;

SELECT superadmin.log_migration_step('PKG_DSV_V1_00003_SECURITY', 'INFO', 'Seed RBAC inicial aplicado');

CREATE OR REPLACE FUNCTION security.user_has_permission(
    p_user_id UUID,
    p_permission_name VARCHAR(100),
    p_company_id UUID DEFAULT NULL
)
RETURNS BOOLEAN AS $$
DECLARE
    v_has_permission BOOLEAN := FALSE;
BEGIN
    SELECT EXISTS(
        SELECT 1
        FROM security.user_roles ur
        JOIN security.role_permissions rp ON ur.role_id = rp.role_id
        JOIN security.permissions p ON rp.permission_id = p.id
        WHERE ur.user_id = p_user_id
          AND p.name = p_permission_name
          AND (p_company_id IS NULL OR ur.company_id = p_company_id)
    ) INTO v_has_permission;
    RETURN v_has_permission;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

SELECT superadmin.log_migration_step('PKG_DSV_V1_00003_SECURITY', 'INFO', 'Funcao user_has_permission criada');

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
    'PKG_DSV_V1_00003_SECURITY',
    '01-SECURITY-CRE.sql',
    'desenvolvimento',
    'Schema security: RBAC, sessions, api_keys, login_audit, log_events + seed roles',
    encode(sha256('PKG_DSV_V1_00003_SECURITY'::bytea), 'hex')
);

SELECT superadmin.log_migration_step('PKG_DSV_V1_00003_SECURITY', 'INFO', 'Registro no historico concluido');

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
    SELECT COUNT(*) INTO v_count FROM pg_catalog.pg_namespace WHERE nspname = 'security';
    IF v_count > 0 THEN v_success_count := v_success_count + 1; RAISE NOTICE 'Schema security OK';
    ELSE RAISE NOTICE 'FALHA - schema security'; END IF;

    FOREACH v_table IN ARRAY ARRAY[
        'roles', 'permissions', 'role_permissions', 'user_roles',
        'sessions', 'api_keys', 'login_audit', 'log_events'
    ]
    LOOP
        v_total_checks := v_total_checks + 1;
        SELECT COUNT(*) INTO v_count FROM pg_tables WHERE schemaname = 'security' AND tablename = v_table;
        IF v_count > 0 THEN
            v_success_count := v_success_count + 1;
            RAISE NOTICE 'Tabela security.% OK', v_table;
        ELSE
            RAISE NOTICE 'FALHA - tabela security.%', v_table;
        END IF;
    END LOOP;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM security.roles;
    IF v_count >= 4 THEN v_success_count := v_success_count + 1; RAISE NOTICE 'Seed roles OK (% )', v_count;
    ELSE RAISE NOTICE 'FALHA - seed roles'; END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migrations
    WHERE package_name = 'PKG_DSV_V1_00003_SECURITY' AND file_name = '01-SECURITY-CRE.sql';
    IF v_count > 0 THEN v_success_count := v_success_count + 1; RAISE NOTICE 'Historico OK';
    ELSE RAISE NOTICE 'FALHA - historico'; END IF;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migration_logs ml
    JOIN superadmin.migrations m ON ml.migration_id = m.id
    WHERE m.package_name = 'PKG_DSV_V1_00003_SECURITY';
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

SELECT 'MIGRATION CONCLUIDA: PKG_DSV_V1_00003_SECURITY - ' || NOW() AS log_entry;
\o

-- =====================================================
-- Status: Migration aplicada com sucesso
-- =====================================================
