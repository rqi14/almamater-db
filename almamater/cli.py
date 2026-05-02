"""amdb command-line entry point."""
from __future__ import annotations
import argparse
import csv
import io
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

# Allow running this file directly: `python almamater/cli.py`
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "almamater"

from .build import build as run_build
from .schema import QS_SUBJECTS, init_schema
from .sources import china_edu, shuangyiliu

DEFAULT_DB = "data/university.db"
DEFAULT_DATA_DIR = "data"
UNMATCHED_LOG = "data/unmatched.log"


def _open_db(path: str) -> sqlite3.Connection:
    p = Path(path)
    if not p.exists():
        print(f"error: database not found at {path}; run `amdb build` first", file=sys.stderr)
        sys.exit(3)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _emit(rows: list[dict[str, Any]] | dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    if fmt == "csv":
        if not rows:
            return
        items = rows if isinstance(rows, list) else [rows]
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=list(items[0].keys()))
        w.writeheader()
        for r in items:
            w.writerow(r)
        sys.stdout.write(out.getvalue())
        return
    # table
    items = rows if isinstance(rows, list) else [rows]
    if not items:
        print("(no results)")
        return
    keys = list(items[0].keys())
    widths = [max(len(str(k)), *(len(str(r.get(k, ""))) for r in items)) for k in keys]
    line = "  ".join(str(k).ljust(w) for k, w in zip(keys, widths))
    print(line)
    print("  ".join("-" * w for w in widths))
    for r in items:
        print("  ".join(str(r.get(k, "")).ljust(w) for k, w in zip(keys, widths)))


# ---------- match strategy ----------

def _exact_match(conn: sqlite3.Connection, q: str) -> list[int]:
    rows = conn.execute(
        "SELECT id FROM universities WHERE name = ? OR name_en = ?", (q, q)
    ).fetchall()
    return [r["id"] for r in rows]


def _alias_match(conn: sqlite3.Connection, q: str) -> list[int]:
    rows = conn.execute(
        "SELECT university_id FROM university_aliases WHERE alias = ?", (q,)
    ).fetchall()
    return [r["university_id"] for r in rows]


def _fuzzy_match(conn: sqlite3.Connection, q: str) -> list[int]:
    from rapidfuzz import process as fuzz

    candidates: dict[str, int] = {}
    for r in conn.execute("SELECT id, name, name_en FROM universities").fetchall():
        candidates[r["name"]] = r["id"]
        if r["name_en"]:
            candidates[r["name_en"]] = r["id"]
    for r in conn.execute("SELECT alias, university_id FROM university_aliases").fetchall():
        candidates.setdefault(r["alias"], r["university_id"])
    if not candidates:
        return []
    matches = fuzz.extract(q, candidates.keys(), limit=3, score_cutoff=60)
    if not matches:
        return []
    top_score = matches[0][1]
    return list({candidates[m[0]] for m in matches if m[1] == top_score})


def _record(conn: sqlite3.Connection, uid: int) -> dict[str, Any]:
    u = conn.execute("SELECT * FROM universities WHERE id = ?", (uid,)).fetchone()
    if not u:
        return {}
    rec: dict[str, Any] = {
        "name": u["name"],
        "name_en": u["name_en"],
        "country": u["country"],
        "province": u["province"],
        "school_type": u["school_type"],
        "is_985": bool(u["is_985"]),
        "is_211": bool(u["is_211"]),
        "qs_world_rank": u["qs_rank"],
        "qs_world_score": u["qs_score"],
        "qs_year": u["qs_year"],
    }
    cur_round = conn.execute("SELECT MAX(round) FROM syl_rounds").fetchone()[0]
    if cur_round is not None:
        in_cur = conn.execute(
            "SELECT 1 FROM university_syl WHERE university_id = ? AND round = ?",
            (uid, cur_round),
        ).fetchone()
        ever = conn.execute(
            "SELECT MAX(round) FROM university_syl WHERE university_id = ?", (uid,)
        ).fetchone()[0]
        if in_cur:
            subjects = [
                r["subject"]
                for r in conn.execute(
                    """SELECT subject FROM university_syl_subjects
                       WHERE university_id = ? AND round = ?""",
                    (uid, cur_round),
                ).fetchall()
            ]
            rec["shuangyiliu"] = {
                "current": True,
                "round": cur_round,
                "subjects": subjects,
            }
        elif ever is not None:
            rec["shuangyiliu"] = {"current": False, "round": ever, "subjects": []}
        else:
            rec["shuangyiliu"] = None
    else:
        rec["shuangyiliu"] = None

    rec["subject_rankings"] = [
        {"subject": r["subject"], "rank": r["qs_rank"], "score": r["qs_score"]}
        for r in conn.execute(
            """SELECT subject, qs_rank, qs_score FROM university_subject_rankings
               WHERE university_id = ? ORDER BY qs_rank""",
            (uid,),
        ).fetchall()
    ]
    return rec


def _log_unmatched(q: str) -> None:
    try:
        Path(UNMATCHED_LOG).parent.mkdir(parents=True, exist_ok=True)
        with open(UNMATCHED_LOG, "a", encoding="utf-8") as f:
            f.write(q + "\n")
    except OSError:
        pass


# ---------- subcommands ----------

def cmd_build(args: argparse.Namespace) -> int:
    run_build(args.data_dir, args.db, quiet=args.quiet)
    return 0


def cmd_refresh(args: argparse.Namespace) -> int:
    if args.china_edu:
        path = Path(args.china_edu)
        if not path.exists():
            print(f"error: file not found: {path}", file=sys.stderr)
            return 3
        conn = _open_db(args.db)
        n = china_edu.load_csv(conn, path)
        conn.commit()
        conn.close()
        if not args.quiet:
            print(f"[refresh] imported {n} schools from {path}")
        return 0
    if not args.quiet:
        print("[refresh] no source specified. Use --china-edu /path/to.csv", file=sys.stderr)
    return 0


def cmd_import_syl(args: argparse.Namespace) -> int:
    payload = shuangyiliu.parse_or_raise(args.json_file)
    if payload is None:
        print(f"error: invalid JSON or schema in {args.json_file}", file=sys.stderr)
        return 4
    if args.dry_run:
        if not args.quiet:
            print(
                f"[dry-run] round={payload.round} year={payload.announced_year} "
                f"schools={len(payload.schools)}"
            )
        return 0
    conn = sqlite3.connect(args.db)
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    stats = shuangyiliu.load(conn, payload)
    conn.commit()
    conn.close()
    if not args.quiet:
        print(f"[import-syl] {stats}")
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    conn = _open_db(args.db)
    q = args.name
    ids = _exact_match(conn, q) or _alias_match(conn, q) or _fuzzy_match(conn, q)
    if not ids:
        _log_unmatched(q)
        if not args.quiet:
            print(f"no match for {q!r}", file=sys.stderr)
        return 1
    if len(ids) > 1:
        candidates = [
            {"name": r["name"], "name_en": r["name_en"]}
            for r in conn.execute(
                f"SELECT name, name_en FROM universities WHERE id IN ({','.join('?' * len(ids))})",
                ids,
            ).fetchall()
        ]
        if not args.quiet:
            print("ambiguous match:", file=sys.stderr)
        _emit(candidates, args.format)
        return 2
    rec = _record(conn, ids[0])
    if args.subject:
        rec["subject_rankings"] = [
            r for r in rec["subject_rankings"] if r["subject"] == args.subject
        ]
    _emit(rec, args.format)
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    conn = _open_db(args.db)
    where = []
    params: list[Any] = []
    if args.country:
        where.append("u.country = ?")
        params.append(args.country)
    if args.min_qs_rank:
        where.append("u.qs_rank IS NOT NULL AND u.qs_rank <= ?")
        params.append(args.min_qs_rank)

    syl_join = ""
    if args.shuangyiliu is not None:
        opt = args.shuangyiliu
        if opt.startswith("round="):
            r = int(opt.split("=", 1)[1])
            syl_join = (
                "JOIN university_syl s ON s.university_id = u.id AND s.round = ?"
            )
            params.insert(0, r)
        elif opt == "ever":
            syl_join = "JOIN university_syl s ON s.university_id = u.id"
        else:
            # Default: current round only.
            syl_join = (
                "JOIN university_syl s ON s.university_id = u.id "
                "AND s.round = (SELECT MAX(round) FROM syl_rounds)"
            )

    sql = f"""SELECT DISTINCT u.name, u.name_en, u.country, u.province,
                     u.is_985, u.is_211, u.qs_rank
              FROM universities u {syl_join}"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY u.qs_rank IS NULL, u.qs_rank, u.name"

    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    _emit(rows, args.format)
    return 0


def cmd_subjects(args: argparse.Namespace) -> int:
    _emit([{"subject": s} for s in QS_SUBJECTS], args.format)
    return 0


def cmd_rounds(args: argparse.Namespace) -> int:
    conn = _open_db(args.db)
    rows = [dict(r) for r in conn.execute(
        "SELECT round, valid_from FROM syl_rounds ORDER BY round").fetchall()]
    _emit(rows, args.format)
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    conn = _open_db(args.db)
    s = {
        "universities": conn.execute("SELECT COUNT(*) FROM universities").fetchone()[0],
        "aliases": conn.execute("SELECT COUNT(*) FROM university_aliases").fetchone()[0],
        "syl_rounds": conn.execute("SELECT COUNT(*) FROM syl_rounds").fetchone()[0],
        "syl_universities": conn.execute(
            "SELECT COUNT(DISTINCT university_id) FROM university_syl"
        ).fetchone()[0],
        "subject_rankings": conn.execute(
            "SELECT COUNT(*) FROM university_subject_rankings"
        ).fetchone()[0],
        "qs_ranked": conn.execute(
            "SELECT COUNT(*) FROM universities WHERE qs_rank IS NOT NULL"
        ).fetchone()[0],
    }
    _emit(s, args.format)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    conn = _open_db(args.db)
    issues: list[dict[str, Any]] = []
    orphan_aliases = conn.execute(
        """SELECT a.alias FROM university_aliases a
           LEFT JOIN universities u ON a.university_id = u.id
           WHERE u.id IS NULL"""
    ).fetchall()
    for r in orphan_aliases:
        issues.append({"type": "orphan_alias", "value": r["alias"]})

    no_country = conn.execute(
        "SELECT name FROM universities WHERE country IS NULL OR country = ''"
    ).fetchall()
    for r in no_country:
        issues.append({"type": "missing_country", "value": r["name"]})

    xx_country = conn.execute(
        "SELECT name FROM universities WHERE country = 'XX'"
    ).fetchall()
    for r in xx_country:
        issues.append({"type": "unresolved_country", "value": r["name"]})

    _emit(issues, args.format)
    return 0


# ---------- arg parsing ----------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="amdb", description="University quality database CLI")
    p.add_argument("--db", default=DEFAULT_DB, help="path to university.db")
    p.add_argument("--format", choices=["table", "json", "csv"], default="table")
    p.add_argument("--quiet", action="store_true")

    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("build")
    s.add_argument("--data-dir", default=DEFAULT_DATA_DIR)
    s.set_defaults(func=cmd_build)

    s = sub.add_parser("refresh")
    s.add_argument("--china-edu", metavar="CSV", help="path to DaoSword-format wide-table CSV")
    s.set_defaults(func=cmd_refresh)

    s = sub.add_parser("import-syl")
    s.add_argument("json_file")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(func=cmd_import_syl)

    s = sub.add_parser("query")
    s.add_argument("name")
    s.add_argument("--subject")
    s.set_defaults(func=cmd_query)

    s = sub.add_parser("list")
    s.add_argument("--country")
    s.add_argument("--shuangyiliu", nargs="?", const="current")
    s.add_argument("--min-qs-rank", type=int)
    s.set_defaults(func=cmd_list)

    s = sub.add_parser("subjects")
    s.set_defaults(func=cmd_subjects)

    s = sub.add_parser("rounds")
    s.set_defaults(func=cmd_rounds)

    s = sub.add_parser("stats")
    s.set_defaults(func=cmd_stats)

    s = sub.add_parser("validate")
    s.set_defaults(func=cmd_validate)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
