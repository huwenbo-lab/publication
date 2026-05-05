# API 导出

本目录为静态 JSON 端点，供 AI 工具或外部脚本直接读取。

## 结构

```
api/
├── dashboard.json
├── overview.json
├── journals.json
├── browse.json
├── authors.json
├── browse/
│   └── by_journal_year/
└── articles/
    └── 10.1086/
        └── 714825.json
```

## DOI 到路径的规则

- DOI 会按 `/` 拆成路径层级
- 最后一段加上 `.json` 后缀
- 例如 `10.1086/714825` → `api/articles/10.1086/714825.json`

## 浏览与作者索引

- `browse.json`：期刊和年份计数总览。
- `browse/by_journal_year/*.json`：某本期刊下各年份文章列表。
- `authors.json`：保守规范化后的作者索引，供 Top Scholars 和作者检索使用。

当前已生成 **32,410** 个单篇 JSON 端点。
