# 文献数据库维护与自动更新

本页面向维护者。普通使用者请看[使用指南](../guides/使用指南.md)。

## 1. 权威输入与生成物

| 类型 | 路径 | Git |
|---|---|---|
| 当前权威快照 | `articles.json` | 跟踪 |
| 网页兼容数据 | `data.json` | 跟踪 |
| 对外 Agent 索引 | `lit_db/`、`agent_lit_index/generated/` | 跟踪 |
| 网页与构建脚本 | `index.html`、`app.js`、`style.css`、`scripts/` | 跟踪 |
| 部署 API / 搜索库 | `api/`、`literature.db`、`literature.db.gz` | 不跟踪，Actions 构建 |
| 本地订阅来源 | `raw_data/*.xls` | 不跟踪，不公开 |
| 审计中间物 | `.cache/`、`exports/`、`backups/` | 不跟踪 |

本地 17 份 Web of Science XLS 只覆盖部分期刊，不能精确重建当前 31 刊主库。不要用 `build_articles.py` 的输出直接覆盖已发布快照，除非正在执行经过复核的全链重建。

## 2. 环境

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Crossref 联系邮箱是可选的：

```bash
export LITDB_CONTACT_EMAIL="项目联系邮箱"
```

OpenAlex 请求必须使用维护者自己的 key：

```bash
export OPENALEX_API_KEY="你的 OpenAlex API key"
```

变量只放在 shell 或 GitHub Actions Secrets，不写进脚本、`.env.example` 的真实值或提交历史。

## 3. 日常增量更新

先检查：

```bash
python scripts/update.py --days 30 --dry-run
```

确认后写入并重建：

```bash
python scripts/update.py --days 30
```

`update.py` 会按 DOI 去重，并在写入前复用非文献分类规则。默认还会依次重建 `lit_db/`、Agent 索引、部署 API、SQLite 搜索库和质量报告，最后运行发布检查。

也可以分步执行：

```bash
python scripts/update.py --days 30 --skip-derived
python scripts/audit_non_articles.py --dry-run
python scripts/build_lit_db.py
python scripts/build_agent_lit_index.py
python scripts/build_search_db.py --rebuild
python scripts/build_article_api.py
python scripts/check_quality.py
python scripts/check_release.py --with-generated
```

## 4. 非文献条目

```bash
python scripts/audit_non_articles.py --dry-run
```

dry-run 会生成本地 CSV 和 `docs/reports/non_article_audit_report.md`。只在确认高置信度清单安全后执行：

```bash
python scripts/audit_non_articles.py --apply
```

Editorial、Introduction、Book Review、Correction、Erratum、Commentary、Reply、Response 等边界条目默认只进入人工复核。只有逐条确认后，才可使用 `--apply --include-review`。apply 前脚本会备份 `articles.json`。

## 5. 历史补档与早期边界

历史补档不是每周流程。`backfill_core_journals.py` 默认 dry-run；正式写入前必须复核 `exports/` 清单。

以下裁剪是有意的发布口径：

- American Journal of Sociology：1950+
- American Sociological Review：1960+
- Social Forces：1950+

`prune_early_core_journals.py` 用于保护和重现该边界。不要把起点前记录当作普通缺口补回。

## 6. 卷期字段

当前主数据没有 `volume` / `issue` / 页码。只可先运行：

```bash
python scripts/audit_volume_issue.py --dry-run
```

该命令不改主库。真正增加字段前，需要先确定 schema、来源和兼容策略，并抽样核对不同出版平台。

## 7. GitHub Actions

### Weekly Update

`.github/workflows/update.yml` 每周一或手动运行：

1. Crossref 增量更新；
2. 重建并提交 `data.json`、`lit_db/`、`agent_lit_index/generated/`；
3. 更新质量、非文献审计和更新日志；
4. 运行 `check_release.py`；
5. 只在确有变化时提交到 `main`。

它不提交 `api/`、SQLite、XLS、缓存、备份或 CSV。

### Deploy GitHub Pages

`.github/workflows/deploy-pages.yml` 在 `main` 更新后：

1. 临时构建 API、`lit_db/` 和 SQLite；
2. 运行包含生成物的发布检查；
3. gzip 压缩浏览器搜索库；
4. 组装并部署 Pages artifact。

## 8. GitHub 设置

- Pages Source：`GitHub Actions`
- Actions：允许运行
- Workflow permissions：更新工作流需要 `Read and write permissions`
- 如 `main` 有分支保护，改为 bot 可提交的 PR 流程
- OpenAlex 只在相应工作流确实调用它时配置 `OPENALEX_API_KEY`

## 9. 故障定位

- Crossref 限速：稍后重跑 dry-run，不要绕过间隔或关闭去重。
- OpenAlex 401/403：检查 `OPENALEX_API_KEY` 是否存在，不要把 key 打进日志。
- Pages 有概况但不能检索：确认 artifact 中有 `literature.db.gz` 和 `vendor/sqljs/`。
- 浏览索引或作者页为空：本地运行 `build_article_api.py` 检查生成日志。
- Agent 链接失效：重建并提交 `lit_db/` 与 `agent_lit_index/generated/`。
- 发布检查报告旧路径/旧数字：先重建派生物，再运行 `check_release.py --with-generated`。
