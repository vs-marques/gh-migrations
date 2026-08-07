"""
Preenche geography.cities.ibge_municipality_code (sede) e parent_city_id (distritos CEP Aberto).

1) Descarrega todos os municípios oficiais do IBGE (API localidades).
2) Fase A: UPDATE nas linhas cuja geography.cities.name coincide com o nome IBGE na mesma UF (sedes).
3) Fase B: UPDATE parent_city_id em linhas ``Distrito (Sede)`` → linha sede com mesmo state_id e nome = texto entre parêntesis.

O UNIQUE (ibge_municipality_code) exige **um** código por município: distritos **não** recebem ibge; ficam ligados ao sede.

Conexão: GEOGRAPHY_DATABASE_URL ou --dsn.

Exemplo::

  set GEOGRAPHY_DATABASE_URL=postgresql://user:pass@host:5432/ge
  python scripts/backfill_geography_cities_ibge.py --dry-run
  python scripts/backfill_geography_cities_ibge.py
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

try:
    import psycopg2
    from psycopg2.extensions import connection as PgConnection
except ImportError as e:  # pragma: no cover
    raise SystemExit("Instale psycopg2: pip install psycopg2-binary") from e

MUNICIPIOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"


def _load_json_http(url: str, timeout: int) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "nyoka-migrations/backfill_geography_cities_ibge"})
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
            return str(cur).strip().upper() or None
        except (KeyError, TypeError):
            continue
    return None


def fetch_ibge_rows(timeout: int) -> list[tuple[str, str, int]]:
    data = _load_json_http(MUNICIPIOS_URL, timeout=timeout)
    if not isinstance(data, list):
        raise RuntimeError("Resposta IBGE inesperada (esperado array de municípios)")
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
    return out


def phase_a_exact_ibge(conn: PgConnection, rows: list[tuple[str, str, int]], dry_run: bool) -> int:
    """
    Atribui ibge_municipality_code onde (UF, nome da cidade) coincide com o município IBGE.
    Evita violar UNIQUE se já existir outra linha com o mesmo código.
    """
    sql = """
        UPDATE geography.cities ci
        SET ibge_municipality_code = %(ibge)s, updated_at = NOW()
        FROM geography.states st
        WHERE ci.state_id = st.id
          AND st.uf = %(uf)s
          AND lower(trim(ci.name)) = lower(trim(%(nome)s))
          AND (ci.ibge_municipality_code IS DISTINCT FROM %(ibge)s)
          AND NOT EXISTS (
              SELECT 1
              FROM geography.cities other
              WHERE other.ibge_municipality_code = %(ibge)s
                AND other.id <> ci.id
          )
    """
    total = 0
    cur = conn.cursor()
    for uf, nome, ibge in rows:
        if dry_run:
            cur.execute(
                """
                SELECT COUNT(*)::int
                FROM geography.cities ci
                JOIN geography.states st ON st.id = ci.state_id
                WHERE st.uf = %s
                  AND lower(trim(ci.name)) = lower(trim(%s))
                  AND (ci.ibge_municipality_code IS DISTINCT FROM %s)
                  AND NOT EXISTS (
                      SELECT 1 FROM geography.cities o
                      WHERE o.ibge_municipality_code = %s AND o.id <> ci.id
                  )
                """,
                (uf, nome, ibge, ibge),
            )
            total += int(cur.fetchone()[0])
        else:
            cur.execute(sql, {"uf": uf, "nome": nome, "ibge": ibge})
            total += cur.rowcount
    cur.close()
    return total


def phase_b_parent_district(conn: PgConnection, dry_run: bool) -> int:
    sql = """
        UPDATE geography.cities child
        SET parent_city_id = parent.id, updated_at = NOW()
        FROM geography.cities parent
        WHERE child.parent_city_id IS NULL
          AND child.ibge_municipality_code IS NULL
          AND parent.ibge_municipality_code IS NOT NULL
          AND parent.parent_city_id IS NULL
          AND child.state_id = parent.state_id
          AND child.id <> parent.id
          AND child.name ~ '\\([^)]+\\)\\s*$'
          AND btrim(substring(child.name from '\\(([^)]+)\\)\\s*$')) = btrim(parent.name)
    """
    cur = conn.cursor()
    if dry_run:
        cur.execute(
            """
            SELECT COUNT(*)::int
            FROM geography.cities child
            JOIN geography.cities parent ON parent.state_id = child.state_id
            WHERE child.parent_city_id IS NULL
              AND child.ibge_municipality_code IS NULL
              AND parent.ibge_municipality_code IS NOT NULL
              AND parent.parent_city_id IS NULL
              AND child.id <> parent.id
              AND child.name ~ '\\([^)]+\\)\\s*$'
              AND btrim(substring(child.name from '\\(([^)]+)\\)\\s*$')) = btrim(parent.name)
            """
        )
        n = int(cur.fetchone()[0])
        cur.close()
        return n
    cur.execute(sql)
    n = cur.rowcount
    cur.close()
    return n


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dsn", default=os.environ.get("GEOGRAPHY_DATABASE_URL"), help="DSN Postgres (GE)")
    p.add_argument("--timeout", type=int, default=300, help="Timeout HTTP IBGE (s)")
    p.add_argument("--dry-run", action="store_true", help="Só contar linhas afetadas, sem UPDATE")
    p.add_argument("--skip-parent", action="store_true", help="Não executar fase B (parent_city_id)")
    args = p.parse_args()
    if not args.dsn:
        print("Defina GEOGRAPHY_DATABASE_URL ou --dsn", file=sys.stderr)
        return 2

    print("A descarregar municípios IBGE…")
    ibge_rows = fetch_ibge_rows(args.timeout)
    print(f"  → {len(ibge_rows)} municípios na API")

    conn = psycopg2.connect(args.dsn)
    try:
        n_a = phase_a_exact_ibge(conn, ibge_rows, args.dry_run)
        print(f"Fase A (ibge na sede): {'linhas ' if args.dry_run else ''}{n_a} {'afetadas' if args.dry_run else 'UPDATE(s)'}")
        if not args.skip_parent:
            n_b = phase_b_parent_district(conn, args.dry_run)
            print(
                f"Fase B (parent_city_id distrito→sede): {'linhas ' if args.dry_run else ''}{n_b} {'afetadas' if args.dry_run else 'UPDATE(s)'}"
            )
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, RuntimeError) as e:
        conn.rollback()
        print(f"Erro: {e}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
