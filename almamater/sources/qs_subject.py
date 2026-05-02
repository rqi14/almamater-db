"""QS Subject Rankings Excel loader (sheet-per-subject)."""
from __future__ import annotations
import re
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd

from ..country_map import to_iso
from ..name_map import to_zh
from ..schema import QS_SHEET_NAME_MAP, QS_SUBJECTS


def _parse_rank(val) -> int | None:
    if pd.isna(val):
        return None
    m = re.match(r"(\d+)", str(val).strip())
    return int(m.group(1)) if m else None


def _parse_score(val) -> float | None:
    if pd.isna(val):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _pick_col(cols: list[str], patterns: list[str]) -> str | None:
    for c in cols:
        for p in patterns:
            if re.search(p, str(c), re.IGNORECASE):
                return c
    return None


def _match_sheet(actual_sheets: list[str], target: str) -> str | None:
    # Reverse-lookup: if a sheet name is a known truncated form, map it back.
    reverse = {v: k for k, v in QS_SHEET_NAME_MAP.items()}
    lookup = reverse.get(target, target)
    return lookup if lookup in actual_sheets else None


def _ensure_university(conn: sqlite3.Connection, name_en: str, country: str) -> int:
    zh = to_zh(name_en)
    lookup = zh if zh else name_en
    row = conn.execute("SELECT id FROM universities WHERE name = ?", (lookup,)).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        """INSERT INTO universities (name, name_en, country, updated_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET name_en = excluded.name_en
           RETURNING id""",
        (name_en, name_en, country, date.today().isoformat()),
    )
    res = cur.fetchone()
    return res[0]


def load(conn: sqlite3.Connection, path: str | Path, year: int = 2026) -> dict[str, int]:
    xls = pd.ExcelFile(path)
    sheets = xls.sheet_names
    counts: dict[str, int] = {}
    for subject in QS_SUBJECTS:
        sheet = _match_sheet(sheets, subject)
        if not sheet:
            counts[subject] = 0
            continue
        # Subject sheets: row 0=banner, 1=subject name, 2=empty, 3=headers, 4+=data
        df = pd.read_excel(xls, sheet_name=sheet, header=3)
        cols = list(df.columns)
        c_rank = _pick_col(cols, [r"^2026$", r"^\s*(2026 |2025 )?rank\s*$", r"^rank"])
        c_name = _pick_col(cols, [r"^institution$", r"institution.*name", r"^name$"])
        c_country = _pick_col(cols, [r"country.*territory", r"location"])
        c_score = _pick_col(cols, [r"^score$", r"overall.*score"])
        if not (c_rank and c_name):
            counts[subject] = 0
            continue
        n = 0
        for _, row in df.iterrows():
            name_en = str(row[c_name]).strip()
            if not name_en or name_en.lower() == "nan":
                continue
            rank = _parse_rank(row[c_rank])
            score = _parse_score(row[c_score]) if c_score else None
            country = to_iso(str(row[c_country]) if c_country and pd.notna(row[c_country]) else "")
            uid = _ensure_university(conn, name_en, country)
            conn.execute(
                """INSERT INTO university_subject_rankings
                   (university_id, subject, qs_rank, qs_score, year)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(university_id, subject) DO UPDATE SET
                     qs_rank = excluded.qs_rank,
                     qs_score = excluded.qs_score,
                     year = excluded.year""",
                (uid, subject, rank, score, year),
            )
            n += 1
        counts[subject] = n
    return counts
