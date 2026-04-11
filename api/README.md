# API 导出

本目录为静态 JSON 端点，供 AI 工具或外部脚本直接读取。

## 结构

```
api/
├── overview.json
├── journals.json
└── articles/
    └── 10.1086/
        └── 714825.json
```

## DOI 到路径的规则

- DOI 会按 `/` 拆成路径层级
- 最后一段加上 `.json` 后缀
- 例如 `10.1086/714825` → `api/articles/10.1086/714825.json`

当前已生成 **34,146** 个单篇 JSON 端点。
