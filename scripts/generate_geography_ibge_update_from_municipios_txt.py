"""
Lê nyoka-migrations/docs/municipios.txt (formato: código TAB nome) e gera SQL
com UPDATE em massa em geography.cities.ibge_municipality_code.

A UF resolve-se pelo prefixo numérico IBGE do município: states.ibge_state_code = (codigo / 100000).

Uso (a partir da pasta nyoka-migrations)::

  python scripts/generate_geography_ibge_update_from_municipios_txt.py

Saídas por defeito (pastas criadas se não existirem)::

  migrations/geography/desenvolvimento/2026/Maio/21.05.2026/PKG_DSV_GE_V1_00006_GEOGRAPHY/01-GEOGRAPHY-IBGE-UPD.sql
  migrations/geography/produção/2026/Maio/21.05.2026/PKG_PRD_GE_V1_00006_GEOGRAPHY/01-GEOGRAPHY-IBGE-UPD.sql
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, TextIO

LINE_RE = re.compile(r"^\s*(\d+)\s+(.+?)\s*$")

MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


def _load_json_http(url: str, timeout: int) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "nyoka-migrations/ibge_txt_generator"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def fetch_ibge_codigo_nome(timeout: int) -> list[tuple[int, str]]:
    data = _load_json_http(MUNICIPIOS_URL, timeout=timeout)
    if not isinstance(data, list):
        raise RuntimeError("Resposta IBGE inesperada (esperado array)")
    out: list[tuple[int, str]] = []
    for m in data:
        if not isinstance(m, dict):
            continue
        nome = (m.get("nome") or "").strip()
        mid = m.get("id")
        if not nome or mid is None:
            continue
        out.append((int(mid), nome))
    out.sort(key=lambda t: (t[0], t[1]))
    return out


def sql_str(s: str) -> str:
    return "'" + s.replace("\\", "\\\\").replace("'", "''") + "'"


def load_rows(path: Path) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    raw = path.read_text(encoding="utf-8")
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            code_s, name = line.split("\t", 1)
            code_s, name = code_s.strip(), name.strip()
        else:
            m = LINE_RE.match(line)
            if not m:
                print(f"Ignorada linha não reconhecida: {line[:80]!r}", file=sys.stderr)
                continue
            code_s, name = m.group(1), m.group(2).strip()
        rows.append((int(code_s), name))
    rows.sort(key=lambda t: (t[0], t[1]))
    return rows


def emit_update_values(rows: list[tuple[int, str]], fh: TextIO) -> None:
    fh.write(
        "-- geography.cities: preencher ibge_municipality_code a partir da lista IBGE (código + nome).\n"
        "-- Junção à UF: geography.states.ibge_state_code = (src.codigo / 100000).\n"
        "UPDATE geography.cities AS c\n"
        "SET\n"
        "    ibge_municipality_code = src.codigo,\n"
        "    updated_at = NOW()\n"
        "FROM (\n"
        "    VALUES\n"
    )
    for i, (cod, nome) in enumerate(rows):
        sep = ",\n" if i + 1 < len(rows) else "\n"
        fh.write(f"        ({cod}, {sql_str(nome)}){sep}")
    fh.write(
        ") AS src(codigo, nome_ibge)\n"
        "JOIN geography.states AS s\n"
        "  ON s.ibge_state_code = (src.codigo / 100000)\n"
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
    rows: list[tuple[int, str]],
    out: Path,
    *,
    package: str,
    environment: str,
    file_name: str,
    notes: str,
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    today = date.today().strftime("%d/%m/%Y")
    iso = date.today().isoformat()
    with out.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(
            f"-- =====================================================\n"
            f"-- Migration: {package}\n"
            f"-- Arquivo: {file_name}\n"
            f"-- Data: {today}\n"
            f"-- Banco destino: GE (schema geography) — ver MIGRATIONS_MASTER_REFERENCE.md\n"
            f"-- Descrição: UPDATE geography.cities.ibge_municipality_code (lista oficial IBGE em docs/municipios.txt).\n"
            f"--   Junção: states.ibge_state_code = (codigo_municipio / 100000); nome com lower(trim()).\n"
            f"-- Dependência: PKG_*_GE_V1_00001_GEOGRAPHY, PKG_*_GE_V1_00002_GEOGRAPHY.\n"
            f"-- Fonte: docs/municipios.txt (regenerado em {iso}).\n"
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
            f"-- =====================================================\n"
            f"-- UPDATE IBGE (municípios)\n"
            f"-- =====================================================\n\n"
        )
        emit_update_values(rows, fh)
        fh.write(
            f"\nSELECT superadmin.log_migration_step(\n"
            f"    '{package}', 'INFO', 'UPDATE ibge_municipality_code aplicado (docs/municipios.txt).'\n"
            f");\n\n"
            f"COMMIT;\n\n"
            f"SELECT 'MIGRATION CONCLUIDA: {package} - ' || NOW() AS log_entry;\n"
        )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--input",
        type=Path,
        default=root / "docs" / "municipios.txt",
        help="Ficheiro código TAB nome",
    )
    p.add_argument("--dsv-out", type=Path, default=None)
    p.add_argument("--prd-out", type=Path, default=None)
    args = p.parse_args()

    inp = args.input if args.input.is_absolute() else root / args.input
    if not inp.is_file():
        print(f"Ficheiro inexistente: {inp}", file=sys.stderr)
        return 1

    rows = load_rows(inp)
    if len(rows) < 5500:
        print(f"Aviso: só {len(rows)} linhas (esperado ~5570).", file=sys.stderr)

    dsv_out = args.dsv_out or (
        root
        / "migrations/geography/desenvolvimento/2026/Maio/21.05.2026/PKG_DSV_GE_V1_00006_GEOGRAPHY/01-GEOGRAPHY-IBGE-UPD.sql"
    )
    prd_out = args.prd_out or (
        root
        / "migrations/geography/produção/2026/Maio/21.05.2026/PKG_PRD_GE_V1_00006_GEOGRAPHY/01-GEOGRAPHY-IBGE-UPD.sql"
    )

    emit_migration(
        rows,
        dsv_out,
        package="PKG_DSV_GE_V1_00006_GEOGRAPHY",
        environment="desenvolvimento",
        file_name="01-GEOGRAPHY-IBGE-UPD.sql",
        notes="UPD: ibge_municipality_code em cities (docs/municipios.txt). GE.",
    )
    emit_migration(
        rows,
        prd_out,
        package="PKG_PRD_GE_V1_00006_GEOGRAPHY",
        environment="producao",
        file_name="01-GEOGRAPHY-IBGE-UPD.sql",
        notes="UPD: ibge_municipality_code em cities (docs/municipios.txt). GE.",
    )
    print(f"DSV: {dsv_out} ({len(rows)} municípios)")
    print(f"PRD: {prd_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
