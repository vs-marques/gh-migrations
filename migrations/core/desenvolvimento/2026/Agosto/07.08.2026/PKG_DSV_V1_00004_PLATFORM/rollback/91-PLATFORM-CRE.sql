-- =====================================================
-- Rollback: PKG_DSV_V1_00004_PLATFORM
-- Arquivo: rollback/91-PLATFORM-CRE.sql
-- Data: 07/08/2026
-- Descrição: Reversão de 01-PLATFORM-CRE.sql
-- =====================================================
-- Nota: aplicar antes rollback/92-SECURITY-EXP.sql (FK em security).

DROP TABLE IF EXISTS platform.feed_events CASCADE;
DROP TABLE IF EXISTS platform.mural_edges CASCADE;
DROP TABLE IF EXISTS platform.mural_nodes CASCADE;
DROP TABLE IF EXISTS platform.spark_chapter_links CASCADE;
DROP TABLE IF EXISTS platform.chapter_revisions CASCADE;
DROP TABLE IF EXISTS platform.chapters CASCADE;
DROP TABLE IF EXISTS platform.spark_entity_links CASCADE;
DROP TABLE IF EXISTS platform.spark_mentions CASCADE;
DROP TABLE IF EXISTS platform.sparks CASCADE;
DROP TABLE IF EXISTS platform.entity_relations CASCADE;
DROP TABLE IF EXISTS platform.entities CASCADE;
DROP TABLE IF EXISTS platform.project_members CASCADE;
DROP TABLE IF EXISTS platform.projects CASCADE;

DROP FUNCTION IF EXISTS platform.update_updated_at_column();

DROP TYPE IF EXISTS platform.feed_event_kind_enum;
DROP TYPE IF EXISTS platform.mural_node_kind_enum;
DROP TYPE IF EXISTS platform.chapter_status_enum;
DROP TYPE IF EXISTS platform.spark_status_enum;
DROP TYPE IF EXISTS platform.entity_kind_enum;
DROP TYPE IF EXISTS platform.project_member_role_enum;
DROP TYPE IF EXISTS platform.project_status_enum;

DROP SCHEMA IF EXISTS platform CASCADE;

UPDATE superadmin.migrations
SET
    status = 'rolled_back',
    updated_at = NOW(),
    notes = COALESCE(notes, '') || ' | ROLLBACK APLICADO'
WHERE package_name = 'PKG_DSV_V1_00004_PLATFORM'
  AND file_name = '01-PLATFORM-CRE.sql'
  AND environment = 'desenvolvimento';

-- =====================================================
-- Status: Rollback aplicado com sucesso
-- =====================================================
