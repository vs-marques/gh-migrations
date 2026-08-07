"""
Importação em massa dos CSVs CEP Aberto (faixas) para geography.postal_codes.

Layout esperado (pasta --root):
  AC/ac.cepaberto_parte_1.csv
  SP/sp.cepaberto_parte_3.csv
  ...

Formato de linha (sem cabeçalho), separador `,` ou `;`:
  cep,logradouro,complemento,bairro,localidade_id,ativo

- city_id: JOIN geography.cities c ON c.external_code = localidade_id (inteiro do CSV).
- street_id: sempre NULL (use import_cep_aberto_streets.py para ligar logradouros).
- neighborhood_name / complement_hint: bairro / complemento (truncados a 255).
- Delimitador / encoding: ver cep_aberto_csv.py.

Conexão: variável de ambiente GEOGRAPHY_DATABASE_URL (ou --dsn).

Exemplo:
  set GEOGRAPHY_DATABASE_URL=postgresql://user:pass@host:5432/ge_db
  python scripts/import_cep_aberto_postal_codes.py --root "C:/Users/victo/Downloads/cepaberto"
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

INSERT_SQL = """
INSERT INTO geography.postal_codes (cep, city_id, street_id, neighborhood_name, complement_hint)
SELECT v.cep::char(8), c.id, NULL,
       CASE WHEN length(v.nb) > 255 THEN left(v.nb, 255) ELSE v.nb END::varchar(255),
       CASE WHEN length(v.co) > 255 THEN left(v.co, 255) ELSE v.co END::varchar(255)
FROM (VALUES %s) AS v(cep, ext_id, nb, co)
JOIN geography.cities c ON c.external_code = v.ext_id::integer
ON CONFLICT (cep) DO UPDATE SET
  city_id = EXCLUDED.city_id,
  neighborhood_name = EXCLUDED.neighborhood_name,
  complement_hint = EXCLUDED.complement_hint,
  updated_at = NOW()
"""


def import_file(cur, path: Path, batch_size: int, delimiter: str | None, verbose: bool) -> int:
    """Returns total rowcount reported by PostgreSQL for batched INSERT..ON CONFLICT."""
    batch: list[tuple[str, int, str | None, str | None]] = []
    total = 0
    tpl = "(%s::text, %s::int, %s::text, %s::text)"

    for row in cab.iter_cepaberto_rows(path, delimiter=delimiter, verbose=verbose):
        cep, ext_id, _log, nb, co = row
        batch.append((cep, ext_id, nb, co))
        if len(batch) >= batch_size:
            execute_values(cur, INSERT_SQL, batch, template=tpl, page_size=len(batch))
            total += cur.rowcount
            batch.clear()
    if batch:
        execute_values(cur, INSERT_SQL, batch, template=tpl, page_size=len(batch))
        total += cur.rowcount
    return total


def main() -> int:
    p = argparse.ArgumentParser(description="Importa CSVs CEP Aberto em geography.postal_codes")
    p.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Pasta raiz (ex.: C:/Users/.../Downloads/cepaberto) com subpastas UF",
    )
    p.add_argument(
        "--dsn",
        default=os.environ.get("GEOGRAPHY_DATABASE_URL", ""),
        help="DSN PostgreSQL (default: env GEOGRAPHY_DATABASE_URL)",
    )
    p.add_argument("--batch-size", type=int, default=4000, help="Linhas por INSERT batelado")
    p.add_argument(
        "--ufs",
        default="",
        help="Opcional: UFs separadas por vírgula (ex.: AC,SP). Vazio = todas as pastas",
    )
    p.add_argument(
        "--delimiter",
        default="",
        help="Força separador CSV (um caractere: , ou ; ou tab). Vazio = detectar por arquivo",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Imprime encoding e delimitador detectados por arquivo",
    )
    args = p.parse_args()
    root: Path = args.root.expanduser()
    if not root.is_dir():
        print("ERRO: --root não é diretório:", root, file=sys.stderr)
        return 1
    dsn = (args.dsn or "").strip()
    if not dsn:
        print("ERRO: defina GEOGRAPHY_DATABASE_URL ou passe --dsn", file=sys.stderr)
        return 1

    uf_filter = {u.strip().upper() for u in args.ufs.split(",") if u.strip()}

    subdirs = sorted(d for d in root.iterdir() if d.is_dir())
    if uf_filter:
        subdirs = [d for d in subdirs if d.name.upper() in uf_filter]

    files: list[Path] = []
    for d in subdirs:
        for f in sorted(d.iterdir()):
            if not f.is_file():
                continue
            if f.suffix.lower() != ".csv":
                continue
            if "cepaberto" not in f.name.lower():
                continue
            files.append(f)

    delim_force: str | None = None
    if args.delimiter.strip():
        d = args.delimiter.strip()
        delim_force = "\t" if d.lower() in ("tab", "\\t") else d[0]

    if not files:
        print("Nenhum .csv encontrado em", root)
        return 1

    print("Arquivos:", len(files))
    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = False
        grand = 0
        for fp in files:
            with conn.cursor() as cur:
                n = import_file(cur, fp, args.batch_size, delim_force, args.verbose)
            conn.commit()
            grand += n
            print(f"  {fp.relative_to(root)} -> {n} linhas afetadas (INSERT/UPDATE)")
        print("Total linhas afetadas (soma por arquivo, ON CONFLICT conta updates):", grand)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
