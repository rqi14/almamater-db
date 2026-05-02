"""QS World University Rankings Excel loader."""
from __future__ import annotations
import re
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from ..country_map import to_iso
from ..name_map import to_zh

# QS xlsx ships with a banner row, header is on row index 1.
DEFAULT_HEADER = 1
DEFAULT_SKIP = [0]

# Tolerant column name lookup.
_COL_PATTERNS = {
    "rank": [r"^\s*(2026 |2025 )?rank\s*$", r"^rank.*overall$"],
    "name": [r"institution.*name", r"^name$"],
    "country": [r"country.*territory", r"^country$", r"location"],
    "score": [r"overall.*score", r"^score$"],
}


def _match_col(columns: list[str], key: str) -> str | None:
    for col in columns:
        for pat in _COL_PATTERNS[key]:
            if re.search(pat, str(col), re.IGNORECASE):
                return col
    return None


def _parse_rank(val) -> int | None:
    if pd.isna(val):
        return None
    s = str(val).strip()
    # QS publishes "601-650" for tied bands; take the lower bound.
    m = re.match(r"(\d+)", s)
    return int(m.group(1)) if m else None


def _parse_score(val) -> float | None:
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def load(conn: sqlite3.Connection, path: str | Path, year: int = 2026) -> int:
    df = pd.read_excel(path, header=DEFAULT_HEADER, skiprows=DEFAULT_SKIP)
    cols = list(df.columns)
    c_rank = _match_col(cols, "rank")
    c_name = _match_col(cols, "name")
    c_country = _match_col(cols, "country")
    c_score = _match_col(cols, "score")
    if not (c_rank and c_name and c_country):
        raise ValueError(f"QS World columns not recognised: {cols!r}")

    today = date.today().isoformat()
    n = 0
    for _, row in df.iterrows():
        name_en = str(row[c_name]).strip()
        if not name_en or name_en.lower() == "nan":
            continue
        rank = _parse_rank(row[c_rank])
        score = _parse_score(row[c_score]) if c_score else None
        country = to_iso(str(row[c_country]) if pd.notna(row[c_country]) else "")

        zh = to_zh(name_en)
        if zh is not None:
            # Update existing CN row, attach English name.
            conn.execute(
                """UPDATE universities
                   SET name_en = COALESCE(name_en, ?),
                       qs_rank = ?, qs_score = ?, qs_year = ?, updated_at = ?
                   WHERE name = ?""",
                (name_en, rank, score, year, today, zh),
            )
        else:
            conn.execute(
                """INSERT INTO universities
                   (name, name_en, country, qs_rank, qs_score, qs_year, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                     name_en = excluded.name_en,
                     qs_rank = excluded.qs_rank,
                     qs_score = excluded.qs_score,
                     qs_year = excluded.qs_year,
                     updated_at = excluded.updated_at""",
                (name_en, name_en, country, rank, score, year, today),
            )
        n += 1
    return n
