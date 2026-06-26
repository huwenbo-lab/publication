# Agent literature index overview

Generated at: 2026-06-27T07:24:27

- Full archive records: **44,614**
- Default screening records: **29,676**
- Full archive rough title+abstract tokens: **10,610,003**
- Default screening rough title+preview tokens: **5,717,650**
- Abstract preview length: **800 characters**

## Tier Counts

| Tier | Archive records | Default screening records |
|---|---:|---:|
| adjacent_recent | 6,610 | 6,610 |
| archive_on_demand | 14,938 | 0 |
| core_default | 22,532 | 22,532 |
| review_anchor | 534 | 534 |

## Default Use

Search `generated/index/default_screening.tsv` first. Use
`generated/index/full_titles.tsv` for broad title-first searches and
`generated/index/archive_lookup.tsv` for abstract-rescue or targeted
archive follow-up.

Do not read either TSV wholesale into an agent context. Use `rg`, SQLite,
or another filter first, then load a small candidate set.
