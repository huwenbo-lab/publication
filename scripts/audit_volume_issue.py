"""
audit_volume_issue.py — dry-run 检测 raw_data 中可补充的卷期/页码字段

本脚本不修改 articles.json。它只用 DOI 将 raw_data/*.xls 中的 Volume、Issue、
Publication Date、Start Page、End Page 等字段与主数据匹配，输出可补充清单，
供后续人工确认 schema 后再决定是否写入主数据。
"""

import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import xlrd

from _paths import REPORTS_DIR, ROOT

ARTICLES_JSON = ROOT / "articles.json"
RAW_DATA = ROOT / "raw_data"
EXPORTS_DIR = ROOT / "exports"
OUTPUT_CSV = EXPORTS_DIR / "volume_issue_dry_run.csv"
REPORT_PATH = REPORTS_DIR / "volume_issue_dry_run_report.md"


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_doi(value):
    doi = clean_text(value)
    doi = re.sub(r"^https?://doi\.org/", "", doi, flags=re.I)
    return doi.lower()


def load_articles_by_doi():
    articles = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
    by_doi = {}
    for index, article in enumerate(articles):
        doi = normalize_doi(article.get("doi"))
        if doi and doi not in by_doi:
            by_doi[doi] = (index, article)
    return articles, by_doi


def read_raw_rows():
    rows = []
    for path in sorted(RAW_DATA.glob("*.xls")):
        workbook = xlrd.open_workbook(str(path))
        sheet = workbook.sheet_by_index(0)
        headers = [clean_text(sheet.cell_value(0, col)) for col in range(sheet.ncols)]
        for row_index in range(1, sheet.nrows):
            row = {
                headers[col]: clean_text(sheet.cell_value(row_index, col))
                for col in range(sheet.ncols)
            }
            row["_raw_file"] = path.name
            row["_raw_row"] = row_index + 1
            rows.append(row)
    return rows


def build_candidates(raw_rows, articles_by_doi):
    candidates = []
    for row in raw_rows:
        doi = normalize_doi(row.get("DOI"))
        if not doi:
            continue
        article_match = articles_by_doi.get(doi)
        if not article_match:
            match_status = "raw_doi_not_in_articles"
            article_index = ""
            article = {}
        else:
            match_status = "matched"
            article_index, article = article_match

        volume = clean_text(row.get("Volume"))
        issue = clean_text(row.get("Issue"))
        start_page = clean_text(row.get("Start Page"))
        end_page = clean_text(row.get("End Page"))
        article_number = clean_text(row.get("Article Number"))
        publication_date = clean_text(row.get("Publication Date"))
        publication_type = clean_text(row.get("Publication Type"))
        document_type = clean_text(row.get("Document Type"))

        has_candidate_field = any([volume, issue, start_page, end_page, article_number, publication_date, publication_type, document_type])
        if not has_candidate_field:
            continue

        candidates.append({
            "match_status": match_status,
            "article_index": article_index,
            "doi": doi,
            "article_title": clean_text(article.get("title")),
            "raw_title": clean_text(row.get("Article Title")),
            "journal": clean_text(article.get("journal") or row.get("Source Title")),
            "year": article.get("year") or clean_text(row.get("Publication Year")),
            "volume": volume,
            "issue": issue,
            "start_page": start_page,
            "end_page": end_page,
            "article_number": article_number,
            "publication_date": publication_date,
            "publication_type": publication_type,
            "document_type": document_type,
            "raw_file": row["_raw_file"],
            "raw_row": row["_raw_row"],
        })
    return candidates


def write_csv(rows):
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "match_status", "article_index", "doi", "article_title", "raw_title", "journal", "year",
        "volume", "issue", "start_page", "end_page", "article_number", "publication_date",
        "publication_type", "document_type", "raw_file", "raw_row",
    ]
    with OUTPUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_report(articles, raw_rows, candidates):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    status_counts = Counter(row["match_status"] for row in candidates)
    matched = [row for row in candidates if row["match_status"] == "matched"]
    with_volume_issue = [row for row in matched if row["volume"] or row["issue"]]

    lines = [
        "# 卷期字段补充 dry-run 报告",
        "",
        f"生成时间：{now}",
        "",
        "## 结论",
        "",
        "- 本脚本没有修改主数据。",
        "- `articles.json` 当前没有 `volume`、`issue`、`pages`、`publication_date`、`publication_type`、`document_type` 字段。",
        "- `raw_data/*.xls` 中存在这些字段，但只覆盖部分期刊和原始 WoS 导出范围。",
        "- 建议后续先确定主数据 schema，再用 DOI 精确匹配写入；对 raw_data 覆盖不到的期刊，再用 CrossRef/OpenAlex dry-run 补充。",
        "",
        "## 统计",
        "",
        f"- `articles.json` 记录数：{len(articles):,}",
        f"- raw_data 行数：{len(raw_rows):,}",
        f"- 输出候选行数：{len(candidates):,}",
        f"- DOI 匹配主数据且存在卷期/页码等字段：{len(matched):,}",
        f"- DOI 匹配且至少有 volume 或 issue：{len(with_volume_issue):,}",
        f"- 输出 CSV：`{OUTPUT_CSV.relative_to(ROOT)}`",
        "",
        "## 匹配状态",
        "",
        "| 状态 | 数量 |",
        "|---|---:|",
    ]
    for status, count in status_counts.most_common():
        lines.append(f"| {status} | {count} |")

    lines.extend([
        "",
        "## 后续补充方案",
        "",
        "1. 新增主数据字段：`volume`、`issue`、`start_page`、`end_page`、`article_number`、`publication_date`、`publication_type`、`document_type`，并更新 `data.json` 兼容字段映射。",
        "2. 先用本 CSV 中 `match_status=matched` 且 DOI 唯一的记录补充 raw_data 覆盖范围。",
        "3. 对 raw_data 无覆盖或 DOI 不匹配的期刊，新增 CrossRef/OpenAlex dry-run，只输出候选，不直接写入。",
        "4. 抽样人工核对不同出版社的卷期格式，确认空字符串、early access、article number 与页码的表示方式。",
        "",
    ])
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="dry-run 检测 raw_data 可补充的卷期/页码字段")
    parser.add_argument("--dry-run", action="store_true", help="保留兼容参数；脚本始终只 dry-run")
    parser.parse_args()

    articles, articles_by_doi = load_articles_by_doi()
    raw_rows = read_raw_rows()
    candidates = build_candidates(raw_rows, articles_by_doi)
    write_csv(candidates)
    write_report(articles, raw_rows, candidates)
    print(f"raw_data 行数：{len(raw_rows):,}")
    print(f"候选行数：{len(candidates):,}")
    print(f"输出 CSV：{OUTPUT_CSV}")
    print(f"报告：{REPORT_PATH}")


if __name__ == "__main__":
    main()
