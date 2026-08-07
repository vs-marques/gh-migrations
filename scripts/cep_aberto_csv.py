"""Leitura comum dos CSVs CEP Aberto (faixas / logradouros)."""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def norm_cep(raw: str) -> str | None:
    d = "".join(ch for ch in raw.strip() if ch.isdigit())
    if len(d) > 8:
        d = d[:8]
    if len(d) < 8:
        d = d.zfill(8)
    if len(d) != 8:
        return None
    return d


def read_text_prefix(path: Path, max_bytes: int = 65536) -> tuple[str, str]:
    raw = path.read_bytes()[:max_bytes]
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace"), "latin-1"


def sniff_csv_delimiter(sample: str) -> str:
    sample = sample.lstrip("\ufeff").strip()
    if not sample:
        return ","
    head = sample[:8192]
    try:
        d = csv.Sniffer().sniff(head, delimiters=";\t,")
        if d.delimiter in ";,\t":
            return d.delimiter
    except csv.Error:
        pass
    line = head.splitlines()[0] if head else ""
    if line.count(";") >= 5 or (line.count(";") > line.count(",") and ";" in line):
        return ";"
    if line.count("\t") >= 5:
        return "\t"
    return ","


def split_street_type_name(logradouro: str | None) -> tuple[str, str]:
    """
    Separa tipo curto + nome (heurística simples). Tipo vazio vira '' para bater na UNIQUE
    (city_id, street_type, name) sem NULL duplicado.
    """
    raw = (logradouro or "").strip()
    if not raw:
        return "", ""
    prefixes = (
        "Avenida",
        "Rodovia",
        "Travessa",
        "Alameda",
        "Estrada",
        "Praça",
        "Praca",
        "Conjunto",
        "Quadra",
        "Chácara",
        "Chacara",
        "Sítio",
        "Sitio",
        "Jardim",
        "Parque",
        "Servidão",
        "Servidao",
        "Passagem",
        "Caminho",
        "Largo",
        "Vila",
        "Beco",
        "Via",
        "Rua",
        "Av.",
        "Av ",
    )
    for p in sorted(prefixes, key=len, reverse=True):
        pl = len(p)
        if len(raw) >= pl and raw[:pl].upper() == p.upper():
            if len(raw) == pl or raw[pl] in " \t,.;-":
                rest = raw[pl:].strip().lstrip(",.;-").strip()
                nm = (rest or raw)[:255]
                return p[:64], nm
    return "", raw[:255]


def parse_cep_row(parts: list[str]) -> tuple[str, int, str, str | None, str | None] | None:
    """cep, logradouro, complemento, bairro, localidade_id, ativo -> cep, ext_id, log, nb, co"""
    if len(parts) < 6:
        return None
    cep_raw, log, complemento, bairro, loc_raw, ativo = (
        parts[0],
        parts[1],
        parts[2],
        parts[3],
        parts[4],
        parts[5],
    )
    a = (ativo or "").strip().lower()
    if a in ("0", "false", "f", "n", "no", "inativo", "nao", "não", "n\u00e3o"):
        return None
    cep = norm_cep(cep_raw)
    if not cep:
        return None
    try:
        ext_id = int(loc_raw.strip())
    except ValueError:
        return None
    nb = (bairro or "").strip() or None
    co = (complemento or "").strip() or None
    return (cep, ext_id, (log or "").strip(), nb, co)


def iter_cepaberto_rows(
    path: Path, delimiter: str | None = None, verbose: bool = False
) -> tuple[str, int, str, str | None, str | None]:
    prefix, encoding = read_text_prefix(path)
    delim = delimiter if delimiter is not None else sniff_csv_delimiter(prefix)
    if delim == "\\t":
        delim = "\t"
    if verbose:
        print(f"    [debug] {path.name}: encoding={encoding!r} delimiter={delim!r}", file=sys.stderr)
    with path.open(newline="", encoding=encoding, errors="replace") as f:
        for parts in csv.reader(f, delimiter=delim):
            if not parts or all(not (c or "").strip() for c in parts):
                continue
            row = parse_cep_row(parts)
            if row:
                yield row
