# 社会学与人口学期刊文献数据库

31本核心期刊、46,179 条清洗后文章元数据（标题、摘要、作者、DOI），覆盖年份 1896–2026。

研究领域：社会分层 · 婚姻与家庭 · 人口学 · 教育社会学 · 性别 · 劳动与就业

📄 **在线浏览**：[GitHub Pages](https://huwenbo-lab.github.io/publication/)

---

## 快速导航

- 普通使用者：看 [docs/guides/使用指南.md](docs/guides/使用指南.md)
- Agent 文献入口：看 [agent_lit_index/README.md](agent_lit_index/README.md)
- 数据与站点入口：`index.html`、`app.js`、`style.css`、`articles.json`、`data.json`、`api/`、`lit_db/`
- 维护脚本：看 [scripts/README.md](scripts/README.md)
- 自动更新：看 [docs/workflows/maintenance_workflows.md](docs/workflows/maintenance_workflows.md)
- 报告与更新日志：看 [docs/reports/](docs/reports)
- 数据源策略：看 [docs/reports/source_strategy_crossref_openalex.md](docs/reports/source_strategy_crossref_openalex.md)
- 内部规划/交接：看 [docs/README.md](docs/README.md)

---

## 期刊列表（31本）

| 期刊 | ISSN | 数据起始年 |
|---|---|---|
| American Journal of Sociology | 0002-9602 | 2000 |
| American Sociological Review | 0003-1224 | 2000 |
| Annual Review of Sociology | 0360-0572 | 2000 |
| Asian Population Studies | 1744-1730 | 2005 |
| British Journal of Sociology | 0007-1315 | 2000 |
| British Journal of Sociology of Education | 0142-5692 | 2000 |
| Chinese Journal of Sociology | 2057-150X | 2015 |
| Chinese Sociological Review | 2162-0555 | 2000 |
| Demographic Research | 1435-9871 | 2000 |
| Demography | 0070-3370 | 2000 |
| European Journal of Population | 0168-6577 | 2000 |
| European Sociological Review | 0266-7215 | 2000 |
| Gender & Society | 0891-2432 | 2000 |
| Journal of Family Issues | 0192-513X | 2000 |
| Journal of Family Theory & Review | 1756-2570 | 2009 |
| Journal of Marriage and Family | 0022-2445 | 2000 |
| Population Studies | 0032-4728 | 1947 |
| Population and Development Review | 0098-7921 | 2000 |
| Research in Social Stratification and Mobility | 0276-5624 | 2000 |
| Social Indicators Research | 0303-8300 | 1974 |
| Social Forces | 0037-7732 | 2000 |
| Social Psychology Quarterly | 0190-2725 | 1979 |
| Social Science Research | 0049-089X | 2000 |
| Sociology Compass | 1751-9020 | 2007 |
| Sociological Science | 2330-6696 | 2014 |
| Sociology | 0038-0385 | 2000 |
| Sociology of Education | 0038-0407 | 2000 |
| Socius | 2378-0231 | 2015 |
| Advances in Life Course Research | 1569-4909 | 2000 |
| Work and Occupations | 0730-8884 | 1982 |
| Work, Employment and Society | 0950-0170 | 2000 |

---

## 文件结构

```
publication/
├── README.md                  # 本文件
├── CLAUDE.md                  # 项目说明（供 Claude Code 使用）
├── AGENTS.md                  # Codex / agent 工作说明
├── index.html                 # GitHub Pages 前端入口
├── app.js                     # 前端逻辑（搜索 / 浏览 / SQLite 回退）
├── style.css                  # 前端样式
├── .nojekyll                  # GitHub Pages 配置
├── .github/workflows/         # 自动更新与 Pages 部署
│
├── articles.json              # 主数据文件（46,179条，新格式）
├── data.json                  # 旧格式备用数据（前端回退模式使用）
├── data.js                    # JavaScript 版备用数据
│
├── opensearch.xml             # 浏览器地址栏搜索描述文件
│
├── scripts/                   # 所有维护脚本集中在这里
│   ├── README.md              # 常用命令速查
│   ├── build_articles.py
│   ├── enrich_crossref.py
│   ├── enrich_openalex.py
│   ├── update.py
│   ├── check_quality.py
│   ├── build_lit_db.py
│   ├── build_article_api.py
│   ├── build_search_db.py
│   ├── audit_non_articles.py
│   ├── audit_volume_issue.py
│   └── clean_data.py
│
├── docs/
│   ├── README.md              # 文档导航
│   ├── guides/                # 面向普通用户的使用文档
│   ├── reports/               # 质量报告、更新日志
│   ├── plans/                 # 历史规划文档
│   └── handoff/               # agent 交接资料
│
├── data/
│   └── README.md              # 数据组织约定；运行时数据暂保留根目录以兼容 Pages
│
├── raw_data/                  # Web of Science 原始导出文件（归档）
│   └── *.xls                  # 17 本期刊的 Excel 导出文件
│
├── lit_db/                    # 轻量级文献索引（供 AI 查阅）
│   ├── overview.md            # 数据库概况（~3KB，可直接给 AI 读）
│   ├── titles/
│   │   ├── all_titles.tsv     # 全量标题索引，可 grep（~5MB）
│   │   └── by_journal/        # 按期刊：每个文件含该刊所有标题
│   └── abstracts/
│       ├── 2020_2026/         # 近6年文章，含摘要片段，按期刊
│       ├── 2010_2019/         # 2010–2019 年
│       └── 2000_2009/         # 2000–2009 年
└── api/                       # 静态 JSON 端点（供 AI / 外部工具读取）
    ├── dashboard.json
    ├── overview.json
    ├── journals.json
    ├── browse.json
    ├── authors.json
    ├── browse/
    │   └── by_journal_year/
    └── articles/
        └── 10.1086/714825.json

# 本地但默认不提交
backups/                       # 清理前自动备份
exports/                       # 审计 CSV 输出
logs/                          # 本地日志
archive/                       # 本地归档和整理前快照
literature.db                  # 本地 SQLite 搜索库，部署时重建
```

### 目录管理规则

- 正式数据与发布产物保留在根目录、`api/`、`lit_db/`、`agent_lit_index/`、`docs/` 和 `scripts/`。
- 本地备份、临时脚本、一次性导出和历史整理材料统一放入 `_local/`，不提交 GitHub。
- 可从脚本重建的本地数据库 `literature.db` 不纳入 git；如需网页端使用，由部署流程或本地脚本重新生成。
- 不要把 `venv/`、`.cache/`、`__pycache__/`、`.wrangler/`、日志文件和本地备份推到仓库。

当前为了不破坏 GitHub Pages，运行时入口和数据仍保留在根目录。`data/`、`logs/`、`archive/` 主要用于说明、日志和本地归档；大规模迁移路径前必须同步修改前端、脚本和 workflow。

---

## 数据字段

`articles.json` 中每条记录包含 6 个字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | string | 文章标题 |
| `abstract` | string | 摘要（部分早期文章可能为空） |
| `authors` | string | 作者列表，格式：`姓, 名; 姓, 名` |
| `journal` | string | 期刊名称 |
| `year` | int | 发表年份 |
| `doi` | string | DOI 标识符 |

> `data.json` / `data.js` 使用旧字段名（`Source Title`, `Publication Year` 等），现主要作为前端回退模式的数据源。

---

## 日常更新

```bash
source venv/bin/activate
python scripts/update.py              # 抓取最近 30 天新文章
python scripts/update.py --days 60    # 抓取最近 60 天
python scripts/update.py --dry-run    # 仅检查，不写入
```

`update.py` 会在新文献入库前调用非文献审计规则，跳过 Editorial、Book Review、Correction、Issue Information 等候选条目，并把跳过数量写入更新日志。更新后仍会再跑一次 `audit_non_articles.py --dry-run` 作为复核。

更新后同步重建索引：

```bash
python scripts/build_lit_db.py        # 重建 AI 查阅索引
python scripts/build_article_api.py   # 重建静态 JSON 端点
python scripts/build_search_db.py     # 重建全文检索数据库
```

如需审计非文献条目：

```bash
python scripts/audit_non_articles.py --dry-run   # 只生成候选清单和报告
python scripts/audit_non_articles.py --apply     # 只删除高置信度非文献条目，先自动备份
python scripts/audit_non_articles.py --apply --include-review  # 人工确认后连同复核候选一起删除
```

如需评估卷期字段补充可能性：

```bash
python scripts/audit_volume_issue.py --dry-run
```

---

## 全文检索

`scripts/build_search_db.py` 基于 SQLite FTS5 构建本地全文检索数据库（`literature.db`），支持对标题、摘要、作者、作者规范化变体、期刊和年份的关键词搜索，毫秒级返回结果。

```bash
# 构建索引（首次使用，或 articles.json 更新后重建）
python scripts/build_search_db.py

# 基本搜索
python scripts/build_search_db.py --search "education inequality China"

# 限制返回条数
python scripts/build_search_db.py --search "marriage fertility" --limit 10

# 按期刊过滤
python scripts/build_search_db.py --search "stratification" --journal "American Journal of Sociology"

# 按年份范围过滤
python scripts/build_search_db.py --search "labor market" --year-from 2015 --year-to 2023

# 强制重建索引
python scripts/build_search_db.py --rebuild
```

搜索语法支持 SQLite FTS5 标准语法：
- 多个关键词默认为 AND 关系：`education inequality`
- 精确短语：`"social mobility"`
- OR 逻辑：`marriage OR cohabitation`
- NOT 逻辑：`fertility NOT mortality`

> `literature.db` 为生成文件，不纳入 git 版本管理，可随时从 `articles.json` 重建。当前仓库采用“Pages 部署产物单独发布”的方式：`main` 分支不保存数据库文件，但 GitHub Pages 部署时会自动构建并携带 `literature.db`，因此网页端仍可直接使用浏览器内 SQLite 搜索。

> 如果你刚新增了 `deploy-pages.yml`，还需要在仓库设置中把 GitHub Pages 的来源切换到 **GitHub Actions**。这是一次性设置，之后每次推送 `main` 都会自动重新发布站点。

---

## 全量重建

如需从头重建（例如新增了 XLS 文件）：

```bash
source venv/bin/activate
python scripts/build_articles.py      # 从 raw_data/*.xls 重建
python scripts/enrich_crossref.py     # CrossRef 补全（耗时较长）
python scripts/enrich_openalex.py     # OpenAlex + S2 二次补全摘要
python scripts/build_lit_db.py        # 重建 AI 查阅索引
python scripts/build_article_api.py   # 重建静态 JSON 端点
python scripts/build_search_db.py     # 重建全文检索数据库
```

---

## AI 查阅文献库

`lit_db/` 目录为 AI agent 设计的两步检索结构：

**第一步：标题初筛**（按期刊加载，每个文件 50–420KB）

```
https://raw.githubusercontent.com/huwenbo-lab/publication/main/lit_db/titles/by_journal/Demography.md
```

**第二步：摘要精读**（按期刊 × 年份段，每个文件 50–490KB）

```
https://raw.githubusercontent.com/huwenbo-lab/publication/main/lit_db/abstracts/2020_2026/Demography.md
```

从这里开始：[`lit_db/overview.md`](lit_db/overview.md)

网页端文章详情弹窗也会直接给出：
- 单篇 JSON：`/api/articles/[DOI路径].json`
- 本刊标题索引 raw URL
- 同年份段摘要 raw URL
- 可复制给 AI 的提示词

首页还会直接读取：
- `api/dashboard.json`：数据库概况、年度趋势、热门关键词、高产作者与期刊分布
- `api/browse.json` 与 `api/browse/by_journal_year/*.json`：期刊—年份—文章浏览索引
- `api/authors.json`：高产作者和作者文章列表索引

---

## 静态 API

`api/` 目录为机器可读导出：

```text
/api/dashboard.json
/api/overview.json
/api/journals.json
/api/browse.json
/api/authors.json
/api/browse/by_journal_year/Demography.json
/api/articles/10.1086/714825.json
```

其中单篇端点按 DOI 生成，规则是把 DOI 按 `/` 拆成路径层级，再给最后一段加 `.json`。

`api/browse.json` 当前只提供“期刊—年份—文章”层级；主数据尚无 `volume` / `issue` 字段，不硬造卷期。`scripts/audit_volume_issue.py` 会从 `raw_data/*.xls` dry-run 检测可按 DOI 补充的卷期字段。

`api/authors.json` 使用保守作者名规范化：大小写、标点、`Smith, John` / `John Smith` 顺序差异会进入检索变体；但全名和首字母名不强行合并，以免误合并同姓作者。

---

## 数据来源

- **原始数据**：Web of Science 手动导出（存放于 `raw_data/`）
- **主更新源**：Crossref API（按 ISSN / DOI / 日期抓取期刊文章）
- **增强补全源**：OpenAlex API（建议后续用于作者、机构、主题、引用、开放获取等增强字段）
- **当前建议**：Crossref 继续作为主更新源，OpenAlex 作为 DOI 级补全和分析增强源。理由见 [Crossref 与 OpenAlex 数据源策略建议](docs/reports/source_strategy_crossref_openalex.md)。
- **非文献审核**：新增条目入库前会运行非文献规则；命中候选会被跳过，并写入更新日志。

---

## GitHub Pages 与自动更新

- `deploy-pages.yml`：推送 `main` 后重建 `api/`、`lit_db/`、`literature.db`，再部署静态站点。
- `update.yml`：每周一自动抓取新文献，重建派生文件，运行质量检查和非文献 dry-run，并在有变化时 commit 回 `main`。
- 需要在 GitHub 设置中确认 Pages Source 为 **GitHub Actions**，Workflow permissions 为 **Read and write permissions**。

---

## AI agent 使用方式

AI 可以直接遍历和读取本仓库的结构化数据来回答问题，例如：

> 帮我找 2010-2025 年发表于 Demography 和 Journal of Marriage and Family、主题与 fertility decline 相关的文献。

推荐读取顺序：

1. 先读 `api/browse.json` 或 `api/browse/by_journal_year/*.json`，按期刊和年份缩小范围。
2. 再读 `lit_db/titles/by_journal/*.md` 做标题初筛。
3. 对候选文章读取 `api/articles/{doi}.json` 或对应年份段摘要文件。
4. 如果在本地运行，可以直接用 `literature.db` 或 `scripts/build_search_db.py --search ...` 做全文检索。

这个流程适合 3 万多篇规模的数据库；不要把整个 `articles.json` 一次性塞进单个 AI 上下文，应按期刊、年份、主题关键词分批检索。

---

## Push 前检查

```bash
git status --short
python3 -m py_compile scripts/*.py
node --check app.js
ruby -ryaml -e 'ARGV.each { |p| YAML.load_file(p); puts "ok #{p}" }' .github/workflows/update.yml .github/workflows/deploy-pages.yml
python3 scripts/audit_non_articles.py --dry-run
```

默认不提交：

- `literature.db`
- `venv/`
- `.cache/`
- `backups/`
- `exports/`
- `logs/` 中除 `README.md` 外的文件
- `archive/` 中除 `README.md` 外的文件
- `.env*`、密钥、token、系统缓存

---

## 下一步计划

1. 拆分 `api/authors.json`，改为作者 overview + 单作者详情，降低 Top Scholars 首次加载体积。
2. 新增 OpenAlex DOI 级 dry-run 补全脚本，先输出候选 CSV，不直接覆盖主数据。
3. 设计可选增强字段 schema：`openalex_id`、`orcid`、`institutions`、`topics`、`cited_by_count`、`open_access`。
4. 评估是否逐步淘汰 `data.js`，减少根目录重复大文件。
5. 在前端增加“AI 检索提示”入口，指导按期刊、年份、主题分批读取数据库。
