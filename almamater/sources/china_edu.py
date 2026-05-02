"""Chinese universities seed loader.

`load()` — inserts the built-in SEED of well-known schools (always available).
`load_csv()` — optional: imports all schools from a DaoSword-format wide-table CSV
               for complete 985/211 coverage. Called by `amdb refresh --china-edu`.
"""
from __future__ import annotations
import csv
import sqlite3
from datetime import date
from pathlib import Path

# (name, name_en, province, school_type, is_985, is_211)
SEED: list[tuple[str, str | None, str, str, int, int]] = [
    ("清华大学", "Tsinghua University", "北京市", "公办", 1, 1),
    ("北京大学", "Peking University", "北京市", "公办", 1, 1),
    ("中国人民大学", "Renmin University of China", "北京市", "公办", 1, 1),
    ("北京师范大学", "Beijing Normal University", "北京市", "公办", 1, 1),
    ("北京航空航天大学", "Beihang University", "北京市", "公办", 1, 1),
    ("北京理工大学", "Beijing Institute of Technology", "北京市", "公办", 1, 1),
    ("中国农业大学", "China Agricultural University", "北京市", "公办", 1, 1),
    ("北京邮电大学", "Beijing University of Posts and Telecommunications", "北京市", "公办", 0, 1),
    ("北京交通大学", "Beijing Jiaotong University", "北京市", "公办", 0, 1),
    ("北京林业大学", "Beijing Forestry University", "北京市", "公办", 0, 1),
    ("中央民族大学", "Minzu University of China", "北京市", "公办", 1, 1),
    ("南开大学", "Nankai University", "天津市", "公办", 1, 1),
    ("天津大学", "Tianjin University", "天津市", "公办", 1, 1),
    ("大连理工大学", "Dalian University of Technology", "辽宁省", "公办", 1, 1),
    ("东北大学", "Northeastern University (China)", "辽宁省", "公办", 1, 1),
    ("吉林大学", "Jilin University", "吉林省", "公办", 1, 1),
    ("哈尔滨工业大学", "Harbin Institute of Technology", "黑龙江省", "公办", 1, 1),
    ("复旦大学", "Fudan University", "上海市", "公办", 1, 1),
    ("上海交通大学", "Shanghai Jiao Tong University", "上海市", "公办", 1, 1),
    ("同济大学", "Tongji University", "上海市", "公办", 1, 1),
    ("华东师范大学", "East China Normal University", "上海市", "公办", 1, 1),
    ("华东理工大学", "East China University of Science and Technology", "上海市", "公办", 0, 1),
    ("上海大学", "Shanghai University", "上海市", "公办", 0, 1),
    ("南京大学", "Nanjing University", "江苏省", "公办", 1, 1),
    ("东南大学", "Southeast University", "江苏省", "公办", 1, 1),
    ("苏州大学", "Soochow University", "江苏省", "公办", 0, 1),
    ("南京航空航天大学", "Nanjing University of Aeronautics and Astronautics", "江苏省", "公办", 0, 1),
    ("南京理工大学", "Nanjing University of Science and Technology", "江苏省", "公办", 0, 1),
    ("南京农业大学", "Nanjing Agricultural University", "江苏省", "公办", 0, 1),
    ("南京林业大学", "Nanjing Forestry University", "江苏省", "公办", 0, 0),
    ("浙江大学", "Zhejiang University", "浙江省", "公办", 1, 1),
    ("中国科学技术大学", "University of Science and Technology of China", "安徽省", "公办", 1, 1),
    ("合肥工业大学", "Hefei University of Technology", "安徽省", "公办", 0, 1),
    ("安徽大学", "Anhui University", "安徽省", "公办", 0, 1),
    ("厦门大学", "Xiamen University", "福建省", "公办", 1, 1),
    ("山东大学", "Shandong University", "山东省", "公办", 1, 1),
    ("中国海洋大学", "Ocean University of China", "山东省", "公办", 1, 1),
    ("武汉大学", "Wuhan University", "湖北省", "公办", 1, 1),
    ("华中科技大学", "Huazhong University of Science and Technology", "湖北省", "公办", 1, 1),
    ("华中农业大学", "Huazhong Agricultural University", "湖北省", "公办", 0, 1),
    ("武汉理工大学", "Wuhan University of Technology", "湖北省", "公办", 0, 1),
    ("湖南大学", "Hunan University", "湖南省", "公办", 1, 1),
    ("中南大学", "Central South University", "湖南省", "公办", 1, 1),
    ("中山大学", "Sun Yat-sen University", "广东省", "公办", 1, 1),
    ("华南理工大学", "South China University of Technology", "广东省", "公办", 1, 1),
    ("暨南大学", "Jinan University", "广东省", "公办", 0, 1),
    ("广西大学", "Guangxi University", "广西壮族自治区", "公办", 0, 1),
    ("四川大学", "Sichuan University", "四川省", "公办", 1, 1),
    ("电子科技大学", "University of Electronic Science and Technology of China", "四川省", "公办", 1, 1),
    ("西南交通大学", "Southwest Jiaotong University", "四川省", "公办", 0, 1),
    ("四川农业大学", "Sichuan Agricultural University", "四川省", "公办", 0, 1),
    ("成都中医药大学", "Chengdu University of Traditional Chinese Medicine", "四川省", "公办", 0, 0),
    ("重庆大学", "Chongqing University", "重庆市", "公办", 1, 1),
    ("西南大学", "Southwest University", "重庆市", "公办", 0, 1),
    ("西安交通大学", "Xi'an Jiaotong University", "陕西省", "公办", 1, 1),
    ("西北工业大学", "Northwestern Polytechnical University", "陕西省", "公办", 1, 1),
    ("西安电子科技大学", "Xidian University", "陕西省", "公办", 0, 1),
    ("西北农林科技大学", "Northwest A&F University", "陕西省", "公办", 1, 1),
    ("兰州大学", "Lanzhou University", "甘肃省", "公办", 1, 1),
    ("中国科学院大学", "University of Chinese Academy of Sciences", "北京市", "公办", 0, 0),
    ("中国科学院", "Chinese Academy of Sciences", "北京市", "公办", 0, 0),
    ("温州大学", "Wenzhou University", "浙江省", "公办", 0, 0),
    ("天津科技大学", "Tianjin University of Science and Technology", "天津市", "公办", 0, 0),
    ("国防科技大学", "National University of Defense Technology", "湖南省", "军事", 1, 1),
]


def load_csv(conn: sqlite3.Connection, csv_path: str | Path) -> int:
    """Load all universities from a DaoSword-style wide-table CSV.

    Expected columns (flexible matching):
      学校名称, 所在省份, 学校性质, 985工程, 211工程
    All rows are upserted; missing columns are silently treated as unknown.
    Returns the number of rows processed.
    """
    today = date.today().isoformat()
    n = 0
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return 0
        # Flexible column resolution
        fields = list(reader.fieldnames)
        def _col(*candidates: str) -> str | None:
            for c in candidates:
                if c in fields:
                    return c
            return None
        c_name     = _col("学校名称", "名称")
        c_province = _col("所在省份", "省份")
        c_type     = _col("学校性质", "性质")
        c_985      = _col("985工程", "985")
        c_211      = _col("211工程", "211")
        if not c_name:
            raise ValueError(f"CSV missing '学校名称' column; found: {fields}")
        for row in reader:
            name = row[c_name].strip()
            if not name:
                continue
            province   = row[c_province].strip() if c_province else None
            school_type = row[c_type].strip()    if c_type     else None
            is_985 = int(float(row[c_985] or 0)) if c_985 else 0
            is_211 = int(float(row[c_211] or 0)) if c_211 else 0
            conn.execute(
                """INSERT INTO universities
                   (name, country, province, school_type, is_985, is_211, updated_at)
                   VALUES (?, 'CN', ?, ?, ?, ?, ?)
                   ON CONFLICT(name) DO UPDATE SET
                     province    = excluded.province,
                     school_type = excluded.school_type,
                     is_985      = excluded.is_985,
                     is_211      = excluded.is_211,
                     updated_at  = excluded.updated_at""",
                (name, province, school_type, is_985, is_211, today),
            )
            n += 1
    return n


def load(conn: sqlite3.Connection) -> int:
    today = date.today().isoformat()
    rows = [
        (name, name_en, "CN", province, stype, is_985, is_211, today)
        for name, name_en, province, stype, is_985, is_211 in SEED
    ]
    conn.executemany(
        """INSERT INTO universities
           (name, name_en, country, province, school_type, is_985, is_211, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(name) DO UPDATE SET
             name_en = excluded.name_en,
             province = excluded.province,
             school_type = excluded.school_type,
             is_985 = excluded.is_985,
             is_211 = excluded.is_211,
             updated_at = excluded.updated_at""",
        rows,
    )
    return len(rows)
