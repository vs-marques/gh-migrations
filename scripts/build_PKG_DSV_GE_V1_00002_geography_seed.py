"""
Monta o arquivo único 01-GEOGRAPHY-SEED.sql (EXP + estados + cidades CEP Aberto).
Saída: migrations/geography/.../PKG_DSV_GE_V1_00002_GEOGRAPHY/01-GEOGRAPHY-SEED.sql
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "migrations" / "geography" / "desenvolvimento" / "2026" / "Maio" / "17.05.2026" / "PKG_DSV_GE_V1_00002_GEOGRAPHY"
CITIES_CSV = ROOT / "data" / "cep_aberto" / "cities.cepaberto.csv"

# IBGE — código da UF (2 dígitos) por sigla (fonte IBGE).
IBGE_UF: dict[str, int] = {
    "AC": 12,
    "AL": 27,
    "AM": 13,
    "AP": 16,
    "BA": 29,
    "CE": 23,
    "DF": 53,
    "ES": 32,
    "GO": 52,
    "MA": 21,
    "MG": 31,
    "MS": 50,
    "MT": 51,
    "PA": 15,
    "PB": 25,
    "PE": 26,
    "PI": 22,
    "PR": 41,
    "RJ": 33,
    "RN": 24,
    "RO": 11,
    "RR": 14,
    "RS": 43,
    "SC": 42,
    "SE": 28,
    "SP": 35,
    "TO": 17,
}

STATES_ROWS: list[tuple[int, str, str]] = [
    (1, "Acre", "AC"),
    (2, "Alagoas", "AL"),
    (3, "Amazonas", "AM"),
    (4, "Amapá", "AP"),
    (5, "Bahia", "BA"),
    (6, "Ceara", "CE"),
    (7, "Distrito Federal", "DF"),
    (8, "Espirito Santo", "ES"),
    (9, "Goiás", "GO"),
    (10, "Maranhão", "MA"),
    (11, "Minas Gerais", "MG"),
    (12, "Mato Grosso do Sul", "MS"),
    (13, "Mato Grosso", "MT"),
    (14, "Pará", "PA"),
    (15, "Paraíba", "PB"),
    (16, "Pernambuco", "PE"),
    (17, "Piauí", "PI"),
    (18, "Paraná", "PR"),
    (19, "Rio de Janeiro", "RJ"),
    (20, "Rio Grande do Norte", "RN"),
    (21, "Rondônia", "RO"),
    (22, "Roraima", "RR"),
    (23, "Rio Grande do Sul", "RS"),
    (24, "Santa Catarina", "SC"),
    (25, "Sergipe", "SE"),
    (26, "São Paulo", "SP"),
    (27, "Tocantins", "TO"),
]


def esc(s: str) -> str:
    return s.replace("'", "''")


def parse_city_line(ln: str) -> tuple[int, str, int]:
    parts = ln.split(",")
    if len(parts) < 3:
        raise ValueError(ln)
    cid, se = parts[0], parts[-1]
    name = ",".join(parts[1:-1])
    return int(cid), name, int(se)


def gen_cities_batches() -> str:
    lines = [ln.strip() for ln in CITIES_CSV.read_text(encoding="utf-8").splitlines() if ln.strip()]
    rows = [parse_city_line(ln) for ln in lines]
    batch = 400
    out: list[str] = []
    for i in range(0, len(rows), batch):
        part = rows[i : i + batch]
        vals = ",\n".join(f"    ('{esc(name)}', {se}, {cid})" for cid, name, se in part)
        out.append(
            "INSERT INTO geography.cities (name, state_id, ibge_municipality_code, external_code)\n"
            "SELECT v.name, s.id, NULL, v.ext::integer\n"
            "FROM (\nVALUES\n"
            f"{vals}\n"
            ") AS v(name, se, ext)\n"
            "JOIN geography.states s ON s.external_code = v.se\n"
            "ON CONFLICT (external_code) DO UPDATE SET\n"
            "  name = EXCLUDED.name,\n"
            "  state_id = EXCLUDED.state_id,\n"
            "  ibge_municipality_code = EXCLUDED.ibge_municipality_code,\n"
            "  updated_at = NOW();\n"
        )
    return "\n".join(out)


def gen_states_values() -> str:
    lines = []
    for ext, name, uf in STATES_ROWS:
        ibge = IBGE_UF[uf]
        lines.append(f"    ({ext}, '{esc(name)}', '{uf}', {ibge})")
    return ",\n".join(lines)


def main() -> None:
    PKG.mkdir(parents=True, exist_ok=True)
    states_sql = (
        "INSERT INTO geography.states (external_code, name, uf, ibge_state_code)\n"
        "VALUES\n"
        f"{gen_states_values()}\n"
        "ON CONFLICT (uf) DO UPDATE SET\n"
        "  name = EXCLUDED.name,\n"
        "  external_code = EXCLUDED.external_code,\n"
        "  ibge_state_code = EXCLUDED.ibge_state_code,\n"
        "  updated_at = NOW();\n"
    )
    cities_sql = gen_cities_batches()

    header = """-- =====================================================
-- Migration: PKG_DSV_GE_V1_00002_GEOGRAPHY
-- Arquivo: 01-GEOGRAPHY-SEED.sql
-- Data: 17/05/2026
-- Banco destino: GE (PostGIS / schema geography) — ver MIGRATIONS_MASTER_REFERENCE.md
-- Descrição: CEP Aberto fase 1 — external_code + seed UF/municípios; no mesmo BEGIN: DROP UNIQUE (state_id,name),
--   INSERT dados, dedup (menor external_code), ADD UNIQUE de volta.
-- Dependência: PKG_DSV_GE_V1_00001_GEOGRAPHY (DDL geography).
-- Histórico:
-- - 2026-05-17: EXP external_code + índices únicos; SEED estados (27) e cidades (~10,6k) a partir de dumps CEP Aberto (states.csv / cities.csv).
-- - 2026-05-14: Fluxo único no seed: DROP uq_geography_cities_state_name → INSERT → dedup → ADD CONSTRAINT.
-- =====================================================
--
-- =====================================================
-- OBJETIVO
-- =====================================================
-- 1) geography.states.external_code = id numérico CEP Aberto do estado (1–27); ibge_state_code oficial IBGE.
-- 2) geography.cities.external_code = id numérico CEP Aberto do município (join futuro: postal_codes / ingest CEP).
-- 3) geography.cities.state_id resolve via states.external_code (terceira coluna do cities.csv).
-- 4) Antes dos INSERT de cidades: DROP CONSTRAINT uq_geography_cities_state_name. Depois de todos os INSERT: dedup
--    (state_id, name) mantendo menor external_code; em seguida ADD CONSTRAINT UNIQUE de volta.
-- =====================================================
--
-- =====================================================
-- TRANSACAO / ERRO 25P02 (tudo ou nada)
-- =====================================================
-- Este arquivo usa BEGIN ... COMMIT: ou aplica tudo ou desfaz tudo (exceto se o cliente quebrar a conexão
-- no meio, caso raro).
-- Se um comando FALHAR, o PostgreSQL aborta a transação inteira; qualquer comando seguinte na mesma
-- sessão retorna "current transaction is aborted" (SQLSTATE 25P02) até haver ROLLBACK.
-- Um bloco DO ... EXCEPTION colocado NO FINAL do script NÃO resolve isso: ele só captura erros
-- executados DENTRO daquele DO; erros em INSERT/ALTER anteriores já abortaram o BEGIN externo antes.
-- Depois de erro (DBeaver / SQL Editor): na mesma sessão execute uma vez: ROLLBACK;
-- psql com transação única implícita (NÃO misturar com este BEGIN explícito): ver --single-transaction na doc.
-- =====================================================

--\\o migration_PKG_DSV_GE_V1_00002_GEOGRAPHY_2026-05-17.log

SELECT 'MIGRATION INICIADA: PKG_DSV_GE_V1_00002_GEOGRAPHY - ' || NOW() AS log_entry;

BEGIN;

-- =====================================================
-- REGISTRO OBRIGATÓRIO NA TABELA DE HISTÓRICO
-- =====================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM superadmin.migrations
        WHERE package_name = 'PKG_DSV_GE_V1_00002_GEOGRAPHY'
          AND file_name = '01-GEOGRAPHY-SEED.sql'
          AND environment = 'desenvolvimento'
    ) THEN
        INSERT INTO superadmin.migrations (
            package_name,
            file_name,
            environment,
            notes,
            checksum
        ) VALUES (
            'PKG_DSV_GE_V1_00002_GEOGRAPHY',
            '01-GEOGRAPHY-SEED.sql',
            'desenvolvimento',
            'SEED: CEP Aberto — external_code; DROP uq_geography_cities_state_name → UF + cidades → dedup → ADD CONSTRAINT. GE.',
            encode(sha256('PKG_DSV_GE_V1_00002_GEOGRAPHY'::bytea), 'hex')
        );
    END IF;
END $$;

SELECT superadmin.log_migration_step(
    'PKG_DSV_GE_V1_00002_GEOGRAPHY',
    'INFO',
    'Registro em superadmin.migrations confirmado.'
);

-- =====================================================
-- PARTE A — Colunas e índices (external_code)
-- =====================================================
ALTER TABLE geography.states
    ADD COLUMN IF NOT EXISTS external_code INTEGER NULL;

ALTER TABLE geography.cities
    ADD COLUMN IF NOT EXISTS external_code INTEGER NULL;

COMMENT ON COLUMN geography.states.external_code IS
    'Identificador numérico do estado no dump CEP Aberto (1–27); chave de junção com coluna estado do cities.csv.';

COMMENT ON COLUMN geography.cities.external_code IS
    'Identificador numérico do município no dump CEP Aberto; usar em ingest de CEP (ex.: JOIN cities.external_code = coluna localidade do CSV de faixa).';

CREATE UNIQUE INDEX IF NOT EXISTS uq_geography_states_external_code
    ON geography.states (external_code);

CREATE UNIQUE INDEX IF NOT EXISTS uq_geography_cities_external_code
    ON geography.cities (external_code);

SELECT superadmin.log_migration_step(
    'PKG_DSV_GE_V1_00002_GEOGRAPHY',
    'INFO',
    'Colunas external_code e índices únicos aplicados em geography.states / geography.cities.'
);

-- =====================================================
-- PARTE A2 — Remover UNIQUE (state_id, name) antes dos INSERT de municípios
-- =====================================================
ALTER TABLE geography.cities
    DROP CONSTRAINT IF EXISTS uq_geography_cities_state_name;

SELECT superadmin.log_migration_step(
    'PKG_DSV_GE_V1_00002_GEOGRAPHY',
    'INFO',
    'Constraint uq_geography_cities_state_name removida antes do seed de cidades (recriada após dedup).'
);

-- =====================================================
-- PARTE B — Estados (CEP Aberto states.csv)
-- =====================================================
"""

    mid = states_sql

    mid2 = """
SELECT superadmin.log_migration_step(
    'PKG_DSV_GE_V1_00002_GEOGRAPHY',
    'INFO',
    'Seed geography.states (27 UFs) aplicado.'
);

-- =====================================================
-- PARTE C — Municípios (CEP Aberto cities.csv)
-- =====================================================
"""

    footer = """
SELECT superadmin.log_migration_step(
    'PKG_DSV_GE_V1_00002_GEOGRAPHY',
    'INFO',
    'Seed geography.cities (CEP Aberto) aplicado em lotes.'
);

-- =====================================================
-- PARTE D — Deduplicar (state_id, name); recriar UNIQUE (state_id, name)
-- =====================================================
DO $$
DECLARE
    n INTEGER;
BEGIN
    DELETE FROM geography.cities c
    WHERE c.id IN (
        SELECT r.id
        FROM (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY state_id, name
                    ORDER BY external_code ASC NULLS LAST, id ASC
                ) AS rn
            FROM geography.cities
        ) r
        WHERE r.rn > 1
    );

    GET DIAGNOSTICS n = ROW_COUNT;
    RAISE NOTICE 'geography.cities dedup (state_id, name): % linha(s) removida(s); mantido menor external_code (empate: id).', n;
END $$;

SELECT superadmin.log_migration_step(
    'PKG_DSV_GE_V1_00002_GEOGRAPHY',
    'INFO',
    'Deduplicação geography.cities (state_id, name) concluída.'
);

DROP INDEX IF EXISTS geography.idx_geography_cities_state_id_name;

ALTER TABLE geography.cities
    ADD CONSTRAINT uq_geography_cities_state_name UNIQUE (state_id, name);

SELECT superadmin.log_migration_step(
    'PKG_DSV_GE_V1_00002_GEOGRAPHY',
    'INFO',
    'Constraint uq_geography_cities_state_name recriada após dedup.'
);

COMMIT;

-- =====================================================
-- VALIDAÇÃO FINAL
-- =====================================================
DO $$
DECLARE
    v_states INTEGER;
    v_cities INTEGER;
    v_ok INTEGER := 0;
    v_total INTEGER := 7;
    v_logs INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_states FROM geography.states WHERE external_code IS NOT NULL;
    IF v_states >= 27 THEN
        v_ok := v_ok + 1;
        RAISE NOTICE '✅ geography.states com external_code: % linhas', v_states;
    ELSE
        RAISE NOTICE '❌ geography.states external_code insuficiente: %', v_states;
    END IF;

    SELECT COUNT(*) INTO v_cities FROM geography.cities WHERE external_code IS NOT NULL;
    IF v_cities >= 10000 THEN
        v_ok := v_ok + 1;
        RAISE NOTICE '✅ geography.cities com external_code: % linhas', v_cities;
    ELSE
        RAISE NOTICE '❌ geography.cities external_code insuficiente: %', v_cities;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        JOIN pg_namespace n ON t.relnamespace = n.oid
        WHERE n.nspname = 'geography'
          AND t.relname = 'cities'
          AND c.conname = 'uq_geography_cities_state_name'
    ) THEN
        v_ok := v_ok + 1;
        RAISE NOTICE '✅ Constraint uq_geography_cities_state_name presente.';
    ELSE
        RAISE NOTICE '❌ Constraint uq_geography_cities_state_name ausente.';
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM (
            SELECT state_id, name
            FROM geography.cities
            GROUP BY state_id, name
            HAVING COUNT(*) > 1
        ) d
    ) THEN
        v_ok := v_ok + 1;
        RAISE NOTICE '✅ Sem duplicata (state_id, name) em geography.cities.';
    ELSE
        RAISE NOTICE '❌ Ainda existem duplicatas (state_id, name).';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'geography' AND indexname = 'uq_geography_states_external_code'
    ) THEN
        v_ok := v_ok + 1;
        RAISE NOTICE '✅ Índice uq_geography_states_external_code existe.';
    ELSE
        RAISE NOTICE '❌ Índice uq_geography_states_external_code ausente.';
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'geography' AND indexname = 'uq_geography_cities_external_code'
    ) THEN
        v_ok := v_ok + 1;
        RAISE NOTICE '✅ Índice uq_geography_cities_external_code existe.';
    ELSE
        RAISE NOTICE '❌ Índice uq_geography_cities_external_code ausente.';
    END IF;

    SELECT COUNT(*) INTO v_logs
    FROM superadmin.migration_logs ml
    JOIN superadmin.migrations m ON ml.migration_id = m.id
    WHERE m.package_name = 'PKG_DSV_GE_V1_00002_GEOGRAPHY';
    IF v_logs > 0 THEN
        v_ok := v_ok + 1;
        RAISE NOTICE '✅ Logs em migration_logs: % entradas', v_logs;
    ELSE
        RAISE NOTICE '❌ Nenhum log em migration_logs para este pacote.';
    END IF;

    RAISE NOTICE '📊 RESUMO: % / % verificações OK.', v_ok, v_total;
    IF v_ok = v_total THEN
        RAISE NOTICE '✅ VALIDAÇÃO CONCLUÍDA COM SUCESSO TOTAL!';
    ELSE
        RAISE NOTICE '⚠️ VALIDAÇÃO COM FALHAS.';
    END IF;
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE '❌ ERRO NA VALIDAÇÃO: %', SQLERRM;
END $$;

SELECT 'MIGRATION CONCLUIDA: PKG_DSV_GE_V1_00002_GEOGRAPHY - ' || NOW() AS log_entry;

--\\o

-- =====================================================
-- Status: ✅ Migration aplicada com sucesso
-- =====================================================
"""

    full = header + mid + mid2 + cities_sql + footer
    out = PKG / "01-GEOGRAPHY-SEED.sql"
    out.write_text(full, encoding="utf-8")
    print("written", out, "bytes", out.stat().st_size)


if __name__ == "__main__":
    main()
