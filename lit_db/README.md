# lit_db — AI可查阅的文献库

本目录为社会学文献数据库的轻量级索引，专为AI检索设计。
完整数据见 `../articles.json`（34k条，32MB）。

## 查阅流程

```
1. 读 overview.md          → 了解数据库全貌
2. 读 titles/by_journal/   → 某期刊全部标题，快速初筛
3. 读 abstracts/[年份段]/  → 看初筛结果对应的摘要
```

## 目录结构

```
lit_db/
├── overview.md                    # 数据库概况、期刊列表、使用说明
├── titles/
│   ├── all_titles.tsv             # 全量34k标题，可grep搜索（~5MB）
│   └── by_journal/                # 按期刊：每个文件含该刊所有标题
│       ├── Sociology.md
│       └── ...
└── abstracts/
    ├── 2020_2026/                 # 近6年，每期刊一个文件，含摘要片段
    │   ├── Sociology.md
    │   └── ...
    ├── 2010_2019/
    └── 2000_2009/
```

## 摘要说明

摘要截断至前 300 字符（约2–3句话），保留核心信息。
完整摘要可通过 DOI 在 CrossRef 查询：`https://api.crossref.org/works/[DOI]`

## 重新生成

```bash
source venv/bin/activate
python build_lit_db.py
```