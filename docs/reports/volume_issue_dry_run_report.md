# 卷期字段补充 dry-run 报告

生成时间：2026-05-05 02:02

## 结论

- 本脚本没有修改主数据。
- `articles.json` 当前没有 `volume`、`issue`、`pages`、`publication_date`、`publication_type`、`document_type` 字段。
- `raw_data/*.xls` 中存在这些字段，但只覆盖部分期刊和原始 WoS 导出范围。
- 建议后续先确定主数据 schema，再用 DOI 精确匹配写入；对 raw_data 覆盖不到的期刊，再用 CrossRef/OpenAlex dry-run 补充。

## 统计

- `articles.json` 记录数：35,176
- raw_data 行数：12,665
- 输出候选行数：12,408
- DOI 匹配主数据且存在卷期/页码等字段：12,347
- DOI 匹配且至少有 volume 或 issue：11,989
- 输出 CSV：`exports/volume_issue_dry_run.csv`

## 匹配状态

| 状态 | 数量 |
|---|---:|
| matched | 12347 |
| raw_doi_not_in_articles | 61 |

## 后续补充方案

1. 新增主数据字段：`volume`、`issue`、`start_page`、`end_page`、`article_number`、`publication_date`、`publication_type`、`document_type`，并更新 `data.json`/`data.js` 兼容字段映射。
2. 先用本 CSV 中 `match_status=matched` 且 DOI 唯一的记录补充 raw_data 覆盖范围。
3. 对 raw_data 无覆盖或 DOI 不匹配的期刊，新增 CrossRef/OpenAlex dry-run，只输出候选，不直接写入。
4. 抽样人工核对不同出版社的卷期格式，确认空字符串、early access、article number 与页码的表示方式。
