# Agent literature index overview

Generated at: 2026-07-30T11:35:44

- Full archive records: **56,019**
- Default screening records: **40,856**
- Full archive rough title+abstract tokens: **12,816,712**
- Default screening rough title+preview tokens: **7,441,643**
- Abstract preview length: **800 characters**

## Tier Counts

| Tier | Archive records | Default screening records |
|---|---:|---:|
| adjacent_recent | 6,653 | 6,653 |
| archive_on_demand | 15,163 | 0 |
| core_default | 33,025 | 33,025 |
| review_anchor | 1,178 | 1,178 |

## Default Use

Search `generated/index/default_screening.tsv` first. Use
`generated/index/full_titles.tsv` for broad title-first searches and
`generated/index/archive_lookup.tsv` for abstract-rescue or targeted
archive follow-up.

Do not read either TSV wholesale into an agent context. Use `rg`, SQLite,
or another filter first, then load a small candidate set.
