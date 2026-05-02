# almamater-db

> [English README](README.md)

一个 CLI 工具，用于构建本地 SQLite 高校数据库，整合：

- **中国高校** — 985 / 211 / 双一流状态、省份、学校类型
- **QS 世界大学排名** — 综合排名和分数（最新年份）
- **QS 学科排名** — 14 个理工科学科（最新年份）
- **别名匹配** — 约 200 所全球高校的中文名称、英文缩写和简称

编译后的数据库可以通过其他程序（Node.js、Python 等）以只读 SQLite 方式直接查询，无需独立服务。

## 环境要求

- Python 3.11+
- 从 [topuniversities.com](https://www.topuniversities.com) 下载的 QS 排名 Excel 文件（见[数据准备](#数据准备)）

## 安装

```bash
pip install -e .
# 或不安装直接使用：
pip install -r requirements.txt
```

## 数据准备

QS 排名数据**不包含**在本仓库中。请从 topuniversities.com 下载以下文件并放入 `data/` 目录：

| 文件 | 来源 |
|------|------|
| `2026 QS World University Rankings *.xlsx` | QS 世界大学排名 |
| `QS World University Rankings by Subject 2026 *.xlsx` | QS 学科排名 |

下载这些文件即表示您同意 QS 的[使用条款](https://www.topuniversities.com/terms-conditions)。署名要求见 [NOTICE](NOTICE)。

以下种子数据**已包含**在仓库中：

| 文件 | 内容 |
|------|------|
| `data/intl_aliases.json` | 约 200 所全球高校的中文名称和英文缩写 |
| `data/shuangyiliu_round1.json` | 双一流第一轮（2017 年，140 所高校） |
| `data/shuangyiliu_round2.json` | 双一流第二轮（2022 年，147 所高校） |

## 构建数据库

```bash
amdb build                        # 读取 data/，写入 data/university.db
amdb build --data-dir /custom     # 自定义数据目录
amdb build --db /path/out.db      # 自定义输出路径
```

构建过程是原子操作：先写入 `university.db.tmp`，然后重命名。其他程序以只读方式打开数据库时可以安全运行。

## 查询

```bash
amdb query "北京大学"
amdb query "Peking University"
amdb query "北大"
amdb query "MIT"
amdb query "麻省理工"
amdb --format json query "清华大学"
amdb query "北京大学" --subject "Computer Science & Information Systems"
```

## 列表

```bash
amdb list
amdb list --country CN --shuangyiliu          # 仅当前轮次
amdb list --country CN --shuangyiliu ever     # 曾入选任意轮次
amdb list --shuangyiliu round=1
amdb list --min-qs-rank 200
amdb --format csv list > universities.csv
```

## 扩充 985/211 数据（可选）

默认情况下，`amdb build` 预置了约 65 所知名中国高校。如需完整的 985/211 数据（约 116 所高校），可选择使用
[高等教育数据宽表 CSV](https://github.com/DaoSword/China-Education-Data/blob/main/%E6%95%B0%E6%8D%AE%E6%94%B6%E9%9B%86-%E9%AB%98%E7%AD%89%E6%95%99%E8%82%B2/04-%E6%95%B0%E6%8D%AE%E5%AE%BD%E8%A1%A8/%E9%AB%98%E7%AD%89%E6%95%99%E8%82%B2%E6%95%B0%E6%8D%AE%E5%AE%BD%E8%A1%A8v20230118.csv)。

下载 CSV 后运行：

```bash
amdb refresh --china-edu /path/to/高等教育数据宽表v20230118.csv
```

此命令直接 upsert 到现有数据库，无需重新构建。

## 导入新一轮双一流

第三轮公布后，将官方名单规范化为 JSON 后导入：

```bash
amdb import-syl data/shuangyiliu_round3.json --dry-run
amdb import-syl data/shuangyiliu_round3.json
```

JSON 格式：

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

## 其他命令

```bash
amdb subjects          # 列出 14 个跟踪的 QS 学科
amdb rounds            # 列出已导入的双一流轮次
amdb stats             # 数据库统计
amdb validate          # 检查未解析的国家、孤立别名
```

## 退出码

| 代码 | 含义 |
|------|------|
| 0 | 成功 |
| 1 | 无匹配（`query`） |
| 2 | 匹配结果模糊 |
| 3 | 数据库不存在或 schema 不匹配 |
| 4 | 输入文件验证失败（`import-syl`） |

## 测试

```bash
pip install pytest
pytest tests/
```

## 许可证

MIT — 见 [LICENSE](LICENSE)。

QS 排名数据不随本软件分发。见 [NOTICE](NOTICE)。
