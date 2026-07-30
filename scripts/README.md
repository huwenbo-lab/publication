# scripts 目录说明

这里收纳所有维护脚本。请在项目根目录执行这些命令。

## 常用命令

```bash
source .venv/bin/activate
python scripts/update.py --dry-run
python scripts/backfill_core_journals.py --journal "Annual Review of Sociology"
python scripts/prune_early_core_journals.py
python scripts/audit_non_articles.py --dry-run
python scripts/audit_volume_issue.py --dry-run
python scripts/build_article_api.py
python scripts/build_search_db.py
python scripts/build_lit_db.py
python scripts/build_agent_lit_index.py
python scripts/check_quality.py
python scripts/check_release.py --with-generated
```

## 脚本分工

- `build_articles.py`：从维护者本地的 `raw_data/*.xls` 建立部分历史底库；不能单独精确重建当前 31 刊快照
- `enrich_crossref.py`：用 CrossRef 补 DOI / 摘要 / 缺失期刊
- `enrich_openalex.py`：用 OpenAlex / Semantic Scholar 继续补摘要
- `backfill_core_journals.py`：对 ARS / AJS / ASR / Social Forces / Demography 等老牌收录期刊做早期档案补齐；默认 dry-run，确认后用 `--apply` 写入，`--include-adjacent` 可同时处理 Journal of Marriage and Family 与 Sociology of Education
- `prune_early_core_journals.py`：按当前规则删除 AJS 1950 年以前、ASR 1960 年以前、Social Forces 1950 年以前的早期记录；默认 dry-run，确认后用 `--apply` 写入并备份
- `clean_data.py`：清洗非论文条目、HTML 残留和脏字段
- `update.py`：日常增量更新；新增条目入库前会复用非文献审计规则，跳过非文献候选
- `build_lit_db.py`：重建 `lit_db/`
- `build_agent_lit_index.py`：重建 `agent_lit_index/generated/`
- `build_article_api.py`：重建 `api/`，包括单篇文章 JSON、期刊年份浏览索引 `api/browse.json` / `api/browse/by_journal_year/` 和作者索引 `api/authors.json`
- `build_search_db.py`：重建 `literature.db`，FTS5 覆盖标题、摘要、作者、作者规范化变体、期刊和年份
- `check_quality.py`：检查当前 `articles.json`，生成 `docs/reports/data_quality_report.md`
- `check_release.py`：检查主库/兼容数据一致性、公开文件边界、隐私与派生索引
- `audit_non_articles.py`：审计非文献条目；`--dry-run` 只输出清单，`--apply` 默认只删除高置信度行政性/目录性条目并自动备份，人工确认后可用 `--apply --include-review` 连同复核候选一起删除
- `audit_volume_issue.py`：dry-run 检测 `raw_data/*.xls` 中可通过 DOI 补充的卷期、页码、出版日期和文献类型字段

## 推荐重建顺序

清理或更新 `articles.json` 后，按下面顺序重建派生文件：

```bash
python scripts/build_lit_db.py
python scripts/build_agent_lit_index.py
python scripts/build_search_db.py
python scripts/build_article_api.py
python scripts/check_quality.py
python scripts/check_release.py --with-generated
```

`api/` 和 `literature.db` 是部署生成物，不提交；旧的 `data.js` 已淘汰。
`lit_db/` 与 `agent_lit_index/generated/` 是对外 Agent 产品，随主库一起更新。
