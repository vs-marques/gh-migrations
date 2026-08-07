"""
Liga logradouros (CEP Aberto) a geography.streets e preenche geography.postal_codes.street_id.

Mesmos CSVs do import_cep_aberto_postal_codes.py. Para cada linha válida com logradouro não vazio:
1) INSERT em geography.streets (city_id, street_type, name) com ON CONFLICT DO UPDATE (bump updated_at);
2) UPDATE geography.postal_codes SET street_id = … pelo CEP + cidade + tipo+nome do logradouro.

Heurística de tipo: prefixos comuns (Rua, Avenida, …); senão street_type '' e nome = texto inteiro (até 255 chars).

Conexão: GEOGRAPHY_DATABASE_URL ou --dsn.

  python scripts/import_cep_aberto_streets.py --root "C:/Users/.../Downloads/cepaberto"
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import cep_aberto_csv as cab  # noqa: E402

UPSERT_STREETS = """
INSERT INTO geography.streets (city_id, street_type, name)
SELECT DISTINCT c.id,
       COALESCE(NULLIF(trim(v.styp), ''), '')::varchar(64),
       left(trim(v.nm), 255)::varchar(255)
FROM (VALUES %s) AS v(cep, ext_id, styp, nm, nb, co)
JOIN geography.cities c ON c.external_code = v.ext_id::integer
WHERE trim(v.nm) <> ''
ON CONFLICT (city_id, street_type, name) DO UPDATE SET
  updated_at = NOW()
"""

UPDATE_POSTAL = """
UPDATE geography.postal_codes AS p
SET street_id = s.id, updated_at = NOW()
FROM (VALUES %s) AS v(cep, ext_id, styp, nm, nb, co)
JOIN geography.cities c ON c.external_code = v.ext_id::integer
JOIN geography.streets s
  ON s.city_id = c.id
 AND s.street_type = COALESCE(NULLIF(trim(v.styp), ''), '')::varchar(64)
 AND s.name = left(trim(v.nm), 255)::varchar(255)
WHERE p.cep = v.cep::char(8)
  AND trim(v.nm) <> ''
"""


def row_to_batch_tuple(
    cep: str, ext_id: int, log: str, nb: str | None, co: str | None
) -> tuple[str, int, str, str, str | None, str | None]:
    styp, nm = cab.split_street_type_name(log)
    return (cep, ext_id, styp, nm, nb, co)


def import_file(cur, path: Path, batch_size: int, delimiter: str | None, verbose: bool) -> tuple[int, int]:
    """Returns (street_stmt_rowcount_sum, update_postal_rowcount_sum)."""
    st_total = 0
    up_total = 0
    batch: list[tuple[str, int, str, str, str | None, str | None]] = []
    tpl = "(%s::text, %s::int, %s::text, %s::text, %s::text, %s::text)"

    def flush() -> None:
        nonlocal st_total, up_total, batch
        if not batch:
            return
        # Um CEP por batch: evita UPDATE ambíguo se o CSV repetir o mesmo CEP.
        dedup: dict[str, tuple[str, int, str, str, str | None, str | None]] = {}
        for t in batch:
            dedup[t[0]] = t
        batch2 = list(dedup.values())
        execute_values(cur, UPSERT_STREETS, batch2, template=tpl, page_size=len(batch2))
        st_total += cur.rowcount
        execute_values(cur, UPDATE_POSTAL, batch2, template=tpl, page_size=len(batch2))
        up_total += cur.rowcount
        batch.clear()

    for row in cab.iter_cepaberto_rows(path, delimiter=delimiter, verbose=verbose):
        cep, ext_id, log, nb, co = row
        batch.append(row_to_batch_tuple(cep, ext_id, log, nb, co))
        if len(batch) >= batch_size:
            flush()
    flush()
    return st_total, up_total


def main() -> int:
    p = argparse.ArgumentParser(description="Importa logradouros CEP Aberto → streets + postal_codes.street_id")
    p.add_argument("--root", type=Path, required=True, help="Pasta raiz CEP Aberto (subpastas UF)")
    p.add_argument(
        "--dsn",
        default=os.environ.get("GEOGRAPHY_DATABASE_URL", ""),
        help="PostgreSQL DSN (default: GEOGRAPHY_DATABASE_URL)",
    )
    p.add_argument("--batch-size", type=int, default=4000)
    p.add_argument("--ufs", default="", help="UFs separadas por vírgula (opcional)")
    p.add_argument("--delimiter", default="", help="Força separador CSV (, ; tab)")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    root = args.root.expanduser()
    if not root.is_dir():
        print("ERRO: --root inválido:", root, file=sys.stderr)
        return 1
    dsn = (args.dsn or "").strip()
    if not dsn:
        print("ERRO: GEOGRAPHY_DATABASE_URL ou --dsn", file=sys.stderr)
        return 1

    uf_filter = {u.strip().upper() for u in args.ufs.split(",") if u.strip()}
    subdirs = sorted(d for d in root.iterdir() if d.is_dir())
    if uf_filter:
        subdirs = [d for d in subdirs if d.name.upper() in uf_filter]

    files: list[Path] = []
    for d in subdirs:
        for f in sorted(d.iterdir()):
            if not f.is_file() or f.suffix.lower() != ".csv":
                continue
            if "cepaberto" not in f.name.lower():
                continue
            files.append(f)

    delim_force: str | None = None
    if args.delimiter.strip():
        d = args.delimiter.strip()
        delim_force = "\t" if d.lower() in ("tab", "\\t") else d[0]

    if not files:
        print("Nenhum CSV encontrado.")
        return 1

    print("Arquivos:", len(files))
    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = False
        g_st, g_up = 0, 0
        for fp in files:
            with conn.cursor() as cur:
                st, up = import_file(cur, fp, args.batch_size, delim_force, args.verbose)
            conn.commit()
            g_st += st
            g_up += up
            print(f"  {fp.relative_to(root)} -> streets rowcount={st}, postal_codes atualizados={up}")
        print("Total streets (INSERT/UPSERT linhas):", g_st)
        print("Total postal_codes (UPDATE linhas):", g_up)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
