-- =====================================================
-- Migration: PKG_DSV_V1_00004_PLATFORM
-- Arquivo: 01-PLATFORM-CRE.sql
-- Data: 07/08/2026
-- Banco: GH (trilha core)
-- Descrição: Schema platform — obra: projeto, catálogo, faísca, narrativa, mural, feed.
-- =====================================================

-- =====================================================
-- OBJETIVO: Domínio literário GhostWritter em platform.*
-- =====================================================

\o migration_PKG_DSV_V1_00004_PLATFORM_2026-08-07.log
SELECT 'MIGRATION INICIADA: PKG_DSV_V1_00004_PLATFORM - ' || NOW() AS log_entry;

CREATE SCHEMA IF NOT EXISTS platform;
COMMENT ON SCHEMA platform IS 'Dominio da obra: projetos, catalogo, faiscas, narrativa, mural e feed';
SELECT superadmin.log_migration_step('PKG_DSV_V1_00004_PLATFORM', 'INFO', 'Schema platform criado ou ja existente');

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'platform' AND t.typname = 'project_status_enum') THEN
        CREATE TYPE platform.project_status_enum AS ENUM ('draft', 'active', 'archived', 'published');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'platform' AND t.typname = 'project_member_role_enum') THEN
        CREATE TYPE platform.project_member_role_enum AS ENUM ('owner', 'editor', 'reviewer', 'reader');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'platform' AND t.typname = 'entity_kind_enum') THEN
        CREATE TYPE platform.entity_kind_enum AS ENUM ('character', 'place', 'object', 'event', 'theme', 'other');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'platform' AND t.typname = 'spark_status_enum') THEN
        CREATE TYPE platform.spark_status_enum AS ENUM ('inbox', 'processing', 'linked', 'archived', 'discarded');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'platform' AND t.typname = 'chapter_status_enum') THEN
        CREATE TYPE platform.chapter_status_enum AS ENUM ('draft', 'in_review', 'revised', 'final');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'platform' AND t.typname = 'mural_node_kind_enum') THEN
        CREATE TYPE platform.mural_node_kind_enum AS ENUM ('idea', 'plot', 'character_note', 'theme', 'ai_suggestion', 'other');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'platform' AND t.typname = 'feed_event_kind_enum') THEN
        CREATE TYPE platform.feed_event_kind_enum AS ENUM (
            'spark_ingested', 'entity_created', 'entity_updated', 'relation_created',
            'chapter_revised', 'mural_updated', 'ai_analysis', 'system'
        );
    END IF;
END $$;
SELECT superadmin.log_migration_step('PKG_DSV_V1_00004_PLATFORM', 'INFO', 'ENUMs platform criados');

CREATE OR REPLACE FUNCTION platform.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- PROJETO
-- =============================================================================
CREATE TABLE IF NOT EXISTS platform.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL,
    synopsis TEXT,
    status platform.project_status_enum NOT NULL DEFAULT 'draft',
    settings JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_projects_workspace FOREIGN KEY (workspace_id) REFERENCES core.workspaces(id) ON DELETE CASCADE,
    CONSTRAINT fk_projects_created_by FOREIGN KEY (created_by) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT chk_projects_name_not_empty CHECK (LENGTH(TRIM(name)) > 0),
    CONSTRAINT chk_projects_slug_format CHECK (slug ~* '^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'),
    CONSTRAINT uq_projects_workspace_slug UNIQUE (workspace_id, slug)
);
COMMENT ON TABLE platform.projects IS 'Obra/projeto literario — unidade canonica';

DROP TRIGGER IF EXISTS trigger_projects_updated_at ON platform.projects;
CREATE TRIGGER trigger_projects_updated_at
    BEFORE UPDATE ON platform.projects
    FOR EACH ROW EXECUTE FUNCTION platform.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_projects_workspace_id ON platform.projects (workspace_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON platform.projects (status);

CREATE TABLE IF NOT EXISTS platform.project_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role platform.project_member_role_enum NOT NULL DEFAULT 'editor',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_project_members_project FOREIGN KEY (project_id) REFERENCES platform.projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_project_members_user FOREIGN KEY (user_id) REFERENCES core.users(id) ON DELETE CASCADE,
    CONSTRAINT uq_project_members_project_user UNIQUE (project_id, user_id)
);

DROP TRIGGER IF EXISTS trigger_project_members_updated_at ON platform.project_members;
CREATE TRIGGER trigger_project_members_updated_at
    BEFORE UPDATE ON platform.project_members
    FOR EACH ROW EXECUTE FUNCTION platform.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_project_members_user_id ON platform.project_members (user_id);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00004_PLATFORM', 'INFO', 'Tabelas projects e project_members criadas');

-- =============================================================================
-- CATÁLOGO
-- =============================================================================
CREATE TABLE IF NOT EXISTS platform.entities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    kind platform.entity_kind_enum NOT NULL,
    name VARCHAR(255) NOT NULL,
    summary TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_entities_project FOREIGN KEY (project_id) REFERENCES platform.projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_entities_created_by FOREIGN KEY (created_by) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT chk_entities_name_not_empty CHECK (LENGTH(TRIM(name)) > 0)
);
COMMENT ON TABLE platform.entities IS 'Catalogo da obra: personagens, lugares, objetos, eventos, temas';

DROP TRIGGER IF EXISTS trigger_entities_updated_at ON platform.entities;
CREATE TRIGGER trigger_entities_updated_at
    BEFORE UPDATE ON platform.entities
    FOR EACH ROW EXECUTE FUNCTION platform.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_entities_project_id ON platform.entities (project_id);
CREATE INDEX IF NOT EXISTS idx_entities_kind ON platform.entities (kind);
CREATE INDEX IF NOT EXISTS idx_entities_name ON platform.entities (project_id, name);

CREATE TABLE IF NOT EXISTS platform.entity_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    source_entity_id UUID NOT NULL,
    target_entity_id UUID NOT NULL,
    relation_type VARCHAR(100) NOT NULL,
    notes TEXT,
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_entity_relations_project FOREIGN KEY (project_id) REFERENCES platform.projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_entity_relations_source FOREIGN KEY (source_entity_id) REFERENCES platform.entities(id) ON DELETE CASCADE,
    CONSTRAINT fk_entity_relations_target FOREIGN KEY (target_entity_id) REFERENCES platform.entities(id) ON DELETE CASCADE,
    CONSTRAINT chk_entity_relations_not_self CHECK (source_entity_id <> target_entity_id),
    CONSTRAINT uq_entity_relations UNIQUE (source_entity_id, target_entity_id, relation_type)
);

DROP TRIGGER IF EXISTS trigger_entity_relations_updated_at ON platform.entity_relations;
CREATE TRIGGER trigger_entity_relations_updated_at
    BEFORE UPDATE ON platform.entity_relations
    FOR EACH ROW EXECUTE FUNCTION platform.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_entity_relations_project_id ON platform.entity_relations (project_id);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00004_PLATFORM', 'INFO', 'Tabelas entities e entity_relations criadas');

-- =============================================================================
-- FAÍSCAS
-- =============================================================================
CREATE TABLE IF NOT EXISTS platform.sparks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    title VARCHAR(500),
    body TEXT NOT NULL,
    status platform.spark_status_enum NOT NULL DEFAULT 'inbox',
    source VARCHAR(50) NOT NULL DEFAULT 'user',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_sparks_project FOREIGN KEY (project_id) REFERENCES platform.projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_sparks_created_by FOREIGN KEY (created_by) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT chk_sparks_body_not_empty CHECK (LENGTH(TRIM(body)) > 0),
    CONSTRAINT chk_sparks_source CHECK (source IN ('user', 'ai', 'import', 'system'))
);
COMMENT ON TABLE platform.sparks IS 'Faiscas — fragmentos capturados para a obra';

DROP TRIGGER IF EXISTS trigger_sparks_updated_at ON platform.sparks;
CREATE TRIGGER trigger_sparks_updated_at
    BEFORE UPDATE ON platform.sparks
    FOR EACH ROW EXECUTE FUNCTION platform.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_sparks_project_id ON platform.sparks (project_id);
CREATE INDEX IF NOT EXISTS idx_sparks_status ON platform.sparks (status);

CREATE TABLE IF NOT EXISTS platform.spark_mentions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spark_id UUID NOT NULL,
    mention_text VARCHAR(255) NOT NULL,
    start_offset INTEGER,
    end_offset INTEGER,
    resolved_entity_id UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_spark_mentions_spark FOREIGN KEY (spark_id) REFERENCES platform.sparks(id) ON DELETE CASCADE,
    CONSTRAINT fk_spark_mentions_entity FOREIGN KEY (resolved_entity_id) REFERENCES platform.entities(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS platform.spark_entity_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spark_id UUID NOT NULL,
    entity_id UUID NOT NULL,
    link_strength NUMERIC(5, 4) DEFAULT 1.0,
    created_by_ai BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_spark_entity_links_spark FOREIGN KEY (spark_id) REFERENCES platform.sparks(id) ON DELETE CASCADE,
    CONSTRAINT fk_spark_entity_links_entity FOREIGN KEY (entity_id) REFERENCES platform.entities(id) ON DELETE CASCADE,
    CONSTRAINT uq_spark_entity_links UNIQUE (spark_id, entity_id)
);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00004_PLATFORM', 'INFO', 'Tabelas sparks, spark_mentions e spark_entity_links criadas');

-- =============================================================================
-- NARRATIVA
-- =============================================================================
CREATE TABLE IF NOT EXISTS platform.chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    title VARCHAR(500) NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    status platform.chapter_status_enum NOT NULL DEFAULT 'draft',
    summary TEXT,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_chapters_project FOREIGN KEY (project_id) REFERENCES platform.projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_chapters_created_by FOREIGN KEY (created_by) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT chk_chapters_title_not_empty CHECK (LENGTH(TRIM(title)) > 0)
);

DROP TRIGGER IF EXISTS trigger_chapters_updated_at ON platform.chapters;
CREATE TRIGGER trigger_chapters_updated_at
    BEFORE UPDATE ON platform.chapters
    FOR EACH ROW EXECUTE FUNCTION platform.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_chapters_project_id ON platform.chapters (project_id);
CREATE INDEX IF NOT EXISTS idx_chapters_position ON platform.chapters (project_id, position);

CREATE TABLE IF NOT EXISTS platform.chapter_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chapter_id UUID NOT NULL,
    revision_number INTEGER NOT NULL,
    body TEXT NOT NULL,
    word_count INTEGER,
    created_by UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_chapter_revisions_chapter FOREIGN KEY (chapter_id) REFERENCES platform.chapters(id) ON DELETE CASCADE,
    CONSTRAINT fk_chapter_revisions_created_by FOREIGN KEY (created_by) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT uq_chapter_revisions_number UNIQUE (chapter_id, revision_number)
);

CREATE TABLE IF NOT EXISTS platform.spark_chapter_links (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    spark_id UUID NOT NULL,
    chapter_id UUID NOT NULL,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_spark_chapter_links_spark FOREIGN KEY (spark_id) REFERENCES platform.sparks(id) ON DELETE CASCADE,
    CONSTRAINT fk_spark_chapter_links_chapter FOREIGN KEY (chapter_id) REFERENCES platform.chapters(id) ON DELETE CASCADE,
    CONSTRAINT uq_spark_chapter_links UNIQUE (spark_id, chapter_id)
);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00004_PLATFORM', 'INFO', 'Tabelas chapters, chapter_revisions e spark_chapter_links criadas');

-- =============================================================================
-- MURAL
-- =============================================================================
CREATE TABLE IF NOT EXISTS platform.mural_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    kind platform.mural_node_kind_enum NOT NULL DEFAULT 'idea',
    title VARCHAR(500) NOT NULL,
    body TEXT,
    position_x NUMERIC(12, 4) NOT NULL DEFAULT 0,
    position_y NUMERIC(12, 4) NOT NULL DEFAULT 0,
    color VARCHAR(32),
    linked_entity_id UUID,
    linked_spark_id UUID,
    created_by UUID,
    created_by_ai BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_mural_nodes_project FOREIGN KEY (project_id) REFERENCES platform.projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_mural_nodes_entity FOREIGN KEY (linked_entity_id) REFERENCES platform.entities(id) ON DELETE SET NULL,
    CONSTRAINT fk_mural_nodes_spark FOREIGN KEY (linked_spark_id) REFERENCES platform.sparks(id) ON DELETE SET NULL,
    CONSTRAINT fk_mural_nodes_created_by FOREIGN KEY (created_by) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT chk_mural_nodes_title_not_empty CHECK (LENGTH(TRIM(title)) > 0)
);
COMMENT ON TABLE platform.mural_nodes IS 'Nos (post-its) do mural de ideias';

DROP TRIGGER IF EXISTS trigger_mural_nodes_updated_at ON platform.mural_nodes;
CREATE TRIGGER trigger_mural_nodes_updated_at
    BEFORE UPDATE ON platform.mural_nodes
    FOR EACH ROW EXECUTE FUNCTION platform.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_mural_nodes_project_id ON platform.mural_nodes (project_id);

CREATE TABLE IF NOT EXISTS platform.mural_edges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    source_node_id UUID NOT NULL,
    target_node_id UUID NOT NULL,
    label VARCHAR(255),
    edge_type VARCHAR(100) NOT NULL DEFAULT 'relates',
    created_by UUID,
    created_by_ai BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_mural_edges_project FOREIGN KEY (project_id) REFERENCES platform.projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_mural_edges_source FOREIGN KEY (source_node_id) REFERENCES platform.mural_nodes(id) ON DELETE CASCADE,
    CONSTRAINT fk_mural_edges_target FOREIGN KEY (target_node_id) REFERENCES platform.mural_nodes(id) ON DELETE CASCADE,
    CONSTRAINT fk_mural_edges_created_by FOREIGN KEY (created_by) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT chk_mural_edges_not_self CHECK (source_node_id <> target_node_id),
    CONSTRAINT uq_mural_edges UNIQUE (source_node_id, target_node_id, edge_type)
);

DROP TRIGGER IF EXISTS trigger_mural_edges_updated_at ON platform.mural_edges;
CREATE TRIGGER trigger_mural_edges_updated_at
    BEFORE UPDATE ON platform.mural_edges
    FOR EACH ROW EXECUTE FUNCTION platform.update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_mural_edges_project_id ON platform.mural_edges (project_id);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00004_PLATFORM', 'INFO', 'Tabelas mural_nodes e mural_edges criadas');

-- =============================================================================
-- FEED
-- =============================================================================
CREATE TABLE IF NOT EXISTS platform.feed_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL,
    kind platform.feed_event_kind_enum NOT NULL,
    title VARCHAR(500),
    body TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    actor_user_id UUID,
    related_spark_id UUID,
    related_entity_id UUID,
    related_chapter_id UUID,
    related_mural_node_id UUID,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_feed_events_project FOREIGN KEY (project_id) REFERENCES platform.projects(id) ON DELETE CASCADE,
    CONSTRAINT fk_feed_events_actor FOREIGN KEY (actor_user_id) REFERENCES core.users(id) ON DELETE SET NULL,
    CONSTRAINT fk_feed_events_spark FOREIGN KEY (related_spark_id) REFERENCES platform.sparks(id) ON DELETE SET NULL,
    CONSTRAINT fk_feed_events_entity FOREIGN KEY (related_entity_id) REFERENCES platform.entities(id) ON DELETE SET NULL,
    CONSTRAINT fk_feed_events_chapter FOREIGN KEY (related_chapter_id) REFERENCES platform.chapters(id) ON DELETE SET NULL,
    CONSTRAINT fk_feed_events_mural_node FOREIGN KEY (related_mural_node_id) REFERENCES platform.mural_nodes(id) ON DELETE SET NULL
);
COMMENT ON TABLE platform.feed_events IS 'Feed narrativo / consequencias estruturais da obra';

CREATE INDEX IF NOT EXISTS idx_feed_events_project_id ON platform.feed_events (project_id);
CREATE INDEX IF NOT EXISTS idx_feed_events_kind ON platform.feed_events (kind);
CREATE INDEX IF NOT EXISTS idx_feed_events_created_at ON platform.feed_events (project_id, created_at DESC);
SELECT superadmin.log_migration_step('PKG_DSV_V1_00004_PLATFORM', 'INFO', 'Tabela feed_events criada');

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
    'PKG_DSV_V1_00004_PLATFORM',
    '01-PLATFORM-CRE.sql',
    'desenvolvimento',
    'Schema platform: projects, catalog, sparks, narrative, mural, feed',
    encode(sha256('PKG_DSV_V1_00004_PLATFORM'::bytea), 'hex')
);

SELECT superadmin.log_migration_step('PKG_DSV_V1_00004_PLATFORM', 'INFO', 'Registro no historico concluido');

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
    SELECT COUNT(*) INTO v_count FROM pg_catalog.pg_namespace WHERE nspname = 'platform';
    IF v_count > 0 THEN v_success_count := v_success_count + 1; RAISE NOTICE 'Schema platform OK';
    ELSE RAISE NOTICE 'FALHA - schema platform'; END IF;

    FOREACH v_table IN ARRAY ARRAY[
        'projects', 'project_members',
        'entities', 'entity_relations',
        'sparks', 'spark_mentions', 'spark_entity_links',
        'chapters', 'chapter_revisions', 'spark_chapter_links',
        'mural_nodes', 'mural_edges',
        'feed_events'
    ]
    LOOP
        v_total_checks := v_total_checks + 1;
        SELECT COUNT(*) INTO v_count FROM pg_tables WHERE schemaname = 'platform' AND tablename = v_table;
        IF v_count > 0 THEN
            v_success_count := v_success_count + 1;
            RAISE NOTICE 'Tabela platform.% OK', v_table;
        ELSE
            RAISE NOTICE 'FALHA - tabela platform.%', v_table;
        END IF;
    END LOOP;

    v_total_checks := v_total_checks + 1;
    SELECT COUNT(*) INTO v_count FROM superadmin.migrations
    WHERE package_name = 'PKG_DSV_V1_00004_PLATFORM' AND file_name = '01-PLATFORM-CRE.sql';
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
    IF v_success_count = v_total_checks THEN
        RAISE NOTICE 'VALIDACAO CONCLUIDA COM SUCESSO TOTAL';
    ELSE
        RAISE NOTICE 'VALIDACAO CONCLUIDA COM FALHAS';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'ERRO CRITICO NA VALIDACAO: %', SQLERRM;
END $$;

SELECT 'MIGRATION CONCLUIDA: PKG_DSV_V1_00004_PLATFORM - ' || NOW() AS log_entry;
\o

-- =====================================================
-- Status: Migration aplicada com sucesso
-- =====================================================
