import json
import sqlite3

import pytest

from almamater.schema import init_schema
from almamater.sources import shuangyiliu


GOOD = {
    "round": 9,
    "announced_year": 2030,
    "schools": [
        {"name": "测试大学", "subjects": ["数学", "物理学"]},
        {"name": "整体入选大学", "subjects": []},
    ],
}

BAD_MISSING_ROUND = {"announced_year": 2030, "schools": []}


def test_parse_good(tmp_path):
    p = tmp_path / "good.json"
    p.write_text(json.dumps(GOOD), encoding="utf-8")
    payload = shuangyiliu.parse(p)
    assert payload.round == 9
    assert len(payload.schools) == 2
    assert payload.schools[1].subjects == []


def test_parse_bad(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(BAD_MISSING_ROUND), encoding="utf-8")
    assert shuangyiliu.parse_or_raise(p) is None


def test_load_inserts_subjects():
    conn = sqlite3.connect(":memory:")
    init_schema(conn)
    payload = shuangyiliu.SylRound.model_validate(GOOD)
    stats = shuangyiliu.load(conn, payload)
    assert stats["schools"] == 2
    assert stats["subjects"] == 2

    rows = conn.execute(
        """SELECT u.name, s.subject FROM university_syl_subjects s
           JOIN universities u ON u.id = s.university_id
           ORDER BY u.name, s.subject"""
    ).fetchall()
    assert ("测试大学", "数学") in rows
    assert ("测试大学", "物理学") in rows
