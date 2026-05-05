# 项目整理报告

生成日期：2026-05-05

## 整理原则

- 不删除重要文件。
- 先在 `archive/project_cleanup_20260505/` 保存整理前状态、文件清单和关键配置副本。
- 保留 GitHub Pages 当前运行路径：`index.html`、`app.js`、`style.css`、`data.json`、`api/`、`lit_db/` 不做大规模搬迁。
- 大文件备份、审计 CSV、日志、缓存、虚拟环境和密钥类文件不进入 Git。

## 当前目录分类

| 类别 | 路径 | 处理方式 |
|---|---|---|
| 网页入口 | `index.html`、`app.js`、`style.css`、`opensearch.xml`、`.nojekyll` | 保留根目录，保证 Pages 静态访问 |
| 主数据 | `articles.json` | 保留根目录，脚本和文档继续以此为源 |
| 前端 fallback 数据 | `data.json`、`data.js` | 保留根目录，未来可再评估是否淘汰 |
| 原始数据 | `raw_data/*.xls` | 保留不动，作为 WoS 原始归档 |
| 静态 API | `api/` | 保留，前端和 AI agent 直接读取 |
| AI 索引 | `lit_db/` | 保留，供 AI agent 读取 |
| 维护脚本 | `scripts/` | 保留，脚本统一从 `scripts/_paths.py` 解析根目录 |
| 文档 | `docs/`、`README.md`、`AGENTS.md`、`CLAUDE.md` | 保留并补充维护文档 |
| GitHub 配置 | `.github/workflows/`、`.gitignore` | 保留并更新忽略规则和自动更新提交范围 |
| 依赖缓存 | `venv/`、`.cache/`、`scripts/__pycache__/` | 通过 `.gitignore` 忽略 |
| 本地搜索库 | `literature.db` | 通过 `.gitignore` 忽略，由脚本或 Pages workflow 重建 |
| 审计输出 | `exports/` | 本地保留，默认不提交 |
| 回滚备份 | `backups/` | 本地保留，默认不提交 |
| 临时日志 | `logs/` | 新增目录，默认只提交 `logs/README.md` |
| 本地归档 | `archive/` | 新增目录，默认只提交 `archive/README.md` |
| 数据组织说明 | `data/README.md` | 新增，解释为何运行时数据暂保留根目录 |

## 本次实际整理

- 新增 `data/README.md`、`logs/README.md`、`archive/README.md`。
- 更新 `.gitignore`，排除日志、缓存、备份、导出 CSV、密钥、SQLite 数据库和本地归档。
- 更新 `.github/workflows/update.yml`，自动更新不再尝试提交 `exports/*.csv`。
- 新增 `docs/reports/source_strategy_crossref_openalex.md`，记录 Crossref/OpenAlex 数据源建议。
- 更新 README，说明当前目录结构、数据来源、运行方式、更新方式和下一步计划。

## 保守保留的路径

以下路径虽然更像数据或生成物，但为了不破坏前端和 GitHub Pages，当前不搬迁：

- `articles.json`
- `data.json`
- `data.js`
- `api/`
- `lit_db/`
- `raw_data/`

如果后续要迁入 `data/` 或 `public/`，应先改脚本和前端路径，再通过本地静态服务器和 Pages workflow 验证。

## Push 前注意

- `literature.db`、`venv/`、`.cache/`、`backups/`、`exports/`、`archive/project_cleanup_20260505/` 不应提交。
- `api/authors.json` 约 52MB，低于 GitHub 单文件 100MB 限制，但仍偏大；后续建议拆成作者 overview + 单作者详情。
- `articles.json`、`data.json`、`data.js` 各约 39-41MB，也偏大但当前是站点运行需要。

## Push 前检查

- `python3 -m py_compile scripts/*.py`：通过。
- `node --check app.js`：通过。
- GitHub Actions YAML 解析检查：`update.yml`、`deploy-pages.yml` 通过。
- `scripts/audit_non_articles.py --dry-run`：当前候选 0、自动删除 0、人工复核 0。
- 暂存文件敏感路径扫描：未发现 `venv/`、`.cache/`、`backups/`、`exports/`、`literature.db`、密钥类文件或本地归档快照。
- `git diff --cached --check`：通过。
- 大文件检查：未发现超过 GitHub 100MB 单文件限制的待提交文件。
