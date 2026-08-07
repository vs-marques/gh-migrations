-- =====================================================
-- Script de Correção: Atualizar nomes de ambiente em produção
-- Data: 18/11/2025
-- Descrição: Corrige registros de migrations que foram salvos
--            com 'produção' (com acento) para 'producao' (sem acento)
--            para compatibilidade com o gerenciador de migrations
-- =====================================================

-- ATENÇÃO: Execute este script APENAS se você tiver registros
-- com 'produção' (com acento) na tabela superadmin.migrations

BEGIN;

-- Verificar quantos registros precisam ser corrigidos
SELECT 
    COUNT(*) as total_registros_com_acento,
    COUNT(DISTINCT package_name) as pacotes_afetados
FROM superadmin.migrations
WHERE environment = 'produção';

-- Atualizar registros de 'produção' para 'producao'
UPDATE superadmin.migrations
SET environment = 'producao'
WHERE environment = 'produção';

-- Verificar resultado
SELECT 
    environment,
    COUNT(*) as total_registros
FROM superadmin.migrations
WHERE environment IN ('produção', 'producao')
GROUP BY environment;

COMMIT;

-- =====================================================
-- Status: ✅ Correção aplicada
-- =====================================================

