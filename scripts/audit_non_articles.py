"""
audit_non_articles.py — 可审计筛查并清理非学术文献条目

默认 dry-run，只生成候选清单和报告；只有显式传入 --apply 才会删除高置信度
行政性、目录性、编委会和投稿说明类条目。Editorial、Introduction、Book Review
等边界类型默认只进入人工复核清单。若用户已经人工确认这些边界候选也应删除，
可使用 --apply --include-review。
"""

import argparse
import csv
import json
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

from _paths import REPORTS_DIR, ROOT

ARTICLES_JSON = ROOT / "articles.json"
DATA_JSON = ROOT / "data.json"
DATA_JS = ROOT / "data.js"
BACKUPS_DIR = ROOT / "backups"
EXPORTS_DIR = ROOT / "exports"

CANDIDATES_CSV = EXPORTS_DIR / "non_article_candidates.csv"
REMOVED_CSV = EXPORTS_DIR / "non_article_removed.csv"
REVIEW_CSV = EXPORTS_DIR / "non_article_needs_review.csv"
REPORT_PATH = REPORTS_DIR / "non_article_audit_report.md"

HIGH_CONFIDENCE_PATTERNS = [
    ("Editorial Board", re.compile(r"^editorial board(?:\s+\d{4})?$")),
    ("Masthead", re.compile(r"^masthead$")),
    ("Front Matter", re.compile(r"^front matter$")),
    ("Back Matter", re.compile(r"^back matter$")),
    ("Table of Contents", re.compile(r"^table of contents$")),
    ("Contents", re.compile(r"^(?:volume )?contents$")),
    ("Issue Information", re.compile(r"^issue information$")),
    ("Publication Information", re.compile(r"^publication information$")),
    ("Information for Authors", re.compile(r"^information for authors$")),
    ("Instructions for Authors", re.compile(r"^instructions for authors$")),
    ("List of Reviewers", re.compile(r"^list of reviewers$")),
    ("Acknowledgement of Reviewers", re.compile(r"^acknowledg?ement of reviewers$")),
    ("Annual Reviewer List", re.compile(r"^annual reviewer list$")),
    ("Index", re.compile(r"^index$")),
]

REVIEW_PATTERNS = [
    ("Editorial", re.compile(r"\beditorial\b")),
    ("Introduction", re.compile(r"\bintroduction\b")),
    ("Special Issue Introduction", re.compile(r"\bspecial issue introduction\b")),
    ("Commentary", re.compile(r"\bcommentary\b")),
    ("Reply", re.compile(r"\breply\b")),
    ("Response", re.compile(r"\bresponse\b")),
    ("Correction", re.compile(r"\bcorrection\b")),
    ("Erratum", re.compile(r"\berratum\b")),
    ("Retraction", re.compile(r"\bretraction\b")),
    ("Book Review", re.compile(r"\bbook review\b")),
    ("Review Essay", re.compile(r"\breview essay\b")),
    ("Obituary", re.compile(r"\bobituary\b")),
    ("In Memoriam", re.compile(r"\bin memoriam\b")),
    ("Announcement", re.compile(r"\bannouncement\b")),
    ("Call for Papers", re.compile(r"\bcall for papers\b")),
]

RESEARCH_ABSTRACT_HINTS = re.compile(
    r"\b(data|method|methods|model|models|analysis|analy[sz]e|find|findings|results|"
    r"survey|sample|interview|theory|theoretical|hypothesis|evidence|estimate|regression)\b",
    re.I,
)


def clean_text(value):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def normalize_title(title):
    text = clean_text(title).lower()
    text = text.replace("&", "and")
    text = re.sub(r"[\u2010-\u2015]", "-", text)
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def has_research_like_abstract(abstract):
    text = clean_text(abstract)
    return len(text) >= 700 and bool(RESEARCH_ABSTRACT_HINTS.search(text))


def classify_article(article):
    title = clean_text(article.get("title"))
    normalized = normalize_title(title)
    abstract = clean_text(article.get("abstract"))

    if not title:
        return None

    for label, pattern in REVIEW_PATTERNS:
        if pattern.search(normalized):
            return {
                "action": "needs_review",
                "reason": f"边界类型：{label}",
                "confidence": "medium",
            }

    for label, pattern in HIGH_CONFIDENCE_PATTERNS:
        if pattern.fullmatch(normalized):
            if has_research_like_abstract(abstract):
                return {
                    "action": "needs_review",
                    "reason": f"标题像非文献条目（{label}），但摘要较长且含研究信号",
                    "confidence": "medium",
                }
            return {
                "action": "auto_remove",
                "reason": f"高置信度非文献条目：{label}",
                "confidence": "high",
            }

    return None


def load_articles():
    return json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))


def write_legacy_files(articles):
    legacy = [{
        "Source Title": article.get("journal", ""),
        "Publication Year": article.get("year"),
        "Article Title": article.get("title", ""),
        "Author Full Names": article.get("authors", ""),
        "Abstract": article.get("abstract", ""),
        "DOI": article.get("doi", ""),
    } for article in articles]
    DATA_JSON.write_text(json.dumps(legacy, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DATA_JS.write_text("const DATA = " + json.dumps(legacy, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "index", "action", "confidence", "reason", "title", "journal", "year",
        "doi", "authors", "abstract_length",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def count_by(items, key):
    return Counter(str(item.get(key) or "未知") for item in items)


def top_changes(before, after):
    keys = sorted(set(before) | set(after))
    rows = []
    for key in keys:
        diff = after.get(key, 0) - before.get(key, 0)
        if diff:
            rows.append((key, before.get(key, 0), after.get(key, 0), diff))
    rows.sort(key=lambda item: (item[3], item[0]))
    return rows


def build_report(args, articles, candidates, auto_remove, needs_review, removed_rows, backup_path,
                 removed_archive_path=None, after_articles=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    mode = "apply" if args.apply else "dry-run"
    before_journal = count_by(articles, "journal")
    before_year = count_by(articles, "year")
    after_journal = count_by(after_articles, "journal") if after_articles is not None else before_journal
    after_year = count_by(after_articles, "year") if after_articles is not None else before_year

    lines = [
        "# 非文献条目审计报告",
        "",
        f"生成时间：{now}",
        f"运行模式：`{mode}`",
        f"审计前记录数：{len(articles):,}",
        f"候选条目数：{len(candidates):,}",
        f"高置信度自动删除候选：{len(auto_remove):,}",
        f"人工复核候选：{len(needs_review):,}",
        f"本次计划删除候选：{len(removed_rows):,}",
        "",
        "## 输出文件",
        "",
        f"- 候选清单：`{CANDIDATES_CSV.relative_to(ROOT)}`",
        f"- 删除清单：`{REMOVED_CSV.relative_to(ROOT)}`（dry-run 无计划删除时保留既有清单）",
        f"- 人工复核清单：`{REVIEW_CSV.relative_to(ROOT)}`",
    ]

    if args.apply:
        lines.extend([
            f"- 自动备份：`{backup_path.relative_to(ROOT) if backup_path else ''}`",
            f"- 删除清单归档：`{removed_archive_path.relative_to(ROOT) if removed_archive_path else ''}`",
            f"- 审计后记录数：{len(after_articles):,}",
            f"- 实际删除数：{len(articles) - len(after_articles):,}",
        ])
    else:
        lines.append("- 本次未修改 `articles.json`。")

    lines.extend([
        "",
        "## 删除原则",
        "",
        "- 只自动删除标题完全匹配或高度接近行政性、目录性、编委会、投稿说明、出版信息类的条目。",
        "- `Editorial`、`Introduction`、`Commentary`、`Book Review`、`Correction`、`Erratum` 等边界类型默认不自动删除。",
        "- 若已人工确认边界候选也应删除，可使用 `--apply --include-review`；本次是否包含人工复核候选："
        f"{'是' if args.include_review else '否'}。",
        "- 如果标题像非文献条目但摘要较长且含研究信号，转入人工复核。",
        "",
        "## 按期刊变化",
        "",
        "| 期刊 | 删除前 | 删除后 | 变化 |",
        "|---|---:|---:|---:|",
    ])
    journal_changes = top_changes(before_journal, after_journal)
    if journal_changes:
        for journal, before, after, diff in journal_changes:
            lines.append(f"| {journal} | {before} | {after} | {diff} |")
    else:
        lines.append("| 无变化 |  |  |  |")

    lines.extend([
        "",
        "## 按年份变化",
        "",
        "| 年份 | 删除前 | 删除后 | 变化 |",
        "|---|---:|---:|---:|",
    ])
    year_changes = top_changes(before_year, after_year)
    if year_changes:
        for year, before, after, diff in year_changes:
            lines.append(f"| {year} | {before} | {after} | {diff} |")
    else:
        lines.append("| 无变化 |  |  |  |")

    lines.extend([
        "",
        "## 后续人工复核建议",
        "",
        "请优先打开 `exports/non_article_needs_review.csv`，逐条判断边界类型是否保留。不要仅凭标题中包含 `review` 或 `editorial` 就自动删除，因为这些可能是学术评论、专题导论或勘误。",
        "",
    ])

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="审计并可选清理 articles.json 中的非文献条目")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="只生成清单和报告，不修改数据")
    mode.add_argument("--apply", action="store_true", help="删除高置信度非文献条目，并先备份 articles.json")
    parser.add_argument("--include-review", action="store_true",
                        help="与 --apply 同用：把人工复核候选也纳入删除。需先人工确认。")
    args = parser.parse_args()
    if not args.apply:
        args.dry_run = True
    if args.include_review and not args.apply:
        parser.error("--include-review 只能与 --apply 一起使用")

    articles = load_articles()
    candidates = []
    for index, article in enumerate(articles):
        classification = classify_article(article)
        if not classification:
            continue
        candidates.append({
            "index": index,
            **classification,
            "title": clean_text(article.get("title")),
            "journal": clean_text(article.get("journal")),
            "year": article.get("year") or "",
            "doi": clean_text(article.get("doi")),
            "authors": clean_text(article.get("authors")),
            "abstract_length": len(clean_text(article.get("abstract"))),
        })

    auto_remove = [row for row in candidates if row["action"] == "auto_remove"]
    needs_review = [row for row in candidates if row["action"] == "needs_review"]

    removed_rows = auto_remove + (needs_review if args.include_review else [])

    write_csv(CANDIDATES_CSV, candidates)
    if args.apply or removed_rows or not REMOVED_CSV.exists():
        write_csv(REMOVED_CSV, removed_rows)
    write_csv(REVIEW_CSV, needs_review)

    backup_path = None
    removed_archive_path = None
    after_articles = None
    if args.apply and removed_rows:
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUPS_DIR / f"articles_before_non_article_cleaning_{timestamp}.json"
        removed_archive_path = EXPORTS_DIR / f"non_article_removed_{timestamp}.csv"
        shutil.copy2(ARTICLES_JSON, backup_path)
        write_csv(removed_archive_path, removed_rows)
        remove_indices = {row["index"] for row in removed_rows}
        after_articles = [article for index, article in enumerate(articles) if index not in remove_indices]
        ARTICLES_JSON.write_text(json.dumps(after_articles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        write_legacy_files(after_articles)
    elif args.apply:
        after_articles = articles

    build_report(args, articles, candidates, auto_remove, needs_review, removed_rows, backup_path,
                 removed_archive_path, after_articles)

    print(f"候选条目：{len(candidates):,}")
    print(f"高置信度自动删除候选：{len(auto_remove):,}")
    print(f"人工复核候选：{len(needs_review):,}")
    print(f"本次计划删除候选：{len(removed_rows):,}")
    print(f"候选清单：{CANDIDATES_CSV}")
    print(f"人工复核清单：{REVIEW_CSV}")
    print(f"报告：{REPORT_PATH}")
    if args.apply:
        print(f"已删除：{len(removed_rows):,}")
        if backup_path:
            print(f"备份：{backup_path}")
        if removed_archive_path:
            print(f"删除清单归档：{removed_archive_path}")


if __name__ == "__main__":
    main()
