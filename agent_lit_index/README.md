# Agent literature index

This directory is the agent-facing entry layer for the local sociology and
demography literature database.

It does not replace `articles.json`. The full database remains the archival
source of truth. This layer tells agents which part of the archive to search
first, which journals are adjacent or noisy, and when to escalate to wider
search.

## Read order for agents

1. Read this file.
2. Read `AGENT_PROTOCOL.md`.
3. Read `journal_pools.json`.
4. Use files under `generated/`:
   - `overview.md` for current size and pool counts.
   - `pool_summary.tsv` for compact pool-level statistics.
   - `journal_summary.tsv` for per-journal size and token burden.
   - `shard_manifest.tsv` to decide which journal/year shard to inspect.
   - `index/default_screening.tsv` for default title + abstract-preview search.
   - `index/full_titles.tsv` for broad title-first search across all records.

## Operating principle

Default search is bounded-core-first:

- Start from the custom core journal pool.
- Use broad title search to rank likely candidates, then use abstract-rescue
  search to recover mechanism papers with indirect titles.
- Use adjacent journals only when the mechanism, method, or reviewer risk calls
  for them.
- Use archive-only material or web/open search only after the bounded local pool
  cannot answer the literature question.

Do not claim that the whole academic literature has been searched unless an
explicit open search was run.

## Full-text boundary

Most local records are title-and-abstract metadata. They are good for locating
candidate literature, classifying possible roles, and building read queues.
They are not enough to make firm claims about models, robustness checks, or
full theoretical arguments.
