# Agent literature index overview

Generated at: 2026-06-27T07:36:17

- Full archive records: **46,179**
- Default screening records: **31,016**
- Full archive rough title+abstract tokens: **10,767,374**
- Default screening rough title+preview tokens: **5,821,614**
- Abstract preview length: **800 characters**

## Tier Counts

| Tier | Archive records | Default screening records |
|---|---:|---:|
| adjacent_recent | 6,653 | 6,653 |
| archive_on_demand | 15,163 | 0 |
| core_default | 23,732 | 23,732 |
| review_anchor | 631 | 631 |

## Default Use

Search `generated/index/default_screening.tsv` first. Use
`generated/index/full_titles.tsv` for broad title-first searches and
`generated/index/archive_lookup.tsv` for abstract-rescue or targeted
archive follow-up.

Do not read either TSV wholesale into an agent context. Use `rg`, SQLite,
or another filter first, then load a small candidate set.
