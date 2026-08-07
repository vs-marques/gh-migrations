"""
Gera SQL com um único UPDATE em massa: geography.cities.ibge_municipality_code
a partir da lista oficial de municípios do IBGE (API localidades).

Uso::

  python scripts/generate_geography_ibge_municipios_update_sql.py -o /tmp/ibge_upd.sql

Requer rede na primeira geração (descarrega JSON). O SQL gerado é autónomo
(VALUES com todos os municípios) e pode ser colado no psql ou incluído num pacote de migration.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import urllib.request
from datetime import date
from typing import Any

MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


def _load_json_http(url: str, timeout: int) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "nyoka-migrations/generate_ibge_sql"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def _uf_sigla(mun: dict[str, Any]) -> str | None:
    for path in (
        ("microrregiao", "mesorregiao", "UF", "sigla"),
        ("regiao-imediata", "regiao-intermediaria", "UF", "sigla"),
    ):
        cur: Any = mun
        try:
            for key in path:
                cur = cur[key]
            s = str(cur).strip().upper()
            return s or None
        except (KeyError, TypeError):
            continue
    return None


def fetch_rows(timeout: int) -> list[tuple[str, str, int]]:
    data = _load_json_http(MUNICIPIOS_URL, timeout=timeout)
    if not isinstance(data, list):
        raise RuntimeError("Resposta IBGE inesperada (esperado array)")
    out: list[tuple[str, str, int]] = []
    for m in data:
        if not isinstance(m, dict):
            continue
        nome = (m.get("nome") or "").strip()
        uf = _uf_sigla(m)
        mid = m.get("id")
        if not nome or uf is None or mid is None:
            continue
        out.append((uf, nome, int(mid)))
    out.sort(key=lambda t: (t[0], t[1]))
    return out


def sql_str(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def emit_update_only(rows: list[tuple[str, str, int]], fh: Any) -> None:
    fh.write(
        "-- Preencher ibge_municipality_code onde (UF, nome) = município oficial IBGE.\n"
        "-- Gerado automaticamente; não editar a lista VALUES à mão.\n"
        "UPDATE geography.cities AS c\n"
        "SET\n"
        "    ibge_municipality_code = src.codigo,\n"
        "    updated_at = NOW()\n"
        "FROM (\n"
        "    VALUES\n"
    )
    for i, (uf, nome, cod) in enumerate(rows):
        comma = ",\n" if i + 1 < len(rows) else "\n"
        fh.write(f"        ({sql_str(uf)}, {sql_str(nome)}, {cod}){comma}")
    fh.write(
        ") AS src(uf, nome_ibge, codigo)\n"
        "JOIN geography.states AS s ON upper(s.uf) = upper(src.uf)\n"
        "WHERE c.state_id = s.id\n"
        "  AND lower(trim(c.name)) = lower(trim(src.nome_ibge))\n"
        "  AND (c.ibge_municipality_code IS DISTINCT FROM src.codigo)\n"
        "  AND NOT EXISTS (\n"
        "      SELECT 1\n"
        "      FROM geography.cities AS o\n"
        "      WHERE o.ibge_municipality_code = src.codigo\n"
        "        AND o.id <> c.id\n"
        "  );\n"
    )


def emit_migration(
    rows: list[tuple[str, str, int]],
    fh: Any,
    *,
    package: str,
    file_name: str,
    environment: str,
    notes: str,
) -> None:
    today = date.today().strftime("%d/%m/%Y")
    iso = date.today().isoformat()
    fh.write(
        f"-- =====================================================\n"
        f"-- Migration: {package}\n"
        f"-- Arquivo: {file_name}\n"
        f"-- Data: {today}\n"
        f"-- Banco destino: GE (schema geography)\n"
        f"-- Descrição: UPDATE geography.cities.ibge_municipality_code via lista oficial IBGE\n"
        f"--   (lower(trim(name))) + UF; respeita UNIQUE(ibge_municipality_code).\n"
        f"-- Dependência: PKG_*_GE_V1_00001_GEOGRAPHY, PKG_*_GE_V1_00002_GEOGRAPHY (cidades CEP Aberto).\n"
        f"-- Fonte dados: {MUNICIPIOS_URL} (snapshot na geração {iso}).\n"
        f"-- =====================================================\n\n"
        f"SELECT 'MIGRATION INICIADA: {package} - ' || NOW() AS log_entry;\n\n"
        f"BEGIN;\n\n"
        f"DO $$\n"
        f"BEGIN\n"
        f"    IF NOT EXISTS (\n"
        f"        SELECT 1 FROM superadmin.migrations\n"
        f"        WHERE package_name = '{package}'\n"
        f"          AND file_name = '{file_name}'\n"
        f"          AND environment = '{environment}'\n"
        f"    ) THEN\n"
        f"        INSERT INTO superadmin.migrations (\n"
        f"            package_name, file_name, environment, notes, checksum\n"
        f"        ) VALUES (\n"
        f"            '{package}',\n"
        f"            '{file_name}',\n"
        f"            '{environment}',\n"
        f"            {sql_str(notes)},\n"
        f"            encode(sha256('{package}'::bytea), 'hex')\n"
        f"        );\n"
        f"    END IF;\n"
        f"END $$;\n\n"
        f"SELECT superadmin.log_migration_step(\n"
        f"    '{package}', 'INFO', 'Registro em superadmin.migrations confirmado.'\n"
        f");\n\n"
    )
    fh.write("-- =====================================================\n-- UPDATE IBGE (todos os municípios)\n-- =====================================================\n\n")
    emit_update_only(rows, fh)
    fh.write(
        f"\nSELECT superadmin.log_migration_step(\n"
        f"    '{package}', 'INFO', 'UPDATE ibge_municipality_code aplicado (fonte IBGE localidades).'\n"
        f");\n\n"
        f"COMMIT;\n\n"
        f"SELECT 'MIGRATION CONCLUIDA: {package} - ' || NOW() AS log_entry;\n"
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("-o", "--output", required=True, help="Ficheiro .sql de saída")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument(
        "--mode",
        choices=("migration", "update-only"),
        default="migration",
        help="migration = superadmin + BEGIN/COMMIT; update-only = só o UPDATE",
    )
    p.add_argument("--package", default="PKG_DSV_GE_V1_00006_GEOGRAPHY")
    p.add_argument("--file-name", default="01-GEOGRAPHY-IBGE-UPD.sql")
    p.add_argument("--environment", default="desenvolvimento")
    p.add_argument(
        "--notes",
        default="UPD: ibge_municipality_code em cities (lista oficial IBGE). GE.",
    )
    args = p.parse_args()
    try:
        rows = fetch_rows(args.timeout)
    except Exception as e:
        print(f"Erro ao obter dados IBGE: {e}", file=sys.stderr)
        return 1
    if len(rows) < 5500:
        print(f"Aviso: só {len(rows)} municípios (esperado ~5570).", file=sys.stderr)
    with open(args.output, "w", encoding="utf-8", newline="\n") as fh:
        if args.mode == "update-only":
            emit_update_only(rows, fh)
        else:
            emit_migration(
                rows,
                fh,
                package=args.package,
                file_name=args.file_name,
                environment=args.environment,
                notes=args.notes,
            )
    print(f"Escrito {args.output} ({len(rows)} municípios).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
