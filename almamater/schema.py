"""SQLite schema definitions and migration helpers."""
from __future__ import annotations
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS universities (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  name         TEXT NOT NULL UNIQUE,
  name_en      TEXT,
  country      TEXT NOT NULL,
  province     TEXT,
  school_type  TEXT,
  is_985       INTEGER NOT NULL DEFAULT 0,
  is_211       INTEGER NOT NULL DEFAULT 0,
  qs_rank      INTEGER,
  qs_score     REAL,
  qs_year      INTEGER,
  updated_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS university_aliases (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  university_id INTEGER NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
  alias         TEXT NOT NULL,
  lang          TEXT NOT NULL,
  alias_type    TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_aliases_alias ON university_aliases(alias);

CREATE TABLE IF NOT EXISTS syl_rounds (
  round       INTEGER PRIMARY KEY,
  valid_from  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS university_syl (
  university_id  INTEGER NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
  round          INTEGER NOT NULL REFERENCES syl_rounds(round),
  PRIMARY KEY (university_id, round)
);

CREATE TABLE IF NOT EXISTS university_syl_subjects (
  university_id  INTEGER NOT NULL,
  round          INTEGER NOT NULL,
  subject        TEXT NOT NULL,
  PRIMARY KEY (university_id, round, subject),
  FOREIGN KEY (university_id, round) REFERENCES university_syl(university_id, round)
);

CREATE TABLE IF NOT EXISTS university_subject_rankings (
  university_id  INTEGER NOT NULL REFERENCES universities(id) ON DELETE CASCADE,
  subject        TEXT NOT NULL,
  qs_rank        INTEGER,
  qs_score       REAL,
  year           INTEGER NOT NULL,
  PRIMARY KEY (university_id, subject)
);

CREATE TABLE IF NOT EXISTS build_info (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_universities_name_en ON universities(name_en);
CREATE INDEX IF NOT EXISTS idx_universities_country  ON universities(country);
CREATE INDEX IF NOT EXISTS idx_universities_qs_rank  ON universities(qs_rank);
CREATE INDEX IF NOT EXISTS idx_subject_rankings_subj ON university_subject_rankings(subject, qs_rank);
CREATE INDEX IF NOT EXISTS idx_syl_rounds_valid_from ON syl_rounds(valid_from);
"""

# Excel truncates sheet names to 31 chars. Map truncated → canonical for the 3 affected sheets.
QS_SHEET_NAME_MAP: dict[str, str] = {
    "Engineering - Mechanical, Aeron": "Engineering - Mechanical, Aeronautical & Manufacturing",
    "Engineering - Electrical & Elec": "Engineering - Electrical & Electronic",
    "Computer Science & Information ": "Computer Science & Information Systems",
    "Data Science and Artificial Int": "Data Science and Artificial Intelligence",
}

# QS subject sheet whitelist (spec section 四). Values are canonical QS sheet names.
QS_SUBJECTS = [
    "Biological Sciences",
    "Medicine",
    "Pharmacy & Pharmacology",
    "Agriculture & Forestry",
    "Chemistry",
    "Engineering - Chemical",
    "Engineering - Mechanical, Aeronautical & Manufacturing",
    "Engineering - Electrical & Electronic",
    "Computer Science & Information Systems",
    "Materials Science",
    "Environmental Sciences",
    "Physics & Astronomy",
    "Mathematics",
    "Data Science and Artificial Intelligence",
]


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.execute("PRAGMA foreign_keys = ON")


def truncate_rebuildable(conn: sqlite3.Connection) -> None:
    # Per spec section 七: aliases and subject rankings are rebuilt each time.
    # universities is NOT truncated — deleting it cascades into university_syl,
    # which must persist across builds. Loaders use upsert instead.
    conn.executescript(
        """
        DELETE FROM university_subject_rankings;
        DELETE FROM university_aliases;
        """
    )
