"""International Chinese alias loader (data/intl_aliases.json)."""
from __future__ import annotations
import json
import sqlite3
from datetime import date
from pathlib import Path


def load(conn: sqlite3.Connection, path: str | Path) -> int:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    today = date.today().isoformat()
    n = 0
    for entry in raw:
        name_en = (entry.get("name_en") or "").strip()
        if not name_en:
            continue
        aliases = entry.get("aliases_zh") or []
        # wikidata_id intentionally ignored — schema doesn't store it and source
        # data quality is unreliable.
        # Exact match first; fall back to prefix LIKE to handle QS suffixes like "(MIT)".
        row = conn.execute(
            """SELECT id FROM universities
               WHERE name_en = ? OR name = ?
               OR name_en LIKE ? OR name LIKE ?""",
            (name_en, name_en, name_en + "%", name_en + "%"),
        ).fetchone()
        if not row:
            cur = conn.execute(
                """INSERT INTO universities (name, name_en, country, updated_at)
                   VALUES (?, ?, 'XX', ?)
                   ON CONFLICT(name) DO UPDATE SET name_en = excluded.name_en
                   RETURNING id""",
                (name_en, name_en, today),
            )
            uid = cur.fetchone()[0]
        else:
            uid = row[0]
        for alias in aliases:
            alias = (alias or "").strip()
            if not alias:
                continue
            conn.execute(
                """INSERT OR IGNORE INTO university_aliases
                   (university_id, alias, lang, alias_type)
                   VALUES (?, ?, 'zh', 'zh_for_intl')""",
                (uid, alias),
            )
            n += 1
        for alias_en in (entry.get("aliases_en") or []):
            alias_en = (alias_en or "").strip()
            if not alias_en:
                continue
            conn.execute(
                """INSERT OR IGNORE INTO university_aliases
                   (university_id, alias, lang, alias_type)
                   VALUES (?, ?, 'en', 'short')""",
                (uid, alias_en),
            )
            n += 1
    return n
