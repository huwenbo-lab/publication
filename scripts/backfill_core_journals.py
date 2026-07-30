"""
backfill_core_journals.py — 补齐核心期刊早期论文元数据

目标：对老牌核心期刊按 ISSN + 年份从 Crossref 批量抓取元数据，补充
`articles.json` 中明显缺失的早期论文。脚本优先保证可复现和可审计：

1. 先抓取外部候选；
2. 过滤明显非论文条目（书评、目录、卷信息、编委会、勘误等）；
3. 用 DOI 或 标题+期刊+年份 去重；
4. 只把通过规则的候选写入主库；
5. 把被排除和需复核候选导出到 `exports/`，并生成报告。

默认只做 dry-run。使用 `--apply` 才会写入。
"""

import argparse
import csv
import json
import re
import shutil
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from _paths import API_USER_AGENT, CACHE_DIR, REPORTS_DIR, ROOT, with_contact
from clean_data import clean_abstract, clean_title, should_delete

ARTICLES_JSON = ROOT / "articles.json"
DATA_JSON = ROOT / "data.json"
BACKUPS_DIR = ROOT / "backups"
EXPORTS_DIR = ROOT / "exports"
CACHE_BACKFILL_DIR = CACHE_DIR / "core_backfill"
REPORT_PATH = REPORTS_DIR / "core_archive_backfill_report.md"
REVIEW_CSV = EXPORTS_DIR / "core_archive_backfill_review.csv"
EXCLUDED_CSV = EXPORTS_DIR / "core_archive_backfill_excluded.csv"
ADDED_CSV = EXPORTS_DIR / "core_archive_backfill_added.csv"

CROSSREF_BASE = "https://api.crossref.org/works"
SLEEP_SEC = 0.35
PAGE_SIZE = 1000

CORE_JOURNALS = {
    "Annual Review of Sociology": {
        "issn": "0360-0572",
        "start_year": 1975,
        "pool": "core",
    },
    "American Journal of Sociology": {
        "issn": "0002-9602",
        "start_year": 1895,
        "pool": "core",
    },
    "American Sociological Review": {
        "issn": "0003-1224",
        "start_year": 1936,
        "pool": "core",
    },
    "Social Forces": {
        "issn": "0037-7732",
        "start_year": 1922,
        "pool": "core",
    },
    "Demography": {
        "issn": "0070-3370",
        "start_year": 1964,
        "pool": "core",
    },
    "Journal of Marriage and Family": {
        "issn": "0022-2445",
        "start_year": 1964,
        "pool": "adjacent",
    },
    "Sociology of Education": {
        "issn": "0038-0407",
        "start_year": 1963,
        "pool": "adjacent",
    },
}

BOOK_REVIEW_PATTERNS = [
    re.compile(r"^<i>.+?</i>", re.I),
    re.compile(r"\bby\s+[A-Z][A-Za-z][^,]*,\s*(?:edited\s+by\s+)?[A-Z]", re.I),
    re.compile(r"\s[-‐‑‒–—]\s*(?:edited\s+)?by\s+[A-Z]", re.I),
    re.compile(r"\bby\s+[A-Z][A-Za-z].*\b(?:press|company|publishers?|university|macmillan|routledge|sage|wiley|norton|dutton|harper|prentice|palgrave)\b", re.I),
    re.compile(r"(?<=[a-z)])\.\s+(?:[A-Z]\.\s*){0,3}[A-Z][A-Za-z'’-]+(?:\s+(?:[A-Z]\.\s*)?[A-Z][A-Za-z'’-]+){0,3}$"),
    re.compile(r"(?<=[a-z)])\.\s+[A-Z][A-Za-z'’.:-]+(?:\s+[A-Z][A-Za-z'’.:-]+)*(?:\s*,\s*[A-Z][A-Za-z'’.:-]+(?:\s+[A-Z][A-Za-z'’.:-]+)*){1,8}$"),
    re.compile(r"\b(?:isbn|hardback|paperback|clothbound|cloth|net\s+\$|price\s+\$)\b", re.I),
    re.compile(r"\b\d+\s*(?:pp|pages)\b", re.I),
    re.compile(r"\bpp\.\s*[xivxlc\d+]+\b", re.I),
    re.compile(r"^[A-Z0-9 ,;:'\"().-]{12,}\.\s+By\s+", re.I),
]

ADMIN_PATTERNS = [
    re.compile(r"^volume information$", re.I),
    re.compile(r"^front matter$", re.I),
    re.compile(r"^back matter$", re.I),
    re.compile(r"^table of contents$", re.I),
    re.compile(r"^contents$", re.I),
    re.compile(r"^index(?: to volume)?$", re.I),
    re.compile(r"^editorial board", re.I),
    re.compile(r"^editor'?s comment$", re.I),
    re.compile(r"^editor'?s note$", re.I),
    re.compile(r"^editors?' introduction$", re.I),
    re.compile(r"^from the editors?", re.I),
    re.compile(r"^message from (?:the )?(?:incoming |outgoing )?editors?$", re.I),
    re.compile(r"^books received$", re.I),
    re.compile(r"^ASR\s+\d{4}\s+to\s+\d{4}$", re.I),
    re.compile(r"^introduction$", re.I),
    re.compile(r"^introduction to (?:a |the )?special issue", re.I),
]

REVIEW_LIKE_PATTERNS = [
    re.compile(r"^book reviews?$", re.I),
    re.compile(r"^new books\b", re.I),
    re.compile(r"\bnew books\b", re.I),
    re.compile(r"^recent books\b", re.I),
    re.compile(r"^book notes?\b", re.I),
    re.compile(r"\bbook review\b", re.I),
    re.compile(r"^review of\b", re.I),
    re.compile(r"\breview essay\b", re.I),
    re.compile(r"^review symposium\b", re.I),
    re.compile(r"\breply to\b", re.I),
    re.compile(r"\bresponse to\b", re.I),
    re.compile(r"\ba reply\b", re.I),
    re.compile(r"\bcomments? on\b", re.I),
    re.compile(r"^comment(?:ary)?\b", re.I),
    re.compile(r"^erratum\b", re.I),
    re.compile(r"^correction\b", re.I),
    re.compile(r"^retraction\b", re.I),
    re.compile(r"^obituary\b", re.I),
    re.compile(r"\bin memoriam\b", re.I),
]

SINGLE_PAGE_REVIEW_RISK_JOURNALS = {
    "American Journal of Sociology",
    "American Sociological Review",
    "Demography",
    "Journal of Marriage and Family",
    "Social Forces",
    "Sociology of Education",
}

STRICT_SINGLE_PAGE_METADATA_JOURNALS = {
    "Journal of Marriage and Family",
}

TITLE_KEY_DROP = re.compile(r"[^a-z0-9]+", re.I)


def safe_slug(value):
    text = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip())
    return text.strip("_")


def clean_text(value):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def normalize_doi(value):
    doi = str(value or "").strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.I)
    return doi.lower()


def normalize_title_key(title):
    title = clean_title(title or "").lower()
    title = title.replace("&", "and")
    title = TITLE_KEY_DROP.sub(" ", title)
    return re.sub(r"\s+", " ", title).strip()


def title_year_key(article):
    return (
        clean_text(article.get("journal")).lower(),
        article.get("year"),
        normalize_title_key(article.get("title")),
    )


def get_json(url, retries=4, timeout=45):
    headers = {
        "User-Agent": API_USER_AGENT,
        "Accept": "application/json",
    }
    for attempt in range(retries):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 429:
                wait = 5 * (attempt + 1)
                print(f"    [限速] 等待 {wait}s 后重试")
                time.sleep(wait)
                continue
            print(f"    [HTTP {exc.code}] {url[:120]}")
        except (TimeoutError, URLError, Exception) as exc:
            print(f"    [请求失败] {exc}")
        if attempt < retries - 1:
            time.sleep(2 * (attempt + 1))
    return None


def parse_year(item):
    for key in ("published", "published-print", "published-online", "issued"):
        value = item.get(key)
        parts = (value or {}).get("date-parts") or []
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                return None
    return None


def parse_authors(item):
    authors = []
    for author in item.get("author") or []:
        family = clean_text(author.get("family"))
        given = clean_text(author.get("given"))
        if family and given:
            authors.append(f"{family}, {given}")
        elif family:
            authors.append(family)
        elif given:
            authors.append(given)
    return "; ".join(authors)


def parse_crossref_item(item, journal_name):
    title = clean_text((item.get("title") or [""])[0])
    abstract = clean_abstract(item.get("abstract") or "")
    doi = normalize_doi(item.get("DOI"))
    return {
        "title": clean_title(title),
        "abstract": abstract,
        "authors": parse_authors(item),
        "journal": journal_name,
        "year": parse_year(item),
        "doi": doi,
        "_raw_title": title,
        "_page": clean_text(item.get("page")),
        "_volume": clean_text(item.get("volume")),
        "_issue": clean_text(item.get("issue")),
    }


def page_span(page):
    page = clean_text(page)
    if re.fullmatch(r"\d+", page):
        return 1
    alpha_match = re.match(r"^[A-Za-z]*(\d+)\s*[-–—]\s*[A-Za-z]*(\d+)$", page)
    if alpha_match:
        start, end = int(alpha_match.group(1)), int(alpha_match.group(2))
        if end >= start:
            return end - start + 1
    match = re.match(r"^(\d+)\s*[-–—]\s*(\d+)$", page)
    if not match:
        return None
    start, end = int(match.group(1)), int(match.group(2))
    if end < start:
        return None
    return end - start + 1


def has_book_review_shape(article):
    raw_title = clean_text(article.get("_raw_title"))
    title = clean_text(article.get("title"))
    combined = f"{raw_title} {title}"
    for pattern in BOOK_REVIEW_PATTERNS:
        if pattern.search(combined):
            return True
    return False


def is_short_no_abstract_review_risk(article, span):
    journal = clean_text(article.get("journal"))
    if journal not in SINGLE_PAGE_REVIEW_RISK_JOURNALS:
        return False
    title = clean_text(article.get("title"))
    page = clean_text(article.get("_page"))
    if not page:
        return True
    if title.startswith(":"):
        return True
    if title.endswith("."):
        return True
    if journal in STRICT_SINGLE_PAGE_METADATA_JOURNALS and re.fullmatch(r"\d+", page):
        return True
    if span is None:
        return False
    # Some Crossref records for older journals store only the start page.
    # Treat very short ranges as review risk only when the page field is an actual range.
    return span <= 4 and bool(re.search(r"[-–—]", page))


def classify_candidate(article):
    title = clean_text(article.get("title"))
    if not title:
        return "exclude", "空标题"

    for pattern in ADMIN_PATTERNS:
        if pattern.search(title):
            return "exclude", "行政性/目录性条目"

    should_drop, reason = should_delete(article)
    if should_drop:
        return "exclude", reason

    for pattern in REVIEW_LIKE_PATTERNS:
        if pattern.search(title):
            return "exclude", "书评/勘误/纪念性条目"

    span = page_span(article.get("_page"))
    if has_book_review_shape(article):
        if span is None or span <= 4 or not article.get("abstract"):
            return "exclude", "旧刊书评标题形态"
        return "review", "标题像书评但页数较长，需复核"

    if not article.get("authors"):
        if article.get("abstract"):
            return "review", "无作者但有摘要，需复核"
        return "exclude", "无作者且无摘要"

    if not article.get("abstract"):
        if is_short_no_abstract_review_risk(article, span):
            return "review", "无摘要且页数很短，可能是书评/短评"
        return "keep", "无摘要但元数据像论文，作为 metadata-only 记录保留"

    return "keep", "有摘要或元数据完整"


def fetch_year(journal_name, issn, year):
    CACHE_BACKFILL_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = CACHE_BACKFILL_DIR / f"{safe_slug(journal_name)}_{year}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8")), False

    items = []
    offset = 0
    while True:
        filter_str = (
            f"issn:{issn},"
            f"from-pub-date:{year}-01-01,"
            f"until-pub-date:{year}-12-31,"
            f"type:journal-article"
        )
        url = with_contact(
            f"{CROSSREF_BASE}"
            f"?filter={filter_str}"
            f"&rows={PAGE_SIZE}"
            f"&offset={offset}"
            f"&select=DOI,title,abstract,author,published,published-print,published-online,issued,type,volume,issue,page"
        )
        data = get_json(url)
        time.sleep(SLEEP_SEC)
        if not data or data.get("status") != "ok":
            return items, True

        page_items = data.get("message", {}).get("items", [])
        if not page_items:
            cache_path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return items, False

        for item in page_items:
            parsed = parse_crossref_item(item, journal_name)
            if parsed.get("year") is None:
                parsed["year"] = year
            items.append(parsed)

        if len(page_items) < PAGE_SIZE:
            cache_path.write_text(json.dumps(items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return items, False
        offset += len(page_items)


def load_articles():
    return json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))


def write_legacy_files(articles):
    legacy = []
    for article in articles:
        legacy.append({
            "Source Title": article.get("journal", ""),
            "Publication Year": article.get("year"),
            "Article Title": article.get("title", ""),
            "Author Full Names": article.get("authors", ""),
            "Abstract": article.get("abstract", ""),
            "DOI": article.get("doi", ""),
        })
    DATA_JSON.write_text(json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_articles(articles):
    clean_articles = []
    for article in articles:
        clean_articles.append({
            "title": clean_title(article.get("title", "")),
            "abstract": clean_abstract(article.get("abstract", "")),
            "authors": clean_text(article.get("authors", "")),
            "journal": clean_text(article.get("journal", "")),
            "year": article.get("year"),
            "doi": normalize_doi(article.get("doi", "")),
        })
    clean_articles.sort(key=lambda item: (item.get("journal", ""), item.get("year") or 0, item.get("title", "")))
    ARTICLES_JSON.write_text(json.dumps(clean_articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_legacy_files(clean_articles)


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "action", "reason", "journal", "year", "title", "authors", "doi",
        "abstract_length", "page", "volume", "issue",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def csv_row(article, action, reason):
    return {
        "action": action,
        "reason": reason,
        "journal": article.get("journal", ""),
        "year": article.get("year", ""),
        "title": article.get("title", ""),
        "authors": article.get("authors", ""),
        "doi": article.get("doi", ""),
        "abstract_length": len(article.get("abstract") or ""),
        "page": article.get("_page", ""),
        "volume": article.get("_volume", ""),
        "issue": article.get("_issue", ""),
    }


def selected_journals(names, include_adjacent):
    if not names:
        return {
            name: config
            for name, config in CORE_JOURNALS.items()
            if include_adjacent or config["pool"] == "core"
        }
    selected = {}
    invalid = []
    for raw in names:
        for name in raw.split(","):
            name = name.strip()
            if not name:
                continue
            if name not in CORE_JOURNALS:
                invalid.append(name)
            else:
                selected[name] = CORE_JOURNALS[name]
    if invalid:
        raise SystemExit(f"未知期刊: {', '.join(invalid)}")
    return selected


def build_indexes(articles):
    doi_index = {}
    title_index = {}
    for idx, article in enumerate(articles):
        doi = normalize_doi(article.get("doi"))
        if doi:
            doi_index[doi] = idx
        key = title_year_key(article)
        if key[2]:
            title_index[key] = idx
    return doi_index, title_index


def merge_candidate(candidate, articles, doi_index, title_index, stats, added_rows):
    doi = normalize_doi(candidate.get("doi"))
    if doi and doi in doi_index:
        idx = doi_index[doi]
        if candidate.get("abstract") and not articles[idx].get("abstract"):
            articles[idx]["abstract"] = candidate["abstract"]
            stats[candidate["journal"]]["updated_abstract"] += 1
        else:
            stats[candidate["journal"]]["duplicate"] += 1
        return

    key = title_year_key(candidate)
    if key[2] and key in title_index:
        idx = title_index[key]
        if candidate.get("abstract") and not articles[idx].get("abstract"):
            articles[idx]["abstract"] = candidate["abstract"]
            stats[candidate["journal"]]["updated_abstract"] += 1
        else:
            stats[candidate["journal"]]["duplicate"] += 1
        return

    clean_candidate = {
        "title": candidate.get("title", ""),
        "abstract": candidate.get("abstract", ""),
        "authors": candidate.get("authors", ""),
        "journal": candidate.get("journal", ""),
        "year": candidate.get("year"),
        "doi": candidate.get("doi", ""),
    }
    articles.append(clean_candidate)
    new_idx = len(articles) - 1
    if doi:
        doi_index[doi] = new_idx
    if key[2]:
        title_index[key] = new_idx
    stats[candidate["journal"]]["added"] += 1
    if not candidate.get("abstract"):
        stats[candidate["journal"]]["added_missing_abstract"] += 1
    added_rows.append(csv_row(candidate, "add", ""))


def build_report(args, before_articles, after_articles, stats, failures):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    before_by_journal = Counter(article.get("journal", "") for article in before_articles)
    after_by_journal = Counter(article.get("journal", "") for article in after_articles)
    before_abs = sum(1 for item in before_articles if clean_text(item.get("abstract")))
    if args.apply:
        after_abs = sum(1 for item in after_articles if clean_text(item.get("abstract")))
    else:
        estimated_new_abstracts = sum(
            item["updated_abstract"] + item["added"] - item["added_missing_abstract"]
            for item in stats.values()
        )
        after_abs = before_abs + estimated_new_abstracts
    lines = [
        "# 核心期刊早期补档报告",
        "",
        f"生成时间：{now}",
        f"运行模式：`{'apply' if args.apply else 'dry-run'}`",
        f"处理期刊：{', '.join(stats.keys())}",
        f"年份上限：{args.year_to}",
        "",
        "## 总览",
        "",
        f"- 补档前条目：{len(before_articles):,}",
        f"- 补档后条目：{len(after_articles):,}",
        f"- 净增加条目：{len(after_articles) - len(before_articles):,}",
        f"- 补档前有摘要：{before_abs:,}",
        f"- 补档后有摘要：{after_abs:,}",
        f"- 摘要净增加：{after_abs - before_abs:,}",
        "",
        "## 期刊结果",
        "",
        "| 期刊 | 原有 | 补档后 | 外部候选 | 新增 | 补摘要 | 新增无摘要 | 重复 | 排除 | 需复核 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for journal in stats:
        item = stats[journal]
        lines.append(
            f"| {journal} | {before_by_journal.get(journal, 0):,} | {after_by_journal.get(journal, 0):,} | "
            f"{item['seen']:,} | {item['added']:,} | {item['updated_abstract']:,} | "
            f"{item['added_missing_abstract']:,} | {item['duplicate']:,} | {item['excluded']:,} | {item['review']:,} |"
        )

    lines.extend([
        "",
        "## 输出文件",
        "",
        f"- 新增清单：`{ADDED_CSV.relative_to(ROOT)}`",
        f"- 排除清单：`{EXCLUDED_CSV.relative_to(ROOT)}`",
        f"- 需复核清单：`{REVIEW_CSV.relative_to(ROOT)}`",
        "",
        "## 纳入规则",
        "",
        "- 只处理配置中的核心/邻近期刊，按 ISSN 和年份抓取 Crossref `journal-article` 元数据。",
        "- DOI 已存在或标题+期刊+年份已存在时不新增；若本地缺摘要且候选有摘要，则只补摘要。",
        "- 明确的书评、目录、卷信息、编委会、勘误、纪念性条目和出版信息条目不入库。",
        "- 早期论文常无摘要；标题、作者和页码形态不像非论文条目的候选会作为 metadata-only 记录保留。",
        "- 卷期页码只用于本次清洗报告，暂不写入主库 schema。",
    ])

    if failures:
        lines.extend(["", "## 请求失败年份", ""])
        for journal, years in failures.items():
            lines.append(f"- {journal}: {', '.join(str(year) for year in years)}")

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    global SLEEP_SEC

    parser = argparse.ArgumentParser(description="补齐核心期刊早期论文元数据")
    parser.add_argument("--apply", action="store_true", help="写入 articles.json；默认只 dry-run")
    parser.add_argument("--include-adjacent", action="store_true",
                        help="同时处理 Journal of Marriage and Family 与 Sociology of Education")
    parser.add_argument("--journal", action="append",
                        help="限定期刊；可多次传入或用逗号分隔")
    parser.add_argument("--year-from", type=int, help="覆盖配置中的起始年")
    parser.add_argument("--year-to", type=int, default=datetime.now().year, help="截止年份")
    parser.add_argument("--sleep", type=float, default=SLEEP_SEC, help="Crossref 请求间隔秒数")
    args = parser.parse_args()

    SLEEP_SEC = args.sleep

    targets = selected_journals(args.journal, args.include_adjacent)
    if not targets:
        raise SystemExit("没有可处理的期刊")

    before_articles = load_articles()
    articles = json.loads(json.dumps(before_articles, ensure_ascii=False))
    doi_index, title_index = build_indexes(articles)
    stats = {journal: Counter() for journal in targets}
    failures = defaultdict(list)
    added_rows = []
    review_rows = []
    excluded_rows = []

    print(f"当前主库: {len(articles):,} 条", flush=True)
    print(f"运行模式: {'apply' if args.apply else 'dry-run'}", flush=True)
    print(f"目标期刊: {', '.join(targets)}", flush=True)

    for journal, config in targets.items():
        start_year = args.year_from or config["start_year"]
        print(f"\n=== {journal}: {start_year}-{args.year_to} ===", flush=True)
        for year in range(start_year, args.year_to + 1):
            items, failed = fetch_year(journal, config["issn"], year)
            if failed:
                failures[journal].append(year)
            if not items:
                continue
            stats[journal]["seen"] += len(items)
            for candidate in items:
                action, reason = classify_candidate(candidate)
                if action == "exclude":
                    stats[journal]["excluded"] += 1
                    excluded_rows.append(csv_row(candidate, "exclude", reason))
                elif action == "review":
                    stats[journal]["review"] += 1
                    review_rows.append(csv_row(candidate, "review", reason))
                else:
                    merge_candidate(candidate, articles, doi_index, title_index, stats, added_rows)
            if year % 10 == 0 or year == args.year_to:
                item = stats[journal]
                print(
                    f"  {year}: seen={item['seen']} added={item['added']} "
                    f"updated_abs={item['updated_abstract']} excluded={item['excluded']} review={item['review']}"
                , flush=True)

    write_csv(ADDED_CSV, added_rows)
    write_csv(REVIEW_CSV, review_rows)
    write_csv(EXCLUDED_CSV, excluded_rows)

    if args.apply:
        BACKUPS_DIR.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUPS_DIR / f"articles_before_core_backfill_{stamp}.json"
        shutil.copy2(ARTICLES_JSON, backup_path)
        print(f"\n已备份: {backup_path.relative_to(ROOT)}", flush=True)
        save_articles(articles)
        after_articles = load_articles()
    else:
        after_articles = before_articles + [
            {
                "title": row["title"],
                "abstract": "",
                "authors": row["authors"],
                "journal": row["journal"],
                "year": int(row["year"]) if str(row["year"]).isdigit() else None,
                "doi": row["doi"],
            }
            for row in added_rows
        ]

    build_report(args, before_articles, after_articles, stats, failures)
    print(f"\n报告: {REPORT_PATH.relative_to(ROOT)}", flush=True)
    print(f"新增候选: {len(added_rows):,}", flush=True)
    print(f"需复核: {len(review_rows):,}", flush=True)
    print(f"已排除: {len(excluded_rows):,}", flush=True)
    if not args.apply:
        print("dry-run 未修改 articles.json；确认后加 --apply 写入。", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断。", file=sys.stderr)
        raise
