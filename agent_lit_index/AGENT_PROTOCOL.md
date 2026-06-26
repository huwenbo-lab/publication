# Agent protocol for local literature search

## Goal

Use the local journal database as a stable, bounded first-pass literature map.
The purpose is to identify conversations, theory anchors, empirical precedents,
institutional background, and competing explanations for a concrete research
project.

## Database hygiene assumptions

The full archive is a cleaned metadata archive, not a raw publisher dump.
Maintenance scripts remove obvious non-article records before index generation:

- book reviews, including citation-style book review records with page counts,
  prices, ISBNs, or hardback/paperback metadata;
- editorial-board pages, front/back matter, tables of contents, author/subject
  indexes, contributor/reviewer lists, calls, announcements, and prefaces;
- errata, corrigenda, retractions, duplicate-publication notices, obituaries,
  memorial notes, and special-issue/editorial introductions;
- exact duplicate records by journal + year + normalized title, keeping the
  metadata-complete record.

The archive may still contain older research articles where Crossref exposes
historical records. Use `journal_pools.json` to decide what enters the default
screening layer; do not treat the full archive as the default reading set.

## Default workflow

1. Clarify the project question and empirical finding before searching.
2. Run a broad title search first. Titles are used for prioritization, not final
   exclusion. A typical broad title pass should keep roughly 500-1,500
   candidates when the topic is large enough.
3. Run an abstract-rescue search over `generated/index/archive_lookup.tsv`.
   This recovers records whose titles are abstract or indirect but whose
   abstract contains the mechanism, sample, variable, or context.
4. Merge title hits and abstract-rescue hits, then inspect title, journal,
   year, DOI, and abstract preview.
5. Load full abstracts from `articles.json` only for a narrowed candidate set.
   Read them in batches of roughly 100-200 records; do not load all candidates
   into one context.
6. Classify candidates using:
   - `core_conversation`
   - `theoretical_anchor`
   - `empirical_precedent`
   - `institutional_background`
   - `competing_explanation`
   - `uncertain`
7. Keep `high` and `uncertain` records through the first abstract pass. Do not
   discard an abstract but plausible mechanism paper just because the title is
   broad.
8. Produce a small read queue before requesting PDFs or full-text acquisition.

## Search escalation

Use this order unless the user explicitly asks otherwise:

1. `core_default`: journals most likely to define the paper's home conversation.
2. `review_anchor`: review journals used for conceptual maps and canonical
   references.
3. `adjacent_recent`: adjacent journals, usually recent records only.
4. `archive_on_demand`: older or broad material, only when needed.
5. Open web / Google Scholar / Crossref / OpenAlex search, only for a specific
   gap or strong novelty claim.

## Practical commands

Search the default agent index:

```bash
rg -i "housework|childcare|gender norm|breadwinner" agent_lit_index/generated/index/default_screening.tsv
```

Broad title-first search across the full archive:

```bash
rg -i "housework|childcare|breadwinner|gender ideology" agent_lit_index/generated/index/full_titles.tsv
```

Abstract-rescue search across the full archive preview layer:

```bash
rg -i "division of household labor|relative earnings|gender deviance|fairness" agent_lit_index/generated/index/archive_lookup.tsv
```

Find which shards are likely worth reading:

```bash
rg -i "Gender & Society|Journal of Marriage and Family|Social Psychology Quarterly" agent_lit_index/generated/shard_manifest.tsv
```

Load full records for a small DOI list:

```bash
python3 scripts/build_agent_lit_index.py --extract-dois doi_list.txt
```

## Claim discipline

Use cautious wording when only title and abstract are available:

- "The abstract suggests..."
- "This appears relevant to..."
- "This is a candidate for..."
- "Full text should be checked before using it as a core claim."

Do not write:

- "The article proves..."
- "The authors show through robustness checks..."
- "The paper establishes..."

unless the full text or user notes were read.

## Stop rules

Stop expanding search when:

- A coherent 10-20 item candidate core set exists.
- Main theoretical anchors are identified.
- Main empirical precedents and competing explanations are represented.
- Remaining gaps are specific enough to become targeted follow-up searches.
