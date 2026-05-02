"""One-shot converter: Shuangyiliu HTML tables -> standard JSON.

Usage:
    python almamater/convert_syl_html.py \
        data/第一轮双一流建设高校及建设学科名单.html \
        --round 1 --year 2017 \
        --out data/shuangyiliu_round1.json

The HTML files in data/ have inconsistent markup (round 1 has dense single-line
tables; round 2 has multi-line tables with <a> tags inside subject cells). This
parser strips HTML, splits subjects by Chinese comma 、, and normalises
"（自定）" / "（自主确定建设学科并自行公布）" annotations.
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

# Cell content for "select-it-yourself" entries (round 2 北京大学 / 清华大学).
SELF_DETERMINED_PATTERNS = (
    "自主确定建设学科",
    "自行公布",
)

# Trailing annotations to strip from individual subject names.
SUBJECT_TRIM = re.compile(r"[（(](自定|自主)[）)]\s*$")


def _clean_subject(s: str) -> str:
    s = s.strip()
    s = SUBJECT_TRIM.sub("", s)
    return s.strip()


def _parse_subjects(cell_text: str) -> list[str]:
    text = cell_text.strip()
    if not text:
        return []
    if any(p in text for p in SELF_DETERMINED_PATTERNS):
        return []
    # Subjects separated by Chinese enumeration comma; tolerate full-width or
    # half-width commas as fallback.
    parts = re.split(r"[、,，]", text)
    out = []
    for p in parts:
        cleaned = _clean_subject(p)
        if cleaned:
            out.append(cleaned)
    return out


def parse_html(path: str | Path) -> list[dict]:
    html = Path(path).read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    schools: list[dict] = []
    for tr in rows:
        cells = tr.find_all("td")
        if len(cells) < 3:
            continue
        idx_text = cells[0].get_text(strip=True)
        if not idx_text.isdigit():
            continue
        name = cells[1].get_text(strip=True)
        subjects = _parse_subjects(cells[2].get_text(separator="", strip=True))
        if not name:
            continue
        schools.append({"name": name, "subjects": subjects})
    return schools


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("html_file")
    p.add_argument("--round", type=int, required=True)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--source-url", default="")
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)

    schools = parse_html(args.html_file)
    payload = {
        "round": args.round,
        "announced_year": args.year,
        "source_url": args.source_url,
        "normalized_at": "",
        "schools": schools,
    }
    Path(args.out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"wrote {args.out}: {len(schools)} schools")
    return 0


if __name__ == "__main__":
    sys.exit(main())
