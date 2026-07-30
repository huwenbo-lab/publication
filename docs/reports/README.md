# 数据报告索引

本目录同时保留当前数据快照和历史处理记录。阅读带数字的报告时，请先看生成日期和适用范围；数据库的当前机器可读统计以 [Pages API 概况](https://huwenbo-lab.github.io/publication/api/overview.json) 为准。

## 当前状态与维护记录

- [补档与摘要补全总结](core_archive_completion_report.md)：2026-06-28 主库快照，记录当前 56,019 条数据的来源、摘要覆盖与检索边界。
- [早期记录裁剪报告](core_archive_pruning_report.md)：记录 AJS、ASR 和 Social Forces 的年份裁剪规则及结果。
- [非文献条目审计报告](non_article_audit_report.md)：最近一次非文献规则审计及待人工复核范围。
- [数据更新日志](update_log.md)：按时间记录增量更新。

## 当前质量与来源审计

- [数据质量检查报告](data_quality_report.md)：检查当前完整的 `articles.json`，包括规模、期刊范围、缺失、重复 DOI、公开邮箱和既定早期边界。
- [卷期字段补充 dry-run 报告](volume_issue_dry_run_report.md)：评估原始 XLS 可提供的卷期等字段；当前主数据仍不包含卷期字段。

## 历史处理记录

以下文件用于追溯某一批次的决策和中间数字，其中的记录总数不代表当前数据库：

- [早期补档报告](core_archive_backfill_report.md)
- [非文献清理报告](non_article_cleanup_report.md)
- [Crossref 与 OpenAlex 数据源策略建议](source_strategy_crossref_openalex.md)

如报告与当前结构化数据不一致，应先检查报告日期，再以 `articles.json` 和 `api/overview.json` 的同一生成批次为准。
