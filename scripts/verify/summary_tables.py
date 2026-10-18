"""Parser for results/analysis/summary.md: every table cell of the form '(k/n)' keyed by section, row and column, so
the re-computation can be compared with it cell by cell."""

import re

from common import RES

KN = re.compile(r"\((\d+)/(\d+)\)")


def parse(path=RES / "analysis" / "summary.md") -> dict:
    """{section: [(row_key_tuple, {column: (k, n)})]}; row key: the cells without a (k/n) value."""
    out, section, header = {}, None, None
    for line in open(path, encoding="utf-8"):
        line = line.rstrip("\n")
        if line.startswith("#"):
            section, header = line.lstrip("#").strip(), None
            continue
        if not line.startswith("|"):
            header = None if not line.strip() else header
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if header is None:
            header = cells
            continue
        if set(line) <= set("|-"):
            continue
        key, vals = [], {}
        for h, c in zip(header, cells):
            m = KN.search(c)
            if m:
                vals[h] = (int(m.group(1)), int(m.group(2)))
            else:
                key.append(c)
        out.setdefault(section, []).append((tuple(key), vals))
    return out


def compare(name: str, section_rows: list, mine: dict, key_len: int = 1) -> list[str]:
    """mine: {row_key_tuple: {column: (k, n)}}. Returns mismatch lines (empty: all cells agree)."""
    bad, seen = [], 0
    for key, vals in section_rows:
        key = key[:key_len]
        for col, kn in vals.items():
            seen += 1
            got = mine.get(key, {}).get(col)
            if got != kn:
                bad.append(f"MISMATCH {name} {key} {col}: summary {kn[0]}/{kn[1]}, recomputed "
                           f"{'-' if got is None else f'{got[0]}/{got[1]}'}")
    extra = [k for k in mine if k not in {r[0][:key_len] for r in section_rows}]
    for k in extra:
        bad.append(f"EXTRA ROW {name} {k} (recomputed, not in summary)")
    print(f"[compare] {name}: {seen} cells checked, {len(bad)} differences")
    return bad
