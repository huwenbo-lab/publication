# data 目录说明

本目录用于记录数据层的组织约定。为保持 GitHub Pages 和现有脚本兼容，当前运行时数据文件仍保留在仓库根目录和既有目录：

- `articles.json`：主数据，标准字段为 `title`、`abstract`、`authors`、`journal`、`year`、`doi`。
- `data.json`、`data.js`：旧字段名兼容文件，供前端 fallback 使用。
- `raw_data/`：Web of Science 原始 XLS 导出，作为归档源文件保留。
- `api/`：静态 JSON API，由 `scripts/build_article_api.py` 生成。
- `lit_db/`：供 AI agent 读取的轻量级 Markdown/TSV 索引。
- `literature.db`：本地生成的 SQLite FTS5 搜索库，不提交 Git，可从 `articles.json` 重建。

后续如果要把运行时数据整体迁入 `data/`，必须同步修改前端路径、脚本常量、GitHub Actions 和 GitHub Pages 部署流程。当前不做大规模搬迁，以避免破坏静态站点。
