import sqlite3

from almamater.schema import init_schema, truncate_rebuildable
from almamater.sources import china_edu


def test_china_edu_load_and_truncate():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    n = china_edu.load(conn)
    assert n > 20
    rows = conn.execute("SELECT COUNT(*) FROM universities").fetchone()[0]
    assert rows == n

    truncate_rebuildable(conn)
    # truncate_rebuildable only removes aliases and subject_rankings, not universities
    rows = conn.execute("SELECT COUNT(*) FROM universities").fetchone()[0]
    assert rows == n


def test_schema_indexes_present():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    idx = {
        r[1]
        for r in conn.execute("SELECT * FROM sqlite_master WHERE type='index'").fetchall()
    }
    assert "idx_aliases_alias" in idx
    assert "idx_universities_qs_rank" in idx
    assert "idx_subject_rankings_subj" in idx
