"""
Importa arquivos IBGE *faces_de_logradouros_2022.json* para geography.cartography_*.

Cada arquivo é um GeoJSON FeatureCollection (geralmente LineString por face de quadra).
Nome esperado: ``{codigo_ibge_municipio}_faces_de_logradouros_2022.json`` (7 dígitos).

Dados gravados na camada ``ibge_faces_logradouros_2022``:
  - geom: ST_SetSRID(ST_GeomFromGeoJSON(...), 4326)
  - external_key: ``{ibge}|{CD_SETOR}|{CD_QUADRA}|{CD_FACE}``
  - name: logradouro curto (tipo + nome), truncado a 500 caracteres
  - properties: atributos originais + ``ibge_municipality_code`` (string)

Idempotência: por arquivo, em uma transação, remove feições existentes dessa camada
com ``properties.ibge_municipality_code`` igual ao código do arquivo e reinsere.

Layout de ``--root``:
  - Pastas por UF (ex.: ``IBGE/AC/1200435_....json``), ou
  - Arquivos soltos na raiz; o script busca recursivamente ``*_faces_de_logradouros_2022.json``.

Conexão: ``GEOGRAPHY_DATABASE_URL`` ou ``--dsn``.

Exemplo (PowerShell)::

  $env:GEOGRAPHY_DATABASE_URL = "postgresql://user:pass@host:5432/ge_db"
  python scripts/import_ibge_faces_logradouros.py --root "C:/Users/.../Downloads/IBGE"

Checagem de município: por defeito só importa se existir ``geography.cities.ibge_municipality_code``
igual ao código do ficheiro. O seed CEP Aberto (``01-GEOGRAPHY-SEED.sql``) hoje preenche
``external_code`` e deixa ``ibge_municipality_code`` a NULL — nesse caso use
``--allow-unknown-city`` até haver backfill do código IBGE nas cidades.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

LAYER_KEY = "ibge_faces_logradouros_2022"
FILE_RE = re.compile(r"^(\d{7})_faces_de_logradouros_2022\.json$", re.IGNORECASE)

INSERT_SQL = """
INSERT INTO geography.cartography_features (layer_id, external_key, name, geom, properties)
SELECT v.layer_id::uuid, v.ext_key,
       CASE WHEN length(v.nm) > 500 THEN left(v.nm, 500) ELSE v.nm END::varchar(500),
       ST_SetSRID(ST_GeomFromGeoJSON(v.geojson::text), 4326),
       v.props::jsonb
FROM (VALUES %s) AS v(layer_id, ext_key, nm, geojson, props)
"""


def ensure_layer(cur) -> str:
    cur.execute(
        """
        INSERT INTO geography.cartography_layers (layer_key, title, description, srid, meta, is_active)
        VALUES (
            %s,
            'IBGE — Faces de logradouros (2022)',
            'Malha urbana (faces de quadra); fonte IBGE/CNEFE, geometria em EPSG:4326.',
            4326,
            '{"provider":"IBGE","dataset":"faces_de_logradouros","vintage":2022}'::jsonb,
            true
        )
        ON CONFLICT (layer_key) DO NOTHING
        """,
        (LAYER_KEY,),
    )
    cur.execute(
        "SELECT id::text FROM geography.cartography_layers WHERE layer_key = %s",
        (LAYER_KEY,),
    )
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Camada {LAYER_KEY!r} não encontrada após INSERT")
    return row[0]


def city_exists(cur, ibge: int) -> bool:
    cur.execute(
        "SELECT 1 FROM geography.cities WHERE ibge_municipality_code = %s LIMIT 1",
        (ibge,),
    )
    return cur.fetchone() is not None


def any_city_has_ibge_code(cur) -> bool:
    cur.execute(
        "SELECT 1 FROM geography.cities WHERE ibge_municipality_code IS NOT NULL LIMIT 1"
    )
    return cur.fetchone() is not None


def build_display_name(props: dict[str, Any]) -> str:
    tip = (props.get("NM_TIP_LOG") or "").strip()
    tit = (props.get("NM_TIT_LOG") or "").strip()
    nom = (props.get("NM_LOG") or "").strip()
    parts = [p for p in (tip, tit, nom) if p]
    return " ".join(parts) if parts else ""


def iter_geojson_files(root: Path) -> list[Path]:
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if FILE_RE.match(p.name):
            out.append(p)
    return sorted(out)


def import_one_file(
    cur,
    layer_id: str,
    path: Path,
    ibge: int,
    batch_size: int,
    require_city: bool,
) -> tuple[int, int]:
    """
    Returns (features_inserted, features_skipped_geom).
    """
    if require_city and not city_exists(cur, ibge):
        return 0, 0

    with path.open(encoding="utf-8-sig") as fh:
        doc = json.load(fh)

    feats = doc.get("features") or []
    if not isinstance(feats, list):
        return 0, 0

    ibge_s = str(ibge)
    cur.execute(
        """
        DELETE FROM geography.cartography_features f
        USING geography.cartography_layers l
        WHERE f.layer_id = l.id
          AND l.layer_key = %s
          AND f.properties->>'ibge_municipality_code' = %s
        """,
        (LAYER_KEY, ibge_s),
    )

    batch: list[tuple[str, str, str, str, str]] = []
    inserted = 0
    skipped = 0
    tpl = "(%s::uuid, %s::text, %s::text, %s::text, %s::text)"

    for feat in feats:
        if not isinstance(feat, dict) or feat.get("type") != "Feature":
            continue
        geom = feat.get("geometry")
        if not isinstance(geom, dict):
            skipped += 1
            continue
        gtype = geom.get("type")
        coords = geom.get("coordinates")
        if gtype not in ("LineString", "MultiLineString", "Point", "MultiPoint") or coords is None:
            skipped += 1
            continue

        props_raw = feat.get("properties")
        props: dict[str, Any] = dict(props_raw) if isinstance(props_raw, dict) else {}
        props["ibge_municipality_code"] = ibge_s

        cd_setor = str(props.get("CD_SETOR") or "").strip()
        cd_quadra = str(props.get("CD_QUADRA") or "").strip()
        cd_face = str(props.get("CD_FACE") or "").strip()
        ext_key = "|".join((ibge_s, cd_setor, cd_quadra, cd_face))
        if len(ext_key) > 255:
            ext_key = ext_key[:255]

        name = build_display_name(props)
        geojson = json.dumps(geom, separators=(",", ":"), ensure_ascii=False)
        props_json = json.dumps(props, separators=(",", ":"), ensure_ascii=False)

        batch.append((layer_id, ext_key, name, geojson, props_json))
        if len(batch) >= batch_size:
            execute_values(cur, INSERT_SQL, batch, template=tpl, page_size=len(batch))
            inserted += len(batch)
            batch.clear()

    if batch:
        execute_values(cur, INSERT_SQL, batch, template=tpl, page_size=len(batch))
        inserted += len(batch)

    return inserted, skipped


def main() -> int:
    p = argparse.ArgumentParser(
        description="Importa JSON IBGE faces_de_logradouros_2022 em geography.cartography_features"
    )
    p.add_argument(
        "--root",
        type=Path,
        required=True,
        help='Pasta raiz (ex.: C:/Users/.../Downloads/IBGE); busca recursiva por "*_faces_de_logradouros_2022.json"',
    )
    p.add_argument(
        "--dsn",
        default=os.environ.get("GEOGRAPHY_DATABASE_URL", ""),
        help="DSN PostgreSQL (default: env GEOGRAPHY_DATABASE_URL)",
    )
    p.add_argument("--batch-size", type=int, default=800, help="Feições por INSERT batelado")
    p.add_argument(
        "--ufs",
        default="",
        help="Opcional: UFs (nome de pasta, ex.: AC,TO). Filtra caminho que contenha /UF/ ou \\UF\\",
    )
    p.add_argument(
        "--allow-unknown-city",
        action="store_true",
        help="Importa mesmo se o código IBGE do arquivo não existir em geography.cities",
    )
    p.add_argument(
        "--limit-files",
        type=int,
        default=0,
        help="Processa no máximo N arquivos (0 = sem limite), útil para teste",
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

    files = iter_geojson_files(root)
    uf_filter = {u.strip().upper() for u in args.ufs.split(",") if u.strip()}
    if uf_filter:
        sep = os.sep

        def in_uf(fp: Path) -> bool:
            parts = {x.upper() for x in fp.parts}
            return bool(parts & uf_filter)

        files = [f for f in files if in_uf(f)]

    if args.limit_files > 0:
        files = files[: args.limit_files]

    if not files:
        print("Nenhum arquivo *_faces_de_logradouros_2022.json em", root)
        return 1

    require_city = not args.allow_unknown_city
    print("Arquivos:", len(files))

    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            db_has_ibge = any_city_has_ibge_code(cur)
        conn.commit()

        if require_city and not db_has_ibge:
            print(
                "AVISO: nenhuma linha em geography.cities com ibge_municipality_code preenchido "
                "(seed CEP Aberto só popula external_code). A validação por IBGE ignora todos os "
                "ficheiros até haver backfill ou use --allow-unknown-city.",
                file=sys.stderr,
            )

        layer_id: str | None = None
        total_ins = 0
        total_skip = 0
        total_skip_city = 0

        for fp in files:
            m = FILE_RE.match(fp.name)
            if not m:
                continue
            ibge = int(m.group(1))

            with conn.cursor() as cur:
                if layer_id is None:
                    layer_id = ensure_layer(cur)
                assert layer_id is not None

                if require_city and not city_exists(cur, ibge):
                    why = (
                        " [ibge_municipality_code vazio no seed — use --allow-unknown-city]"
                        if not db_has_ibge
                        else " [sem linha com este código IBGE]"
                    )
                    print(f"  {fp} -> ignorado (município {ibge}){why}")
                    total_skip_city += 1
                    conn.commit()
                    continue

                try:
                    ins, sk = import_one_file(
                        cur, layer_id, fp, ibge, args.batch_size, require_city=False
                    )
                except psycopg2.Error as e:
                    conn.rollback()
                    print(f"  ERRO {fp}: {e}", file=sys.stderr)
                    raise

            conn.commit()
            total_ins += ins
            total_skip += sk
            try:
                rel = fp.relative_to(root)
            except ValueError:
                rel = fp
            print(f"  {rel} -> {ins} inseridas, {sk} geometrias ignoradas (tipo/vazio)")

        print("Total feições inseridas:", total_ins)
        print("Total geometrias ignoradas:", total_skip)
        if require_city:
            print("Arquivos ignorados (cidade desconhecida):", total_skip_city)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
