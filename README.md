# 社会学与人口学期刊文献数据库

一个可浏览、可检索、可供研究 Agent 读取的英文期刊文献元数据库。它帮助研究者建立候选文献清单，不替代数据库检索、全文阅读或引文核验。

[在线浏览](https://huwenbo-lab.github.io/publication/) · [新手指南](docs/guides/使用指南.md) · [Agent 入口](agent_lit_index/README.md) · [维护说明](scripts/README.md)

## 当前发布快照

以下统计对应 **2026-07-30** 的 `articles.json`：

| 指标 | 数值 |
|---|---:|
| 文献记录 | **56,019** |
| 收录期刊 | **31** |
| 年份范围 | **1947–2026** |
| 有摘要记录 | **43,276** |
| 缺摘要记录 | **12,743** |
| 有 DOI / 单篇静态端点 | **55,946** |

数据库只含标题、摘要、作者、期刊、年份和 DOI，不含论文 PDF 或正文。这里的“检索”是对元数据字段的检索，不是对论文全文的检索。

## 三种使用方式

### 1. 在线浏览

打开 [GitHub Pages](https://huwenbo-lab.github.io/publication/)，可按关键词、作者、期刊、年份和摘要可用性筛选；文章卡片支持 DOI 跳转、Google Scholar、收藏，以及复制 BibTeX、APA 和 AI 提示。

收藏默认只保存在当前浏览器。可选同步属于高级自托管功能：只有用户主动填写自己的端点和密钥后才会发送数据。

### 2. 本地字段检索

```bash
python scripts/build_search_db.py
python scripts/build_search_db.py --search "education inequality China"
python scripts/build_search_db.py --search "marriage fertility" --journal "Demography" --limit 10
python scripts/build_search_db.py --search "labor market" --year-from 2015 --year-to 2023
```

生成的 `literature.db` 是可重建的 SQLite FTS5 索引，不纳入 Git。

### 3. Agent / API

- `agent_lit_index/`：先做范围路由，再加载候选条目的摘要。
- `lit_db/`：按期刊和年份段拆分的轻量标题、摘要索引。
- Pages 静态 API：
  - `/api/overview.json`
  - `/api/journals.json`
  - `/api/browse.json`
  - `/api/authors.json`
  - `/api/articles/{DOI前缀}/{DOI后缀}.json`

`api/` 只在部署时从 `articles.json` 生成，不再作为数万个小文件提交到 Git。

## 数据口径

`articles.json` 是当前公开快照和所有派生物的唯一权威输入。2026 年历史补档与清理链为：

```text
46,179
  + 15,361  历史补档
= 61,540
  -      9  高置信度非文献条目
= 61,531
  -  5,512  已确认的早期档案裁剪
= 56,019
```

早期裁剪是明确的收录边界，不是待修复的缺失：

- *American Journal of Sociology*：保留 1950 年及以后；
- *American Sociological Review*：保留 1960 年及以后；
- *Social Forces*：保留 1950 年及以后。

维护或重建时不得把这些边界之前的记录自动补回。17 份本地 Web of Science XLS 只覆盖部分期刊，也不能单独精确重建当前快照。

## 收录期刊

下表为当前数据中的实际范围：

| 期刊 | 记录 | 年份 |
|---|---:|---:|
| Advances in Life Course Research | 638 | 2000–2026 |
| American Journal of Sociology | 3,152 | 1950–2026 |
| American Sociological Review | 3,775 | 1960–2026 |
| Annual Review of Sociology | 1,178 | 1975–2026 |
| Asian Population Studies | 436 | 2005–2026 |
| British Journal of Sociology | 1,746 | 1950–2026 |
| British Journal of Sociology of Education | 1,630 | 1980–2026 |
| Chinese Journal of Sociology | 265 | 2015–2026 |
| Chinese Sociological Review | 273 | 2011–2026 |
| Demographic Research | 1,862 | 1999–2026 |
| Demography | 3,406 | 1964–2026 |
| European Journal of Population | 765 | 1985–2026 |
| European Sociological Review | 1,421 | 1986–2026 |
| Gender & Society | 1,072 | 1987–2026 |
| Journal of Family Issues | 2,359 | 1980–2026 |
| Journal of Family Theory & Review | 753 | 2009–2026 |
| Journal of Marriage and Family | 2,578 | 1965–2026 |
| Population Studies | 3,715 | 1947–2026 |
| Population and Development Review | 1,124 | 1976–2026 |
| Research in Social Stratification and Mobility | 860 | 2001–2026 |
| Social Forces | 4,568 | 1950–2026 |
| Social Indicators Research | 5,938 | 1974–2026 |
| Social Psychology Quarterly | 1,320 | 1979–2026 |
| Social Science Research | 2,237 | 1972–2026 |
| Sociological Science | 403 | 2014–2026 |
| Sociology | 1,926 | 1968–2026 |
| Sociology Compass | 1,798 | 2007–2026 |
| Sociology of Education | 1,291 | 1963–2026 |
| Socius | 1,032 | 2016–2026 |
| Work and Occupations | 935 | 1982–2026 |
| Work, Employment and Society | 1,563 | 1987–2026 |

## 文件结构

```text
publication/
├── README.md
├── index.html / app.js / style.css   # 网页
├── articles.json                     # 权威主数据
├── data.json                         # 网页兼容数据，由主数据生成
├── agent_lit_index/                  # Agent 路由与公开索引
├── lit_db/                           # 轻量标题/摘要索引
├── scripts/                          # 更新、审计、构建、检查
├── docs/
│   ├── guides/                       # 普通用户指南
│   ├── reports/                      # 当前报告与历史审计
│   └── workflows/                    # 维护流程
├── raw_data/README.md                # 私有 XLS 的处理边界
└── vendor/sqljs/                     # 浏览器 SQLite 运行时及其 MIT 许可
```

`api/` 与 `literature.db` 只在部署时生成；旧的重复文件 `data.js` 已淘汰。`raw_data/*.xls`、`.cache/`、`backups/`、`exports/`、`tmp/`、`outputs/` 和 `venv/` 只保留在维护者本地。这些路径均不应提交。

## 字段

`articles.json` 每条记录包含：

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | string | 文章标题 |
| `abstract` | string | 摘要，可能为空；联系邮箱会在公开快照中脱敏 |
| `authors` | string | 作者列表，通常为 `姓, 名; 姓, 名` |
| `journal` | string | 期刊名称 |
| `year` | int | 发表年份 |
| `doi` | string | DOI，少数历史记录为空 |

`data.json` 使用旧字段名，仅供网页兼容模式。单篇 API 仅为有 DOI 的记录生成，因此当前为 55,946 个端点。

## 维护

### 环境

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

可将 `.env.example` 复制为本地 `.env`，但脚本不会自动读取该文件；请在 shell 或 GitHub Actions Secrets 中设置变量：

```bash
export LITDB_CONTACT_EMAIL="项目联系邮箱"
export OPENALEX_API_KEY="你自己的 OpenAlex API key"
```

不要把真实密钥或私人邮箱写进脚本、文档或提交历史。

### 日常更新

```bash
python scripts/update.py --dry-run
python scripts/update.py
python scripts/audit_non_articles.py --dry-run
python scripts/build_lit_db.py
python scripts/build_agent_lit_index.py
python scripts/build_search_db.py --rebuild
python scripts/build_article_api.py
python scripts/check_quality.py
python scripts/check_release.py --with-generated
```

`enrich_openalex.py` 需要 `OPENALEX_API_KEY`。历史补档、非文献删除和早期裁剪不是每周任务；如需重跑，先 dry-run、复核 CSV，并保留同一数据链的报告。

## 来源、权利与使用边界

- 书目元数据主要来自 Web of Science 导出、Crossref、OpenAlex 和 Semantic Scholar，随后经过规则清洗与去重。
- Web of Science 原始 XLS 不在公开仓库分发。
- [Crossref 的元数据复用说明](https://support.crossref.org/hc/en-us/articles/213420286-Looking-up-metadata-and-identifiers)指出，多数书目事实可广泛复用，但摘要通常仍受作者或出版社版权约束；本项目不宣称拥有第三方摘要版权。
- OpenAlex 与 Semantic Scholar 补全数据仍分别受其[官方说明](https://help.openalex.org/hc/en-us/articles/24397762024087-Pricing)和 [Semantic Scholar API License](https://www.semanticscholar.org/product/api/license)约束。
- 本仓库目前尚未选择项目级代码/文档/数据许可证。[没有许可证不等于开放授权](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)；在维护者明确选择许可证前，默认版权规则仍然适用。
- `vendor/sqljs/` 按其 MIT 许可证分发。

本库适合发现、筛选和组织候选文献。论文中的理论、方法和实证结论必须回到原文核对；不要把摘要或 AI 概括直接当作已验证证据。

## 引用

引用时请注明项目名、仓库地址、所用 commit 或 release tag，以及访问日期，例如：

> 社会学与人口学期刊文献数据库，GitHub，`huwenbo-lab/publication`，版本：`<commit-or-tag>`，访问日期：`YYYY-MM-DD`。

数据质量、更新日志和历史审计见 [`docs/reports/`](docs/reports/)。
