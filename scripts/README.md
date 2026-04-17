# scripts 目录说明

这里收纳所有维护脚本。请在项目根目录执行这些命令。

## 常用命令

```bash
source venv/bin/activate
python scripts/update.py --dry-run
python scripts/build_search_db.py
python scripts/build_lit_db.py
python scripts/build_article_api.py
python scripts/check_quality.py
```

## 脚本分工

- `build_articles.py`：从 `raw_data/*.xls` 重建 `articles.json`
- `enrich_crossref.py`：用 CrossRef 补 DOI / 摘要 / 缺失期刊
- `enrich_openalex.py`：用 OpenAlex / Semantic Scholar 继续补摘要
- `clean_data.py`：清洗非论文条目、HTML 残留和脏字段
- `update.py`：日常增量更新
- `build_lit_db.py`：重建 `lit_db/`
- `build_article_api.py`：重建 `api/`
- `build_search_db.py`：重建 `literature.db`
- `check_quality.py`：生成 `docs/reports/data_quality_report.md`
