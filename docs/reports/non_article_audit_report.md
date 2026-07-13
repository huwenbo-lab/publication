# 非文献条目审计报告

生成时间：2026-07-13 04:41
运行模式：`dry-run`
审计前记录数：46,512
候选条目数：533
高置信度自动删除候选：9
人工复核候选：524
本次计划删除候选：9

## 输出文件

- 候选清单：`exports/non_article_candidates.csv`
- 删除清单：`exports/non_article_removed.csv`（dry-run 无计划删除时保留既有清单）
- 人工复核清单：`exports/non_article_needs_review.csv`
- 本次未修改 `articles.json`。

## 删除原则

- 只自动删除标题完全匹配或高度接近行政性、目录性、编委会、投稿说明、出版信息类的条目。
- `Editorial`、`Introduction`、`Commentary`、`Book Review`、`Correction`、`Erratum` 等边界类型默认不自动删除。
- 若已人工确认边界候选也应删除，可使用 `--apply --include-review`；本次是否包含人工复核候选：否。
- 如果标题像非文献条目但摘要较长且含研究信号，转入人工复核。

## 按期刊变化

| 期刊 | 删除前 | 删除后 | 变化 |
|---|---:|---:|---:|
| 无变化 |  |  |  |

## 按年份变化

| 年份 | 删除前 | 删除后 | 变化 |
|---|---:|---:|---:|
| 无变化 |  |  |  |

## 后续人工复核建议

请优先打开 `exports/non_article_needs_review.csv`，逐条判断边界类型是否保留。不要仅凭标题中包含 `review` 或 `editorial` 就自动删除，因为这些可能是学术评论、专题导论或勘误。
