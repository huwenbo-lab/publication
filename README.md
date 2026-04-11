# 社会学与人口学期刊文献数据库

25本核心期刊、2000年至今、34,000+ 篇文章元数据（标题、摘要、作者、DOI）。

研究领域：社会分层 · 婚姻与家庭 · 人口学 · 教育社会学 · 性别 · 劳动与就业

📄 **在线浏览**：[GitHub Pages](https://huwenbo-lab.github.io/publication/)

---

## 期刊列表（25本）

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
| Population and Development Review | 0098-7921 | 2000 |
| Research in Social Stratification and Mobility | 0276-5624 | 2000 |
| Social Forces | 0037-7732 | 2000 |
| Social Science Research | 0049-089X | 2000 |
| Sociological Science | 2330-6696 | 2014 |
| Sociology | 0038-0385 | 2000 |
| Sociology of Education | 0038-0407 | 2000 |
| Socius | 2378-0231 | 2015 |
| Work, Employment and Society | 0950-0170 | 2000 |

---

## 文件结构

```
publication/
├── README.md                  # 本文件
├── CLAUDE.md                  # 项目说明（供 Claude Code 使用）
├── index.html                 # GitHub Pages 前端入口
├── app.js                     # 前端逻辑（搜索 / 浏览 / SQLite 回退）
├── style.css                  # 前端样式
├── .nojekyll                  # GitHub Pages 配置
│
├── articles.json              # 主数据文件（34k条，新格式）
├── data.json                  # 旧格式备用数据（前端回退模式使用）
├── data.js                    # JavaScript 版备用数据
├── data_quality_report.md     # 数据质量检查报告
│
├── build_articles.py          # 从 XLS 构建 articles.json
├── enrich_crossref.py         # CrossRef API 补全摘要/DOI/历史数据
├── enrich_openalex.py         # OpenAlex + Semantic Scholar 补全摘要
├── update.py                  # 定期更新脚本
├── check_quality.py           # 数据质量检查
├── build_lit_db.py            # 生成 lit_db/ 目录
├── build_article_api.py       # 生成 api/ 静态 JSON 端点
├── build_search_db.py         # 构建 SQLite FTS5 全文检索数据库
├── opensearch.xml             # 浏览器地址栏搜索描述文件
├── .github/workflows/update.yml # 每周自动更新 workflow
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
    ├── overview.json
    ├── journals.json
    └── articles/
        └── 10.1086/714825.json
```

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
python update.py              # 抓取最近 30 天新文章
python update.py --days 60    # 抓取最近 60 天
python update.py --dry-run    # 仅检查，不写入
```

更新后同步重建索引：

```bash
python build_lit_db.py        # 重建 AI 查阅索引
python build_article_api.py   # 重建静态 JSON 端点
python build_search_db.py     # 重建全文检索数据库
```

---

## 全文检索

`build_search_db.py` 基于 SQLite FTS5 构建本地全文检索数据库（`literature.db`，约 64 MB），支持对标题、摘要和作者的关键词搜索，毫秒级返回结果。

```bash
# 构建索引（首次使用，或 articles.json 更新后重建）
python build_search_db.py

# 基本搜索
python build_search_db.py --search "education inequality China"

# 限制返回条数
python build_search_db.py --search "marriage fertility" --limit 10

# 按期刊过滤
python build_search_db.py --search "stratification" --journal "American Journal of Sociology"

# 按年份范围过滤
python build_search_db.py --search "labor market" --year-from 2015 --year-to 2023

# 强制重建索引
python build_search_db.py --rebuild
```

搜索语法支持 SQLite FTS5 标准语法：
- 多个关键词默认为 AND 关系：`education inequality`
- 精确短语：`"social mobility"`
- OR 逻辑：`marriage OR cohabitation`
- NOT 逻辑：`fertility NOT mortality`

> `literature.db` 为生成文件，不纳入 git 版本管理，可随时从 `articles.json` 重建。若要在网页端启用浏览器内 SQLite 搜索，需要将该文件一并发布。

---

## 全量重建

如需从头重建（例如新增了 XLS 文件）：

```bash
source venv/bin/activate
python build_articles.py      # 从 raw_data/*.xls 重建
python enrich_crossref.py     # CrossRef 补全（耗时较长）
python enrich_openalex.py     # OpenAlex + S2 二次补全摘要
python build_lit_db.py        # 重建 AI 查阅索引
python build_article_api.py   # 重建静态 JSON 端点
python build_search_db.py     # 重建全文检索数据库
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

---

## 静态 API

`api/` 目录为机器可读导出：

```text
/api/overview.json
/api/journals.json
/api/articles/10.1086/714825.json
```

其中单篇端点按 DOI 生成，规则是把 DOI 按 `/` 拆成路径层级，再给最后一段加 `.json`。

---

## 数据来源

- **原始数据**：Web of Science 手动导出（存放于 `raw_data/`）
- **补全数据**：CrossRef API（历史数据、摘要、DOI、7本无Excel期刊）
- **更新方式**：CrossRef API 定期抓取最新文章
