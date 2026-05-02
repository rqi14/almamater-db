"""End-to-end build orchestration: data sources -> data/university.db."""
from __future__ import annotations
import json
import os
import sqlite3
from datetime import date
from pathlib import Path

from . import name_map
from .name_map import SHORT_ALIASES
from .schema import init_schema, truncate_rebuildable
from .sources import china_edu, intl_aliases, qs_subject, qs_world


# Default file names within --data-dir.
QS_WORLD_NAME = "2026 QS World University Rankings 1.3 (For qs.com).xlsx"
QS_SUBJECT_NAME = "QS World University Rankings by Subject 2026 - Public Results v1.4 (qs.com)_20.xlsx"
INTL_ALIASES_NAME = "intl_aliases.json"


def _add_short_aliases(conn: sqlite3.Connection) -> int:
    n = 0
    for alias, canonical in SHORT_ALIASES.items():
        row = conn.execute(
            "SELECT id FROM universities WHERE name = ?", (canonical,)
        ).fetchone()
        if not row:
            continue
        try:
            conn.execute(
                """INSERT INTO university_aliases (university_id, alias, lang, alias_type)
                   VALUES (?, ?, 'zh', 'short')""",
                (row[0], alias),
            )
            n += 1
        except sqlite3.IntegrityError:
            pass
    return n


def _add_namemap_aliases(conn: sqlite3.Connection) -> int:
    n = 0
    for name_en, name_zh in name_map.QS_EN_TO_ZH.items():
        row = conn.execute("SELECT id FROM universities WHERE name = ?", (name_zh,)).fetchone()
        if not row:
            continue
        try:
            conn.execute(
                """INSERT INTO university_aliases (university_id, alias, lang, alias_type)
                   VALUES (?, ?, 'en', 'alt')""",
                (row[0], name_en),
            )
            n += 1
        except sqlite3.IntegrityError:
            pass
    return n


def build(data_dir: str | Path, db_path: str | Path, quiet: bool = False) -> dict:
    data_dir = Path(data_dir)
    db_path = Path(db_path)
    tmp_path = db_path.with_suffix(db_path.suffix + ".tmp")

    # Snapshot rebuildable=destructive vs syl=preserved tables (spec section 七).
    if db_path.exists():
        # Copy current DB to tmp so syl_* tables survive.
        tmp_path.write_bytes(db_path.read_bytes())
    elif tmp_path.exists():
        tmp_path.unlink()

    conn = sqlite3.connect(tmp_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        init_schema(conn)
        truncate_rebuildable(conn)

        stats: dict = {}
        stats["china_edu"] = china_edu.load(conn)

        qs_world_path = data_dir / QS_WORLD_NAME
        if qs_world_path.exists():
            stats["qs_world"] = qs_world.load(conn, qs_world_path)
        else:
            stats["qs_world"] = 0

        qs_subj_path = data_dir / QS_SUBJECT_NAME
        if qs_subj_path.exists():
            stats["qs_subject"] = qs_subject.load(conn, qs_subj_path)
        else:
            stats["qs_subject"] = {}

        intl_path = data_dir / INTL_ALIASES_NAME
        if intl_path.exists():
            stats["intl_aliases"] = intl_aliases.load(conn, intl_path)
        else:
            stats["intl_aliases"] = 0

        stats["short_aliases"] = _add_short_aliases(conn)
        stats["namemap_aliases"] = _add_namemap_aliases(conn)
        # Remove stub rows (country='XX', no QS rank, not linked to SYL) created
        # by intl_aliases when the QS name didn't match exactly on a prior build.
        conn.execute(
            """DELETE FROM universities
               WHERE country = 'XX' AND qs_rank IS NULL
                 AND id NOT IN (SELECT university_id FROM university_syl)
                 AND id NOT IN (SELECT university_id FROM university_subject_rankings)"""
        )

        # Write build metadata so consumers can inspect what went into the DB.
        meta = {
            "built_at": date.today().isoformat(),
            "china_edu_count": stats.get("china_edu", 0),
            "qs_world_count": stats.get("qs_world", 0),
            "qs_world_file": QS_WORLD_NAME if (data_dir / QS_WORLD_NAME).exists() else "",
            "qs_subject_file": QS_SUBJECT_NAME if (data_dir / QS_SUBJECT_NAME).exists() else "",
            "qs_subject_counts": json.dumps(stats.get("qs_subject", {})),
            "intl_aliases_count": stats.get("intl_aliases", 0),
        }
        conn.executemany(
            "INSERT OR REPLACE INTO build_info (key, value) VALUES (?, ?)",
            meta.items(),
        )
        conn.commit()
    except Exception:
        conn.close()
        if tmp_path.exists():
            tmp_path.unlink()
        raise
    conn.close()
    os.replace(tmp_path, db_path)
    if not quiet:
        print(f"[build] wrote {db_path}: {stats}")
    return stats
