# 核心期刊早期补档报告

生成时间：2026-06-28 10:55
运行模式：`apply`
处理期刊：Annual Review of Sociology, American Journal of Sociology, American Sociological Review, Social Forces, Demography, Journal of Marriage and Family, Sociology of Education
年份上限：2026

## 总览

- 补档前条目：46,179
- 补档后条目：61,540
- 净增加条目：15,361
- 补档前有摘要：34,388
- 补档后有摘要：36,312
- 摘要净增加：1,924

## 期刊结果

| 期刊 | 原有 | 补档后 | 外部候选 | 新增 | 补摘要 | 新增无摘要 | 重复 | 排除 | 需复核 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Annual Review of Sociology | 631 | 1,178 | 1,345 | 547 | 48 | 200 | 733 | 17 | 0 |
| American Journal of Sociology | 1,103 | 5,267 | 27,029 | 4,164 | 0 | 4,164 | 1,079 | 19,743 | 2,043 |
| American Sociological Review | 1,256 | 5,466 | 13,222 | 4,210 | 35 | 4,091 | 1,416 | 641 | 6,920 |
| Social Forces | 2,019 | 6,276 | 20,993 | 4,257 | 0 | 4,210 | 1,952 | 9,512 | 5,272 |
| Demography | 1,923 | 3,406 | 3,830 | 1,483 | 23 | 231 | 2,021 | 223 | 80 |
| Journal of Marriage and Family | 2,531 | 2,578 | 6,908 | 47 | 0 | 0 | 2,192 | 432 | 4,237 |
| Sociology of Education | 638 | 1,291 | 1,391 | 653 | 0 | 647 | 616 | 100 | 22 |

## 输出文件

- 新增清单：`exports/core_archive_backfill_added.csv`
- 排除清单：`exports/core_archive_backfill_excluded.csv`
- 需复核清单：`exports/core_archive_backfill_review.csv`

## 纳入规则

- 只处理配置中的核心/邻近期刊，按 ISSN 和年份抓取 Crossref `journal-article` 元数据。
- DOI 已存在或标题+期刊+年份已存在时不新增；若本地缺摘要且候选有摘要，则只补摘要。
- 明确的书评、目录、卷信息、编委会、勘误、纪念性条目和出版信息条目不入库。
- 早期论文常无摘要；标题、作者和页码形态不像非论文条目的候选会作为 metadata-only 记录保留。
- 卷期页码只用于本次清洗报告，暂不写入主库 schema。
