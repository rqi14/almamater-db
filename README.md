# almamater-db

> [中文文档](README.zh.md)

A CLI tool that builds a local SQLite database of universities, combining:

- **Chinese universities** — 985 / 211 / Double First-Class (双一流) status, province, school type
- **QS World University Rankings** — overall rank and score (latest year)
- **QS Subject Rankings** — 14 STEM/science subjects (latest year)
- **Alias matching** — Chinese names, English abbreviations, and short forms for ~200 universities worldwide

The compiled database is designed to be queried directly from other programs (Node.js, Python, etc.) via read-only SQLite — no server required.

## Prerequisites

- Python 3.11+
- QS ranking Excel files downloaded from [topuniversities.com](https://www.topuniversities.com) (see [Data Setup](#data-setup))

## Install

```bash
pip install -e .
# or without installing:
pip install -r requirements.txt
```

## Data Setup

QS ranking data is **not included** in this repository. Download the following files from topuniversities.com and place them in the `data/` directory:

| File | Source |
|------|--------|
| `2026 QS World University Rankings *.xlsx` | QS World University Rankings |
| `QS World University Rankings by Subject 2026 *.xlsx` | QS Subject Rankings |

By downloading these files you agree to QS's [Terms and Conditions](https://www.topuniversities.com/terms-conditions). See [NOTICE](NOTICE) for attribution requirements.

The following seed data **is included**:

| File | Contents |
|------|----------|
| `data/intl_aliases.json` | Chinese names and English abbreviations for ~200 universities worldwide |
| `data/shuangyiliu_round1.json` | Double First-Class round 1 (2017, 140 schools) |
| `data/shuangyiliu_round2.json` | Double First-Class round 2 (2022, 147 schools) |

## Build

```bash
amdb build                        # reads data/, writes data/university.db
amdb build --data-dir /custom     # custom data directory
amdb build --db /path/out.db      # custom output path
```

The build is atomic: writes to `university.db.tmp` then renames. Safe to run while other processes have the DB open read-only.

## Query

```bash
amdb query "北京大学"
amdb query "Peking University"
amdb query "北大"
amdb query "MIT"
amdb query "麻省理工"
amdb --format json query "清华大学"
amdb query "北京大学" --subject "Computer Science & Information Systems"
```

## List

```bash
amdb list
amdb list --country CN --shuangyiliu          # current round only
amdb list --country CN --shuangyiliu ever     # ever listed in any round
amdb list --shuangyiliu round=1
amdb list --min-qs-rank 200
amdb --format csv list > universities.csv
```

## Expand 985/211 coverage (optional)

By default, `amdb build` seeds ~65 well-known Chinese universities. For complete
985/211 data (~116 schools), you can optionally use the
[China Education Data wide-table CSV](https://github.com/DaoSword/China-Education-Data/blob/main/%E6%95%B0%E6%8D%AE%E6%94%B6%E9%9B%86-%E9%AB%98%E7%AD%89%E6%95%99%E8%82%B2/04-%E6%95%B0%E6%8D%AE%E5%AE%BD%E8%A1%A8/%E9%AB%98%E7%AD%89%E6%95%99%E8%82%B2%E6%95%B0%E6%8D%AE%E5%AE%BD%E8%A1%A8v20230118.csv).

Download the CSV, then run:

```bash
amdb refresh --china-edu /path/to/高等教育数据宽表v20230118.csv
```

This upserts all schools into the existing database without rebuilding. No rebuild required.

## Import a new Double First-Class round

When round 3 is announced, normalize the official list to JSON and import:

```bash
amdb import-syl data/shuangyiliu_round3.json --dry-run
amdb import-syl data/shuangyiliu_round3.json
```

JSON format:

```json
{
  "round": 3,
  "announced_year": 2027,
  "schools": [
    { "name": "北京大学", "subjects": ["数学", "物理学"] },
    { "name": "清华大学", "subjects": [] }
  ]
}
```

## Other commands

```bash
amdb subjects          # list 14 tracked QS subjects
amdb rounds            # list imported Double First-Class rounds
amdb stats             # database counts
amdb validate          # find unresolved countries, orphan aliases
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | No match (`query`) |
| 2 | Ambiguous match |
| 3 | Database missing or schema mismatch |
| 4 | Input file validation failed (`import-syl`) |

## Tests

```bash
pip install pytest
pytest tests/
```

## License

MIT — see [LICENSE](LICENSE).

QS ranking data is not distributed with this software. See [NOTICE](NOTICE).
