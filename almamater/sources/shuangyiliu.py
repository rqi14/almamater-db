"""Double-First-Class (双一流) JSON loader."""
from __future__ import annotations
import json
import sqlite3
from datetime import date
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class _School(BaseModel):
    name: str
    subjects: list[str] = Field(default_factory=list)


class SylRound(BaseModel):
    round: int
    announced_year: int
    source_url: str | None = None
    normalized_at: str | None = None
    schools: list[_School]


def parse(path: str | Path) -> SylRound:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return SylRound.model_validate(raw)


def _ensure_university(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM universities WHERE name = ?", (name,)).fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        """INSERT INTO universities (name, country, updated_at)
           VALUES (?, 'CN', ?)""",
        (name, date.today().isoformat()),
    )
    return cur.lastrowid


def load(conn: sqlite3.Connection, payload: SylRound) -> dict[str, int]:
    conn.execute(
        "INSERT OR REPLACE INTO syl_rounds (round, valid_from) VALUES (?, ?)",
        (payload.round, payload.announced_year),
    )
    n_schools = 0
    n_subjects = 0
    for s in payload.schools:
        uid = _ensure_university(conn, s.name)
        conn.execute(
            "INSERT OR IGNORE INTO university_syl (university_id, round) VALUES (?, ?)",
            (uid, payload.round),
        )
        n_schools += 1
        for subj in s.subjects:
            conn.execute(
                """INSERT OR IGNORE INTO university_syl_subjects
                   (university_id, round, subject) VALUES (?, ?, ?)""",
                (uid, payload.round, subj),
            )
            n_subjects += 1
    return {"schools": n_schools, "subjects": n_subjects, "round": payload.round}


def parse_or_raise(path: str | Path) -> SylRound | None:
    try:
        return parse(path)
    except (ValidationError, json.JSONDecodeError, FileNotFoundError):
        return None
