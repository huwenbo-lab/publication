"""
build_article_api.py — 生成面向 AI / 外部工具的静态 JSON 端点

输出结构：
  api/
  ├── overview.json
  ├── journals.json
  ├── README.md
  └── articles/
      └── 10.1086/
          └── 714825.json

说明：
  - DOI 会按 `/` 拆成路径层级，因此文章 JSON URL 形如：
    /api/articles/10.1086/714825.json
  - 仅为有 DOI 的文章生成单篇端点。
"""

import argparse
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
API_DIR = ROOT / "api"
ARTICLES_DIR = API_DIR / "articles"
ARTICLES_JSON = ROOT / "articles.json"

SITE_BASE = "https://huwenbo-lab.github.io/publication"
RAW_BASE = "https://raw.githubusercontent.com/huwenbo-lab/publication/main"
STOPWORDS = {
    "about", "after", "against", "among", "amongst", "analysis", "and", "are", "article",
    "articles", "between",
    "beyond", "but", "can", "change", "changes", "children", "class", "evidence", "for",
    "from", "into", "its", "more", "new", "not", "over", "paper", "perspective",
    "perspectives", "research", "review", "role", "social", "society", "study", "studies",
    "their", "the", "these", "this", "those", "through", "toward", "towards", "under",
    "using", "when", "where", "which", "with", "within", "without", "book", "books",
    "editorial", "introduction",
}


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", str(text))
    return re.sub(r"\s+", " ", text).strip()


def safe_filename(journal_name):
    name = journal_name.replace("&", "and").replace(",", "")
    name = re.sub(r"[^\w\s-]", "", name)
    return re.sub(r"\s+", "_", name.strip())


def parse_authors(authors_text):
    authors = []
    for item in str(authors_text or "").split(";"):
        raw = item.strip()
        if not raw:
            continue
        parts = [part.strip() for part in raw.split(",", 1)]
        family = parts[0] if parts else ""
        given = parts[1] if len(parts) > 1 else ""
        authors.append({
            "raw": raw,
            "family": family,
            "given": given,
        })
    return authors


def normalize_doi(doi):
    clean = str(doi or "").strip()
    clean = re.sub(r"^https?://doi\.org/", "", clean, flags=re.I)
    return clean.lower()


def doi_to_segments(doi):
    clean = normalize_doi(doi)
    if not clean:
        return []
    return [quote(segment, safe="._-~") for segment in clean.split("/") if segment]


def doi_to_relative_path(doi):
    segments = doi_to_segments(doi)
    if not segments:
        return None
    parent = Path("articles").joinpath(*segments[:-1]) if len(segments) > 1 else Path("articles")
    return parent / f"{segments[-1]}.json"


def build_site_url(relative_path):
    return f"{SITE_BASE}/{relative_path.as_posix()}"


def period_key(year):
    if not year:
        return ""
    if 2020 <= year <= 2026:
        return "2020_2026"
    if 2010 <= year <= 2019:
        return "2010_2019"
    if 2000 <= year <= 2009:
        return "2000_2009"
    return ""


def build_lit_db_urls(article):
    journal_slug = safe_filename(article["journal"])
    period = period_key(article.get("year"))
    urls = {
        "overview": f"{RAW_BASE}/lit_db/overview.md",
        "journal_titles": f"{RAW_BASE}/lit_db/titles/by_journal/{journal_slug}.md",
        "journal_abstracts": f"{RAW_BASE}/lit_db/abstracts/{period}/{journal_slug}.md" if period else "",
    }
    return urls


def load_articles():
    return json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))


def summarize_articles(articles):
    years = [article.get("year") for article in articles if article.get("year")]
    journals = [clean_text(article.get("journal")) for article in articles if clean_text(article.get("journal"))]
    with_abstract = sum(1 for article in articles if clean_text(article.get("abstract")))
    doi_records = sum(1 for article in articles if normalize_doi(article.get("doi")))
    unique_doi_count = len({
        normalize_doi(article.get("doi"))
        for article in articles
        if normalize_doi(article.get("doi"))
    })
    total = len(articles)
    return {
        "total_articles": total,
        "total_journals": len(set(journals)),
        "year_min": min(years) if years else None,
        "year_max": max(years) if years else None,
        "articles_with_abstract": with_abstract,
        "articles_missing_abstract": total - with_abstract,
        "abstract_coverage_rate": round(with_abstract / total, 4) if total else 0,
        "records_with_doi": doi_records,
        "doi_coverage_rate": round(doi_records / total, 4) if total else 0,
        "unique_article_json": unique_doi_count,
    }


def tokenize_title(title):
    return [
        token for token in re.findall(r"[A-Za-z][A-Za-z'-]{2,}", clean_text(title).lower())
        if token not in STOPWORDS and len(token) >= 4
    ]


def build_article_payload(article):
    clean_article = {
        "title": clean_text(article.get("title")),
        "abstract": clean_text(article.get("abstract")),
        "authors_text": clean_text(article.get("authors")),
        "journal": clean_text(article.get("journal")),
        "year": article.get("year"),
        "doi": normalize_doi(article.get("doi")),
    }
    api_path = doi_to_relative_path(clean_article["doi"])
    lit_db_urls = build_lit_db_urls(clean_article)
    payload = {
        "title": clean_article["title"],
        "abstract": clean_article["abstract"],
        "authors": parse_authors(clean_article["authors_text"]),
        "authors_text": clean_article["authors_text"],
        "journal": clean_article["journal"],
        "journal_slug": safe_filename(clean_article["journal"]),
        "year": clean_article["year"],
        "doi": clean_article["doi"],
        "doi_url": f"https://doi.org/{clean_article['doi']}" if clean_article["doi"] else "",
        "share_url": f"{SITE_BASE}/#doi/{quote(clean_article['doi'], safe='')}" if clean_article["doi"] else "",
        "api_url": build_site_url(Path("api") / api_path) if api_path else "",
        "lit_db": lit_db_urls,
    }
    return api_path, payload


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_overview(articles):
    summary = summarize_articles(articles)
    journals = sorted({article.get("journal", "") for article in articles if article.get("journal")})
    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "site_base": SITE_BASE,
        "raw_base": RAW_BASE,
        "total_articles": summary["total_articles"],
        "articles_with_doi": summary["unique_article_json"],
        "total_journals": len(journals),
        "year_range": {
            "min": summary["year_min"],
            "max": summary["year_max"],
        },
        "summary": summary,
        "resources": {
            "articles_json": f"{RAW_BASE}/articles.json",
            "lit_db_overview": f"{RAW_BASE}/lit_db/overview.md",
            "journals_index": build_site_url(Path("api") / "journals.json"),
            "dashboard": build_site_url(Path("api") / "dashboard.json"),
        },
    }
    write_json(API_DIR / "overview.json", payload)


def build_journals_index(articles):
    counter = defaultdict(list)
    for article in articles:
        journal = clean_text(article.get("journal"))
        if journal:
            counter[journal].append(article)

    items = []
    for journal in sorted(counter):
        journal_articles = counter[journal]
        years = [article.get("year") for article in journal_articles if article.get("year")]
        items.append({
            "journal": journal,
            "slug": safe_filename(journal),
            "count": len(journal_articles),
            "year_min": min(years) if years else None,
            "year_max": max(years) if years else None,
            "titles_url": f"{RAW_BASE}/lit_db/titles/by_journal/{safe_filename(journal)}.md",
        })

    write_json(API_DIR / "journals.json", {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "journals": items,
    })


def build_dashboard(articles):
    summary = summarize_articles(articles)
    year_counter = Counter()
    keyword_counter = Counter()
    author_counter = Counter()
    journal_counter = Counter()
    journal_abstract_counter = defaultdict(lambda: {"total": 0, "with_abstract": 0})

    for article in articles:
        year = article.get("year")
        journal = clean_text(article.get("journal"))
        abstract = clean_text(article.get("abstract"))
        if year:
            year_counter[int(year)] += 1
        if journal:
            journal_counter[journal] += 1
            journal_abstract_counter[journal]["total"] += 1
            if abstract:
                journal_abstract_counter[journal]["with_abstract"] += 1
        keyword_counter.update(tokenize_title(article.get("title")))
        for author in parse_authors(article.get("authors")):
            if author["raw"] and not author["raw"].startswith("["):
                author_counter[author["raw"]] += 1

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "summary": summary,
        "year_counts": [
            {"year": year, "count": count}
            for year, count in sorted(year_counter.items())
        ],
        "top_keywords": [
            {"term": term, "count": count}
            for term, count in keyword_counter.most_common(18)
        ],
        "top_authors": [
            {"author": author, "count": count}
            for author, count in author_counter.most_common(12)
        ],
        "top_journals": [
            {"journal": journal, "count": count}
            for journal, count in journal_counter.most_common(10)
        ],
        "abstract_coverage_by_journal": [
            {
                "journal": journal,
                "count": stat["total"],
                "with_abstract": stat["with_abstract"],
                "coverage_rate": round(stat["with_abstract"] / stat["total"], 4) if stat["total"] else 0,
            }
            for journal, stat in sorted(
                journal_abstract_counter.items(),
                key=lambda item: (-item[1]["total"], item[0].lower())
            )
        ],
    }
    write_json(API_DIR / "dashboard.json", payload)


def build_readme(total_written):
    lines = [
        "# API 导出",
        "",
        "本目录为静态 JSON 端点，供 AI 工具或外部脚本直接读取。",
        "",
        "## 结构",
        "",
        "```",
        "api/",
        "├── dashboard.json",
        "├── overview.json",
        "├── journals.json",
        "└── articles/",
        "    └── 10.1086/",
        "        └── 714825.json",
        "```",
        "",
        "## DOI 到路径的规则",
        "",
        "- DOI 会按 `/` 拆成路径层级",
        "- 最后一段加上 `.json` 后缀",
        "- 例如 `10.1086/714825` → `api/articles/10.1086/714825.json`",
        "",
        f"当前已生成 **{total_written:,}** 个单篇 JSON 端点。",
        "",
    ]
    (API_DIR / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="生成静态文章 API")
    parser.add_argument("--limit", type=int, default=0, help="仅生成前 N 篇（用于测试）")
    parser.add_argument("--keep-existing", action="store_true", help="保留已有文章 JSON，不先清空 api/articles/")
    args = parser.parse_args()

    articles = load_articles()
    if args.limit > 0:
        articles = articles[:args.limit]

    API_DIR.mkdir(exist_ok=True)
    if ARTICLES_DIR.exists() and not args.keep_existing:
        shutil.rmtree(ARTICLES_DIR)

    build_overview(articles)
    build_journals_index(articles)
    build_dashboard(articles)

    unique_payloads = {}
    for article in articles:
        doi = normalize_doi(article.get("doi"))
        if not doi:
            continue
        relative_path, payload = build_article_payload(article)
        unique_payloads[relative_path.as_posix()] = (relative_path, payload)

    total_written = 0
    for relative_path, payload in unique_payloads.values():
        write_json(API_DIR / relative_path, payload)
        total_written += 1

    build_readme(total_written)
    print(f"✓ API 已生成：{total_written:,} 个单篇 JSON 端点")


if __name__ == "__main__":
    main()
