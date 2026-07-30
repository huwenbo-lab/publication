# 项目 Agent 说明

默认用中文解释。先读根目录 `README.md`；用户当前指令和实时文件优先于历史报告。

## 当前事实

- 权威主库：`articles.json`
- 2026-07-30 发布快照：56,019 条、31 本收录期刊、1947–2026 年
- 有摘要：43,276 条；无摘要：12,743 条
- 有 DOI / 单篇静态端点：55,946 条
- `data.json` 是网页兼容数据，必须与主库逐条一致
- 本库是元数据和摘要索引，不含论文 PDF 或正文

## 不得破坏的收录边界

早期文献裁剪是已确认口径，不是误删：

- American Journal of Sociology：1950+
- American Sociological Review：1960+
- Social Forces：1950+

不要自动补回这三个起点之前的记录。历史链条和原因见 `README.md` 与 `docs/reports/`。

## 文件角色

- `articles.json`：唯一权威发布快照
- `data.json`：由主库生成的网页兼容数据
- `lit_db/`、`agent_lit_index/generated/`：公开、可重建的 Agent 索引
- `api/`、`literature.db`：部署时生成，不跟踪
- `raw_data/*.xls`：本地受限来源文件，不公开、不跟踪
- `.cache/`、`backups/`、`exports/`、`tmp/`、`outputs/`、`venv/`：本地状态，不进入 release

不要把 17 份 XLS 当作可精确重建当前 31 刊主库的充分来源。

## 修改原则

- 优先小而可复核的差异；大规模数据变更必须先 dry-run。
- 不虚构字段、来源、卷期、许可或 API 行为。
- 数据变更后同步重建 `data.json`、`lit_db/`、`agent_lit_index/generated/`、`literature.db` 和部署 API。
- 边界条目默认进入人工复核，不因标题含 Editorial、Review、Reply 等词就直接删除。
- 不提交密钥、私人邮箱、本机绝对路径、Web of Science XLS 或摘要中的联系邮箱。
- OpenAlex 密钥只通过环境变量 `OPENALEX_API_KEY` 提供；可选 API 联系邮箱通过 `LITDB_CONTACT_EMAIL` 提供。
- 代码、文档、数据的项目级许可证尚未选定，不要代替维护者新增开放许可。

## 最小验证

```bash
python -m py_compile scripts/*.py
python scripts/check_quality.py
python scripts/build_lit_db.py
python scripts/build_agent_lit_index.py
python scripts/build_search_db.py --rebuild
python scripts/build_article_api.py
python scripts/check_release.py --with-generated
```

前端变更还需运行：

```bash
python scripts/check_frontend_ui.py
```

自动更新和部署流程见 `docs/workflows/maintenance_workflows.md`。
