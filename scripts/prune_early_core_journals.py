"""
prune_early_core_journals.py — 删除指定核心期刊的早期记录

本脚本用于把全量主库也收窄到当前研究工作流采用的年份节点：

- American Journal of Sociology: 1950+
- American Sociological Review: 1960+
- Social Forces: 1950+

默认 dry-run。加 `--apply` 后会备份 articles.json，并同步重建 data.json。
"""

import argparse
import csv
import json
import shutil
from collections import Counter
from datetime import datetime

from _paths import REPORTS_DIR, ROOT

ARTICLES_JSON = ROOT / "articles.json"
DATA_JSON = ROOT / "data.json"
BACKUPS_DIR = ROOT / "backups"
EXPORTS_DIR = ROOT / "exports"
REPORT_PATH = REPORTS_DIR / "core_archive_pruning_report.md"
REMOVED_CSV = EXPORTS_DIR / "early_core_journals_removed.csv"

CUTOFFS = {
    "American Journal of Sociology": 1950,
    "American Sociological Review": 1960,
    "Social Forces": 1950,
}


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


def should_remove(article):
    journal = article.get("journal")
    cutoff = CUTOFFS.get(journal)
    if cutoff is None:
        return False
    year = article.get("year")
    return isinstance(year, int) and year < cutoff


def write_removed_csv(rows):
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    fields = ["journal", "year", "title", "authors", "doi", "has_abstract", "cutoff"]
    with REMOVED_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for article in rows:
            writer.writerow({
                "journal": article.get("journal", ""),
                "year": article.get("year", ""),
                "title": article.get("title", ""),
                "authors": article.get("authors", ""),
                "doi": article.get("doi", ""),
                "has_abstract": bool((article.get("abstract") or "").strip()),
                "cutoff": CUTOFFS.get(article.get("journal"), ""),
            })


def build_report(before_articles, after_articles, removed, apply):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    before_counts = Counter(article.get("journal", "") for article in before_articles)
    after_counts = Counter(article.get("journal", "") for article in after_articles)
    removed_counts = Counter(article.get("journal", "") for article in removed)
    removed_abs = Counter(
        article.get("journal", "")
        for article in removed
        if (article.get("abstract") or "").strip()
    )

    lines = [
        "# 核心期刊早期记录裁剪报告",
        "",
        f"生成时间：{now}",
        f"运行模式：`{'apply' if apply else 'dry-run'}`",
        "",
        "## 裁剪规则",
        "",
    ]
    for journal, cutoff in CUTOFFS.items():
        lines.append(f"- {journal}: 保留 {cutoff} 年及以后，删除 {cutoff} 年以前。")

    lines.extend([
        "",
        "## 总览",
        "",
        f"- 裁剪前记录数：{len(before_articles):,}",
        f"- 删除记录数：{len(removed):,}",
        f"- 裁剪后记录数：{len(after_articles):,}",
        f"- 删除清单：`{REMOVED_CSV.relative_to(ROOT)}`",
        "",
        "## 按期刊变化",
        "",
        "| 期刊 | 节点 | 裁剪前 | 删除 | 其中有摘要 | 裁剪后 |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for journal, cutoff in CUTOFFS.items():
        lines.append(
            f"| {journal} | {cutoff}+ | {before_counts[journal]:,} | "
            f"{removed_counts[journal]:,} | {removed_abs[journal]:,} | {after_counts[journal]:,} |"
        )

    if not apply:
        lines.extend(["", "本次未修改 `articles.json`。"])

    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="删除 AJS/ASR/Social Forces 的早期记录")
    parser.add_argument("--apply", action="store_true", help="写入 articles.json；默认只 dry-run")
    args = parser.parse_args()

    articles = load_articles()
    removed = [article for article in articles if should_remove(article)]
    kept = [article for article in articles if not should_remove(article)]

    write_removed_csv(removed)
    build_report(articles, kept, removed, args.apply)

    print(f"运行模式: {'apply' if args.apply else 'dry-run'}")
    print(f"裁剪前: {len(articles):,}")
    print(f"删除: {len(removed):,}")
    print(f"裁剪后: {len(kept):,}")
    for journal, cutoff in CUTOFFS.items():
        n = sum(1 for article in removed if article.get("journal") == journal)
        print(f"  {journal} < {cutoff}: {n:,}")
    print(f"删除清单: {REMOVED_CSV.relative_to(ROOT)}")
    print(f"报告: {REPORT_PATH.relative_to(ROOT)}")

    if not args.apply:
        print("dry-run 未修改 articles.json；确认后加 --apply 写入。")
        return

    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUPS_DIR / f"articles_before_early_core_pruning_{stamp}.json"
    shutil.copy2(ARTICLES_JSON, backup_path)

    ARTICLES_JSON.write_text(json.dumps(kept, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_legacy_files(kept)
    print(f"已备份: {backup_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
