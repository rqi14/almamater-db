import sqlite3

from almamater import cli
from almamater.schema import init_schema


def _seed():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_schema(conn)
    conn.execute(
        """INSERT INTO universities (name, name_en, country, is_985, is_211, updated_at)
           VALUES ('北京大学', 'Peking University', 'CN', 1, 1, '2026-05-01')"""
    )
    uid = conn.execute("SELECT id FROM universities WHERE name='北京大学'").fetchone()["id"]
    conn.execute(
        "INSERT INTO university_aliases (university_id, alias, lang, alias_type) VALUES (?, '北大', 'zh', 'short')",
        (uid,),
    )
    conn.execute(
        """INSERT INTO universities (name, name_en, country, updated_at)
           VALUES ('Massachusetts Institute of Technology',
                   'Massachusetts Institute of Technology', 'US', '2026-05-01')"""
    )
    mit_id = conn.execute(
        "SELECT id FROM universities WHERE name='Massachusetts Institute of Technology'"
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO university_aliases (university_id, alias, lang, alias_type) VALUES (?, '麻省理工', 'zh', 'zh_for_intl')",
        (mit_id,),
    )
    return conn


def test_exact_chinese():
    c = _seed()
    assert cli._exact_match(c, "北京大学") != []


def test_exact_english():
    c = _seed()
    assert cli._exact_match(c, "Peking University") != []


def test_alias_short():
    c = _seed()
    assert cli._exact_match(c, "北大") == []
    assert cli._alias_match(c, "北大") != []


def test_alias_intl_zh():
    c = _seed()
    assert cli._alias_match(c, "麻省理工") != []


def test_fuzzy_typo():
    c = _seed()
    ids = cli._fuzzy_match(c, "北京大学 ")
    assert ids != []
