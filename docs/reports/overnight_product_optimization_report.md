# 文献数据库产品化优化报告

生成日期：2026-05-05
工作分支：`codex/overnight-product-optimization`

## 一、任务目标

本次任务目标是把静态社会学与人口学文献库进一步产品化，用于科研检索、文献综述、研究选题、期刊追踪、作者追踪、AI agent 读取和长期自动更新。约束条件已遵守：未 push、未部署、未删除 `raw_data/`，也没有把 GitHub Pages 静态站点改成后端项目。

## 二、初始仓库状态

- 初始命令：`git status --short --branch`
- 初始结果：`## main`
- 创建分支：沙箱内第一次 `git switch -c codex/overnight-product-optimization` 因 Git ref 写入权限失败；经授权后成功创建并切换到 `codex/overnight-product-optimization`。
- 初始短状态没有显示未提交修改；后续按小步增量修改，未回滚用户已有文件。

## 三、快速诊断

- 前端原本已有搜索、浏览、收藏和 dashboard，但期刊浏览主要由前端扫描数据临时计算，没有专门的浏览 API；收藏是 `publication:favorites:v1` 平面数组；高产作者只在 dashboard 中展示，不是独立可筛选视图。
- `articles.json` 初始有 35,256 条，只包含 `title`、`abstract`、`authors`、`journal`、`year`、`doi` 六个字段；没有 `volume`、`issue`、`pages`、`publication_date`、`source`、`publication_type`。
- 搜索优先使用浏览器内 SQLite FTS5 `literature.db`，不可用时回退到 `data.json` 前端过滤；原 FTS 主要覆盖标题、摘要和作者。
- 收藏使用 `localStorage`，没有文件夹树和导入功能。
- `.github/workflows/update.yml` 和 `deploy-pages.yml` 已存在，但更新流程未覆盖所有新增派生文件和非文献审计。
- 今晚可直接实现浏览索引、作者索引、搜索增强、收藏文件夹、Top Scholars、非文献审计与 workflow 完善；卷期层级因主数据缺字段，只做 dry-run 检测方案，不硬造。

## 四、实际完成的功能

### 1. 期刊—年份—文章浏览

- 新增静态索引：`api/browse.json` 和 `api/browse/by_journal_year/*.json`。
- 前端“浏览”入口支持点击期刊、年份，显示该年文章列表，并支持按年份、标题、作者排序。
- 文章卡片显示标题、作者、期刊、年份、DOI、摘要片段、收藏、DOI、Google Scholar、复制 citation、复制给 AI。
- 浏览状态写入 URL query/hash 相关前端状态，刷新后尽量保持当前位置。
- 当前未实现“期刊—年份—卷期—文章”，原因是主数据没有 `volume` / `issue`。已新增 `scripts/audit_volume_issue.py --dry-run`，用于检测 `raw_data` 可补充的卷期、页码、出版日期字段。

### 2. 科研搜索增强

- 搜索模式新增：全部字段、标题与摘要、作者、期刊。
- 搜索范围覆盖标题、摘要、作者、期刊和年份。
- `scripts/build_search_db.py` 扩展 FTS5 字段，加入 `author_search`、`journal_search`、`year_search`。
- 作者搜索做保守规范化，处理大小写、逗号格式、姓名顺序和常见首字母形式。
- 结果过滤器支持期刊、年份范围、是否有摘要、是否已收藏；排序支持相关度、年份新到旧、年份旧到新、期刊、作者。
- 仍优先使用 SQLite FTS5，保留静态 JSON fallback。

### 3. 收藏文件夹树

- 收藏 schema 升级到 `publication:favorites:v2`，含版本号。
- 旧 `publication:favorites:v1` 会自动迁移到 v2，并进入“未分类收藏”。
- 收藏库 modal 支持新建多级文件夹、重命名、删除空文件夹、移动文章、移回未分类、移除收藏、导入 JSON、导出 JSON / CSV / BibTeX。
- 未引入服务器、登录或后端数据库。

### 4. Top Scholars 视图

- 导航新增“高产作者 / Top Scholars”入口。
- 新增 `api/authors.json`，由 `scripts/build_article_api.py` 生成。
- 默认阈值 20 篇，支持 10 / 20 / 30 切换。
- 每个作者显示规范化作者名、发文数、主要期刊、年份范围和最近年份。
- 点击作者后显示文章列表，并可按期刊、年份范围过滤。
- 作者名规范化保持保守；报告和文档已说明同名、缩写、改姓和跨期刊格式差异的局限。

### 5. 非文献条目筛查与清理

- 新增 `scripts/audit_non_articles.py`，支持 `--dry-run`、`--apply`、`--apply --include-review`。
- 高置信度行政性/目录性条目默认可自动删除；Editorial、Introduction、Book Review、Correction、Erratum、Commentary、Reply、Response 等默认进入人工复核。
- 根据用户确认，本次把原 `exports/non_article_needs_review.csv` 中 2,690 条也删除。
- 删除前总记录数：35,256
- 第一次高置信度删除：80 条；备份 `backups/articles_before_non_article_cleaning_20260505_020150.json`
- 第二次经人工确认删除复核候选：2,690 条；备份 `backups/articles_before_non_article_cleaning_20260505_195708.json`
- 累计删除：2,770 条
- 当前总记录数：32,486
- 当前 dry-run 候选数：0，人工复核数：0
- 删除清单：`exports/non_article_removed.csv`
- 删除清单归档：`exports/non_article_removed_20260505_all_removed.csv`
- 当前候选清单：`exports/non_article_candidates.csv`
- 当前人工复核清单：`exports/non_article_needs_review.csv`
- 审计报告：`docs/reports/non_article_audit_report.md`

### 6. 自动更新中的非文献审核

- `scripts/update.py` 已在 CrossRef 新条目入库前调用 `audit_non_articles.classify_article()`。
- 命中非文献或复核候选的新条目会被跳过，不写入 `articles.json`。
- 跳过数量会写入 `docs/reports/update_log.md`。
- `update.py` 的派生构建流程还会运行 `scripts/audit_non_articles.py --dry-run`，作为更新后的第二道复核。
- `.github/workflows/update.yml` 会运行更新、重建 `api/`、`lit_db/`、`literature.db`、质量检查和非文献 dry-run；如有变化可自动 commit 回 `main`，本地未 push。

### 7. 可视化/前端需求与脚本关系

- 已实现的可视化/交互需求主要在 `index.html`、`app.js`、`style.css`：期刊浏览、搜索模式、收藏文件夹、Top Scholars、dashboard 入口。
- 脚本实现的是这些视图所需的静态数据层：`api/browse.json`、`api/browse/by_journal_year/*.json`、`api/authors.json`、`literature.db`、`lit_db/`。
- 没有把“可视化”全部放进脚本，也不应该这样做；脚本负责可审计生成数据，前端负责浏览和交互。
- 尚未实现卷期可视化，因为主数据没有可靠 `volume` / `issue` 字段；已提供 dry-run 补充方案。

## 五、修改过的主要文件

- `.github/workflows/update.yml`
- `.github/workflows/deploy-pages.yml`
- `index.html`
- `app.js`
- `style.css`
- `articles.json`
- `data.json`
- `data.js`
- `api/README.md`
- `api/dashboard.json`
- `api/journals.json`
- `api/overview.json`
- `lit_db/`
- `scripts/build_article_api.py`
- `scripts/build_lit_db.py`
- `scripts/build_search_db.py`
- `scripts/update.py`
- `README.md`
- `AGENTS.md`
- `scripts/README.md`
- `docs/guides/使用指南.md`
- `docs/workflows/maintenance_workflows.md`
- `docs/reports/data_quality_report.md`
- `docs/reports/non_article_audit_report.md`
- `docs/reports/overnight_product_optimization_report.md`

## 六、新增文件和本地审计产物

- `scripts/audit_non_articles.py`
- `scripts/audit_volume_issue.py`
- `api/browse.json`
- `api/browse/by_journal_year/*.json`
- `api/authors.json`
- `docs/reports/non_article_audit_report.md`
- `docs/reports/volume_issue_dry_run_report.md`
- `docs/workflows/maintenance_workflows.md`

本地审计产物，默认不提交 Git：

- `exports/non_article_candidates.csv`
- `exports/non_article_removed.csv`
- `exports/non_article_removed_20260505_all_removed.csv`
- `exports/non_article_needs_review.csv`
- `exports/volume_issue_dry_run.csv`
- `backups/articles_before_non_article_cleaning_20260505_020150.json`
- `backups/articles_before_non_article_cleaning_20260505_195708.json`

## 七、新增或修改的 API 文件

- `api/browse.json`：25 本期刊的期刊—年份总览。
- `api/browse/by_journal_year/*.json`：按期刊拆分的年份和文章列表，前端按需加载。
- `api/authors.json`：作者索引，含阈值统计、作者变体、期刊、年份范围和文章引用。
- `api/articles/`：删除了 2,770 个非文献条目的单篇 JSON 端点。
- `api/dashboard.json`、`api/journals.json`、`api/overview.json` 随数据清理同步重建。

## 八、运行过的命令和结果

| 命令 | 结果 |
|---|---|
| `git status --short --branch` | 初始为 `## main`；最终在 `codex/overnight-product-optimization` |
| `git switch -c codex/overnight-product-optimization` | 沙箱内失败；授权后成功 |
| `python3 scripts/audit_non_articles.py --dry-run` | 初次候选 2,770；清理后候选 0 |
| `python3 scripts/audit_non_articles.py --apply` | 删除高置信度 80 条并备份 |
| `python3 scripts/audit_non_articles.py --apply --include-review` | 删除人工确认复核候选 2,690 条并备份 |
| `python3 scripts/build_article_api.py` | 生成 32,410 个单篇 JSON 端点，并生成浏览/作者索引 |
| `python3 scripts/build_lit_db.py` | 成功，加载 32,486 篇文章 |
| `python3 scripts/build_search_db.py` | 成功，生成 `literature.db`，32,486 篇，约 81.9MB |
| `python3 scripts/check_quality.py` | 成功，生成 `docs/reports/data_quality_report.md` |
| `python3 scripts/audit_volume_issue.py --dry-run` | raw_data 12,665 行，候选 12,408 行 |
| `python3 -m py_compile scripts/build_article_api.py scripts/build_search_db.py scripts/build_lit_db.py scripts/audit_non_articles.py scripts/audit_volume_issue.py scripts/update.py` | 通过 |
| `node --check app.js` | 通过 |
| `ruby -ryaml -e ... .github/workflows/update.yml .github/workflows/deploy-pages.yml` | 两个 workflow YAML 均可解析 |
| `python3 -c ... articles/data/authors/browse count` | `articles` 32,486；`data` 32,486；Top Scholars 阈值 10/20/30 为 711/138/37；期刊 25 |
| `git diff --stat` / `git diff --shortstat` | 大量生成文件变化；shortstat 为 2,881 个已跟踪文件变化，2,786 行新增，153,998 行删除，主要来自删除 2,770 条非文献及重建 `api/`、`lit_db/`、`data.*` |
| `git status --short --branch` | 当前分支有修改、删除和未跟踪生成文件，未 push |

## 九、失败命令、错误和处理

- `git switch -c codex/overnight-product-optimization`：沙箱内无法写 Git ref；经授权后成功。
- `git switch -c codex-overnight-product-optimization`：同样因 `.git/refs/heads/*.lock` 写入权限失败；放弃回退名。
- 一次 `python3 -c` 字段检查命令：shell 换行转义导致 `SyntaxError`；改用单行命令成功。
- `python3 -m http.server 8765`：端口已占用；改用 8766 完成 HTTP smoke test。
- `pgrep` / `kill` 停止临时服务器时受沙箱限制；经授权停止。

## 十、风险点和未完成事项

- `api/authors.json` 约 52MB，已按需加载，但 Top Scholars 首次进入仍会下载较大文件；后续可拆成作者总览和单作者详情。
- 作者规范化保守，不强行合并 `Smith, J.` 与 `Smith, John`；同名作者和姓名变体仍需人工理解。
- `volume` / `issue` 未写入主数据；后续需先定 schema，再用 `scripts/audit_volume_issue.py --dry-run` 输出抽样核对。
- `check_quality.py` 仍偏向 raw_data Excel 质量检查，不完全覆盖 CrossRef/OpenAlex 补全后的主数据。
- 本地没有做完整浏览器截图回归；已做 JS 语法、YAML 解析、静态索引、搜索库、质量检查和 HTTP smoke test。

## 十一、明天最应该检查的事项

1. 手动打开网页检查“浏览”“搜索”“我的收藏”“高产作者”四个入口。
2. 抽查 `exports/non_article_removed.csv` 或 `exports/non_article_removed_20260505_all_removed.csv`，确认 2,770 条确实都不应保留。
3. 检查 GitHub 设置：Pages Source 为 GitHub Actions，Workflow permissions 为 Read and write，`main` 分支保护是否允许 Actions bot 自动 commit。
4. `backups/` 和 `exports/` 默认不纳入 commit；需要审计时在本地查看，或另行压缩归档保存。
5. 评估 `api/authors.json` 是否需要拆分，以降低 Top Scholars 首次加载体积。

## 十二、建议 commit message

```text
feat: productize literature browsing and curation workflows
```

## 十三、建议拆分 commit

1. `chore(data): remove audited non-article records`
   - `articles.json`、`data.json`、`data.js`、`api/articles/` 删除、`lit_db/`
2. `feat(api): add browse and author indexes`
   - `scripts/build_article_api.py`、`api/browse.json`、`api/browse/`、`api/authors.json`
3. `feat(search): expand scholarly search fields`
   - `scripts/build_search_db.py`、`scripts/update.py`
4. `feat(frontend): add browse, scholars, and favorite folders`
   - `index.html`、`app.js`、`style.css`
5. `chore(workflows-docs): document automated maintenance`
   - `.github/workflows/*.yml`、`README.md`、`AGENTS.md`、`scripts/README.md`、`docs/guides/使用指南.md`、`docs/workflows/maintenance_workflows.md`、本报告
