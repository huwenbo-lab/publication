# 核心期刊补档与摘要补全总结

生成时间：2026-06-28 12:05

## 范围

本轮重点补齐 5 本核心权威期刊：

- Annual Review of Sociology
- American Journal of Sociology
- American Sociological Review
- Social Forces
- Demography

同时对邻近高价值期刊做保守补齐：

- Journal of Marriage and Family
- Sociology of Education

2026-06-28 更新：按当前研究工作流进一步裁剪全库早期档案，删除 AJS 1950 年以前、ASR 1960 年以前、Social Forces 1950 年以前记录。裁剪报告见 `docs/reports/core_archive_pruning_report.md`。

## 数据来源与顺序

1. Crossref：按 ISSN + 年份抓取 `journal-article` 元数据，作为早期档案补齐主来源。
2. OpenAlex：按 DOI 批量补摘要，本轮补到 10,699 篇摘要。
3. Semantic Scholar：尝试第二轮补摘要，但遇到 429 限速；中止前补到少量记录。
4. 期刊官网 / DOI landing page：抽样测试 JSTOR、Duke University Press、University of Chicago Press 页面，均遇到 Cloudflare/JS challenge，不适合批量抓取。

官网和 Google 搜索适合作为后续人工式补全层：只处理高价值经典论文或具体研究问题命中的剩余缺摘要文献，不建议对数千条记录逐篇遍历。

## 最终主库概况

- 主库记录数：56,019
- 有摘要记录：43,276
- 缺摘要记录：12,743
- 期刊数：31
- SQLite FTS5 元数据检索库：`literature.db`，56,019 条，约 134 MB

## 目标期刊覆盖

| 期刊 | 条目 | 有摘要 | 摘要覆盖率 | 年份范围 |
|---|---:|---:|---:|---|
| Annual Review of Sociology | 1,178 | 1,139 | 96.7% | 1975-2026 |
| American Journal of Sociology | 3,152 | 2,899 | 92.0% | 1950-2026 |
| American Sociological Review | 3,775 | 3,041 | 80.6% | 1960-2026 |
| Social Forces | 4,568 | 4,059 | 88.9% | 1950-2026 |
| Demography | 3,406 | 3,357 | 98.6% | 1964-2026 |
| Journal of Marriage and Family | 2,578 | 2,331 | 90.4% | 1965-2026 |
| Sociology of Education | 1,291 | 1,145 | 88.7% | 1963-2026 |

## 剩余缺摘要

剩余目标期刊缺摘要清单已导出：

- `exports/core_archive_missing_abstracts_after_enrichment.csv`

按期刊计数：

| 期刊 | 剩余缺摘要 |
|---|---:|
| American Sociological Review | 734 |
| Social Forces | 509 |
| American Journal of Sociology | 253 |
| Journal of Marriage and Family | 247 |
| Sociology of Education | 146 |
| Demography | 49 |
| Annual Review of Sociology | 39 |

主要 DOI 前缀：

- `10.2307`：JSTOR 早期档案
- `10.1086`：University of Chicago Press / AJS
- `10.1111`：Wiley / JMF

这些剩余项多数是早期 metadata-only 记录，开放索引和官网 HTML 都未稳定暴露摘要。它们仍应保留在主库中，因为标题、作者、年份和 DOI 对经典文献发现很有价值。

## 非论文清理

本轮只自动删除高置信非论文条目：

- 删除 9 条 `Information for Authors` / `Instructions for Authors` / `Masthead`
- 保留 631 条边界复核候选，不自动删除
- 复核清单：`exports/non_article_needs_review.csv`

边界类型包括 Introduction、Response、Reply、Commentary 等。很多标题只是包含这些词，但实际可能是正式论文或学术争论的一部分，因此不做批量删除。

## Agent 使用规则

默认不要把全量 `articles.json` 或全量摘要放进上下文。

推荐工作流：

1. 先用 `literature.db` 或 `agent_lit_index/generated/index/default_screening.tsv` 做标题层检索。
2. 对宽松标题命中的候选，再读取摘要。
3. 对 AJS、ASR、Social Forces、Demography、ARS 的早期经典论文，即使没有摘要，也应保留在标题候选中。
4. 对缺摘要但标题高度相关的文献，优先用 DOI、官网页面、Google 搜索或 browser/computer use 单篇核查。
5. 人工补到摘要后再写回 `articles.json`，然后重建 `data.json`、部署 API、`lit_db/`、`agent_lit_index/` 和 `literature.db`。

本库当前适合“收录期刊范围内的高召回检索 + 标题初筛 + 摘要复筛”，不适合让 agent 直接遍历全量主库或把摘要直接当作全文证据。
