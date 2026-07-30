# raw_data（本地来源文件）

`raw_data/*.xls` 是本地维护者从 Web of Science 导出的来源文件，不随公开仓库分发。导出表可能包含通讯邮箱、机构地址、ResearcherID、ORCID 和资助信息，请不要打包上传或作为 release asset 发布。

公开仓库中的 `articles.json` 是当前发布快照和派生索引的权威输入。17 份历史 XLS 只覆盖部分期刊，不能单独精确重建当前 31 刊、56,019 条记录。

维护者若依法取得相应文件，可将它们放回本目录，并运行：

```bash
python scripts/build_articles.py
python scripts/audit_volume_issue.py --dry-run
```

文件名需与 `scripts/build_articles.py` 中的映射一致。提交前请运行 `python scripts/check_release.py`，确认 XLS 没有被 Git 跟踪。
