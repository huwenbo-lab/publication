# 文献数据库维护与自动更新流程

本文说明本仓库的日常更新、手动更新、GitHub Actions 自动更新和故障排查方式。

## 源文件与生成文件

源文件：

- `articles.json`：主数据文件。
- `raw_data/*.xls`：Web of Science 原始导出，归档保留，不要删除。
- `scripts/*.py`：维护脚本。
- `index.html`、`app.js`、`style.css`：静态前端。

生成文件：

- `data.json`、`data.js`：旧格式前端回退数据，由 `articles.json` 同步生成。
- `api/`：静态 JSON API，包括 `browse.json`、`authors.json`、单篇文章 JSON。
- `lit_db/`：供 AI agent 读取的轻量级文献索引。
- `literature.db`：SQLite FTS5 搜索库，本地和 Pages 部署时生成，不纳入 git。
- `exports/*.csv`：审计脚本输出的候选清单，默认本地保留，不纳入 git。
- `backups/*.json`：清理脚本生成的回滚备份，默认本地保留，不纳入 git。
- `logs/`、`archive/`：本地日志和整理归档，除目录说明外不纳入 git。
- `docs/reports/*.md`：质量、审计和维护报告。

## 本地手动更新

```bash
source venv/bin/activate
python scripts/update.py --dry-run
python scripts/update.py
python scripts/build_article_api.py
python scripts/build_lit_db.py
python scripts/build_search_db.py
python scripts/check_quality.py
```

`scripts/update.py` 在 CrossRef 新条目入库前会复用 `scripts/audit_non_articles.py` 的分类规则，命中的非文献候选会被跳过，不会写入 `articles.json`；跳过数量会写进 `docs/reports/update_log.md`。

如果只想更新最近 60 天：

```bash
python scripts/update.py --days 60
```

## 非文献条目审计

先 dry-run：

```bash
python scripts/audit_non_articles.py --dry-run
```

输出：

- `exports/non_article_candidates.csv`
- `exports/non_article_removed.csv`
- `exports/non_article_needs_review.csv`
- `docs/reports/non_article_audit_report.md`

只有确认高置信度清单安全后才 apply：

```bash
python scripts/audit_non_articles.py --apply
python scripts/build_article_api.py
python scripts/build_lit_db.py
python scripts/build_search_db.py
python scripts/check_quality.py
```

`--apply` 会先备份：

```text
backups/articles_before_non_article_cleaning_YYYYMMDD_HHMMSS.json
```

边界条目默认只人工复核，不自动删除。若已经人工确认 `exports/non_article_needs_review.csv` 中的条目都应删除，可以执行：

```bash
python scripts/audit_non_articles.py --apply --include-review
python scripts/build_article_api.py
python scripts/build_lit_db.py
python scripts/build_search_db.py
python scripts/check_quality.py
```

`--apply --include-review` 仍会先备份 `articles.json`，并额外输出带时间戳的删除清单归档，避免后续 dry-run 覆盖审计证据。

## 卷期字段 dry-run

当前主数据没有 `volume` / `issue`。如需评估补充可能性：

```bash
python scripts/audit_volume_issue.py --dry-run
```

输出：

- `exports/volume_issue_dry_run.csv`
- `docs/reports/volume_issue_dry_run_report.md`

这个脚本不修改主数据。后续真正补字段前，应先确定 schema，再抽样核对不同出版社的卷期、页码和 article number 表示方式。

## GitHub Actions 自动更新

`.github/workflows/update.yml`：

- 每周一运行一次。
- 支持 `workflow_dispatch` 手动触发。
- 运行 `scripts/update.py --days 30 --skip-derived`。
- 重建 `api/`、`lit_db/`、`literature.db`。
- 运行质量检查和非文献 dry-run。
- 新增条目入库前已经做一次非文献筛查，dry-run 是更新后的第二道复核。
- 如有变化，自动 commit 回 `main`。自动提交只包含主数据、派生站点文件和报告，不提交 `exports/` 或 `backups/`。

`.github/workflows/deploy-pages.yml`：

- `main` 有 push 时自动部署。
- 支持 `workflow_dispatch` 手动触发。
- 部署前重建 `api/`、`lit_db/`、`literature.db`。
- 上传静态站点 artifact，不需要后端服务器。

## GitHub 设置检查清单

请在 GitHub 仓库设置中确认：

- **Actions permissions**：允许 GitHub Actions 运行。
- **Workflow permissions**：选择 `Read and write permissions`，否则 update workflow 无法自动 commit。
- **Allow GitHub Actions to create and approve pull requests**：本流程不需要，但如果以后改成 PR 流程可再开启。
- **Pages Source**：设置为 `GitHub Actions`。
- **Branch protection**：如果 `main` 禁止 GitHub Actions push，需要改为 PR 更新流程，或给 bot 放行。
- **Secrets**：当前 workflow 不需要额外 secrets；`GITHUB_TOKEN` 由 GitHub 自动提供。

## 失败排查

- CrossRef 限速或网络失败：重新手动触发 workflow，或本地运行 `python scripts/update.py --dry-run` 确认。
- `xlrd` 缺失：确认 workflow 的 Install dependencies 步骤安装了 `xlrd`。
- Pages 页面能打开但搜索不可用：检查 deploy workflow 是否成功生成并复制 `literature.db`。
- 浏览页或高产作者为空：运行 `python scripts/build_article_api.py`，确认存在 `api/browse.json` 和 `api/authors.json`。
- AI 索引链接失效：运行 `python scripts/build_lit_db.py`，确认 `lit_db/` 被部署或提交。

## 建议提交拆分

1. 数据和审计脚本：非文献清理、审计脚本、卷期 dry-run。
2. API 和搜索构建：浏览索引、作者索引、FTS5 搜索字段。
3. 前端产品功能：浏览增强、搜索模式、收藏文件夹、高产作者。
4. Workflow 和文档：GitHub Actions、README、使用指南、维护流程。
