#!/usr/bin/env python3
"""
Build the agent-facing literature index.

The full archive remains articles.json. This script creates compact routing
files under agent_lit_index/generated/ so agents can search a bounded default
pool first and load full abstracts only for narrowed candidates.
"""
import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from _paths import ROOT

ARTICLES_JSON = ROOT / "articles.json"
AGENT_DIR = ROOT / "agent_lit_index"
POOLS_JSON = AGENT_DIR / "journal_pools.json"
GENERATED_DIR = AGENT_DIR / "generated"
INDEX_DIR = GENERATED_DIR / "index"


def norm_space(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def safe_text(value):
    return norm_space(value).replace("\t", " ")


def year_period(year):
    if not isinstance(year, int):
        return "unknown"
    if year >= 2020:
        return "2020_present"
    if year >= 2010:
        return "2010_2019"
    if year >= 2000:
        return "2000_2009"
    return "pre_2000"


def rough_tokens(text):
    return round(len(text or "") / 4)


def rough_tokens_from_len(char_count):
    return round(char_count / 4)


def load_articles():
    with ARTICLES_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def load_pools():
    with POOLS_JSON.open(encoding="utf-8") as f:
        return json.load(f)


def build_rules(pools):
    journal_rules = {}
    for tier_name, tier in pools["tiers"].items():
        include = tier.get("include_in_default_screening", False)
        for journal in tier.get("journals", []):
            journal_rules[journal] = {
                "tier": tier_name,
                "year_min": tier.get("year_min"),
                "include": include,
                "reason": tier.get("purpose", ""),
            }
        for rule in tier.get("rules", []):
            journal_rules[rule["journal"]] = {
                "tier": tier_name,
                "year_min": rule.get("year_min"),
                "include": include,
                "reason": rule.get("reason", tier.get("purpose", "")),
            }
    return journal_rules


def route_article(article, journal_rules):
    journal = article.get("journal") or ""
    year = article.get("year")
    rule = journal_rules.get(journal)
    if not rule:
        return {
            "tier": "archive_on_demand",
            "include": False,
            "route_note": "Journal is not listed in journal_pools.json.",
        }

    year_min = rule.get("year_min")
    include = bool(rule.get("include"))
    if year_min is not None and (not isinstance(year, int) or year < year_min):
        return {
            "tier": "archive_on_demand",
            "include": False,
            "route_note": f"Below default cutoff for {journal}: {year_min}+.",
        }
    return {
        "tier": rule["tier"],
        "include": include,
        "route_note": rule.get("reason", ""),
    }


def article_key(article, fallback_idx):
    doi = norm_space(article.get("doi")).lower()
    if doi:
        return doi
    title = norm_space(article.get("title")).lower()
    year = article.get("year") or ""
    journal = norm_space(article.get("journal")).lower()
    return f"no-doi:{journal}:{year}:{title[:80]}:{fallback_idx}"


def write_tsv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def build_index(args):
    articles = load_articles()
    pools = load_pools()
    journal_rules = build_rules(pools)
    preview_chars = int(pools.get("abstract_policy", {}).get("preview_chars", 800))

    generated_rows = []
    full_lookup_rows = []
    full_title_rows = []
    default_title_rows = []
    journal_stats = defaultdict(lambda: {
        "records": 0,
        "with_abstract": 0,
        "title_chars": 0,
        "abstract_chars": 0,
        "years": [],
        "default_records": 0,
    })
    shard_stats = defaultdict(lambda: {
        "records": 0,
        "with_abstract": 0,
        "title_chars": 0,
        "abstract_chars": 0,
        "default_records": 0,
    })
    tier_counter = Counter()
    default_counter = Counter()

    for idx, article in enumerate(articles):
        route = route_article(article, journal_rules)
        journal = norm_space(article.get("journal"))
        year = article.get("year")
        title = norm_space(article.get("title"))
        abstract = norm_space(article.get("abstract"))
        key = article_key(article, idx)
        period = year_period(year)
        include = route["include"]
        tier = route["tier"]

        stat = journal_stats[journal]
        stat["records"] += 1
        stat["title_chars"] += len(title)
        stat["abstract_chars"] += len(abstract)
        if abstract:
            stat["with_abstract"] += 1
        if isinstance(year, int):
            stat["years"].append(year)
        if include:
            stat["default_records"] += 1

        shard_key = (tier, journal, period)
        shard = shard_stats[shard_key]
        shard["records"] += 1
        shard["title_chars"] += len(title)
        shard["abstract_chars"] += len(abstract)
        if abstract:
            shard["with_abstract"] += 1
        if include:
            shard["default_records"] += 1

        tier_counter[tier] += 1
        if include:
            default_counter[tier] += 1

        row = {
            "record_id": key,
            "tier": tier,
            "journal": safe_text(journal),
            "year": year if isinstance(year, int) else "",
            "title": safe_text(title),
            "authors": safe_text(article.get("authors")),
            "doi": safe_text(article.get("doi")),
            "abstract_preview": safe_text(abstract[:preview_chars]),
            "has_full_abstract": "yes" if abstract else "no",
            "route_note": safe_text(route["route_note"]),
        }
        title_row = {
            "record_id": key,
            "tier": tier,
            "journal": safe_text(journal),
            "year": year if isinstance(year, int) else "",
            "title": safe_text(title),
            "doi": safe_text(article.get("doi")),
            "has_full_abstract": "yes" if abstract else "no",
        }
        full_lookup_rows.append(row)
        full_title_rows.append(title_row)
        if include:
            generated_rows.append(row)
            default_title_rows.append(title_row)

    write_tsv(
        INDEX_DIR / "default_screening.tsv",
        generated_rows,
        [
            "record_id",
            "tier",
            "journal",
            "year",
            "title",
            "authors",
            "doi",
            "abstract_preview",
            "has_full_abstract",
            "route_note",
        ],
    )
    write_tsv(
        INDEX_DIR / "archive_lookup.tsv",
        full_lookup_rows,
        [
            "record_id",
            "tier",
            "journal",
            "year",
            "title",
            "authors",
            "doi",
            "abstract_preview",
            "has_full_abstract",
            "route_note",
        ],
    )
    write_tsv(
        INDEX_DIR / "full_titles.tsv",
        full_title_rows,
        ["record_id", "tier", "journal", "year", "title", "doi", "has_full_abstract"],
    )
    write_tsv(
        INDEX_DIR / "default_titles.tsv",
        default_title_rows,
        ["record_id", "tier", "journal", "year", "title", "doi", "has_full_abstract"],
    )

    journal_rows = []
    for journal, stat in sorted(journal_stats.items()):
        years = stat["years"]
        journal_rows.append({
            "journal": safe_text(journal),
            "records": stat["records"],
            "default_records": stat["default_records"],
            "with_abstract": stat["with_abstract"],
            "year_min": min(years) if years else "",
            "year_max": max(years) if years else "",
            "rough_title_abstract_tokens": rough_tokens_from_len(stat["title_chars"] + stat["abstract_chars"]),
        })
    write_tsv(
        GENERATED_DIR / "journal_summary.tsv",
        journal_rows,
        [
            "journal",
            "records",
            "default_records",
            "with_abstract",
            "year_min",
            "year_max",
            "rough_title_abstract_tokens",
        ],
    )

    shard_rows = []
    for (tier, journal, period), stat in sorted(shard_stats.items()):
        shard_rows.append({
            "tier": tier,
            "journal": safe_text(journal),
            "period": period,
            "records": stat["records"],
            "default_records": stat["default_records"],
            "with_abstract": stat["with_abstract"],
            "rough_title_abstract_tokens": rough_tokens_from_len(stat["title_chars"] + stat["abstract_chars"]),
        })
    write_tsv(
        GENERATED_DIR / "shard_manifest.tsv",
        shard_rows,
        [
            "tier",
            "journal",
            "period",
            "records",
            "default_records",
            "with_abstract",
            "rough_title_abstract_tokens",
        ],
    )

    pool_rows = []
    for tier in sorted(tier_counter):
        tier_articles = [row for row in full_lookup_rows if row["tier"] == tier]
        default_articles = [row for row in generated_rows if row["tier"] == tier]
        pool_rows.append({
            "tier": tier,
            "archive_records": len(tier_articles),
            "default_screening_records": len(default_articles),
        })
    write_tsv(
        GENERATED_DIR / "pool_summary.tsv",
        pool_rows,
        ["tier", "archive_records", "default_screening_records"],
    )

    default_chars = sum(len(row["title"]) + len(row["abstract_preview"]) for row in generated_rows)
    archive_chars = sum(
        len(norm_space(article.get("title"))) + len(norm_space(article.get("abstract")))
        for article in articles
    )
    overview = [
        "# Agent literature index overview",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"- Full archive records: **{len(articles):,}**",
        f"- Default screening records: **{len(generated_rows):,}**",
        f"- Full archive rough title+abstract tokens: **{round(archive_chars / 4):,}**",
        f"- Default screening rough title+preview tokens: **{round(default_chars / 4):,}**",
        f"- Abstract preview length: **{preview_chars} characters**",
        "",
        "## Tier Counts",
        "",
        "| Tier | Archive records | Default screening records |",
        "|---|---:|---:|",
    ]
    for row in pool_rows:
        overview.append(
            f"| {row['tier']} | {int(row['archive_records']):,} | {int(row['default_screening_records']):,} |"
        )
    overview.extend([
        "",
        "## Default Use",
        "",
        "Search `generated/index/default_screening.tsv` first. Use",
        "`generated/index/full_titles.tsv` for broad title-first searches and",
        "`generated/index/archive_lookup.tsv` for abstract-rescue or targeted",
        "archive follow-up.",
        "",
        "Do not read either TSV wholesale into an agent context. Use `rg`, SQLite,",
        "or another filter first, then load a small candidate set.",
        "",
    ])
    (GENERATED_DIR / "overview.md").write_text("\n".join(overview), encoding="utf-8")

    print(f"Full archive records: {len(articles):,}")
    print(f"Default screening records: {len(generated_rows):,}")
    print(f"Wrote {GENERATED_DIR}")


def extract_dois(args):
    articles = load_articles()
    dois = {
        norm_space(line).lower()
        for line in Path(args.extract_dois).read_text(encoding="utf-8").splitlines()
        if norm_space(line)
    }
    matches = [
        article for article in articles
        if norm_space(article.get("doi")).lower() in dois
    ]
    print(json.dumps(matches, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--extract-dois",
        help="Print full JSON records for DOI values listed one per line.",
    )
    args = parser.parse_args()
    if args.extract_dois:
        extract_dois(args)
    else:
        build_index(args)


if __name__ == "__main__":
    main()
