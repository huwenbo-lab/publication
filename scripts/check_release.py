#!/usr/bin/env python3
"""Fail fast on public-release regressions and derived-data drift."""

import argparse
import json
import re
import sqlite3
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlparse

from _paths import ROOT
from build_article_api import build_site_url, doi_to_relative_path
from check_quality import audit, load_articles, release_errors

DATA_JSON = ROOT / "data.json"
EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w-])",
    re.IGNORECASE,
)
ACTIVE_DOCS = (
    ROOT / "README.md",
    ROOT / "docs" / "guides" / "使用指南.md",
    ROOT / "lit_db" / "README.md",
    ROOT / "lit_db" / "overview.md",
    ROOT / "agent_lit_index" / "README.md",
)
TEXT_SUFFIXES = {
    "",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mjs",
    ".py",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
SOURCE_SCAN_PREFIXES = (
    ".github/",
    "docs/",
    "scripts/",
    "vendor/",
)
SOURCE_SCAN_ROOT_FILES = {
    ".env.example",
    ".gitignore",
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "app.js",
    "index.html",
    "opensearch.xml",
    "style.css",
}


def tracked_files():
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [
        Path(item.decode("utf-8", errors="surrogateescape"))
        for item in result.stdout.split(b"\0")
        if item
    ]


def expected_legacy(article):
    return {
        "Source Title": article.get("journal", ""),
        "Publication Year": article.get("year", ""),
        "Article Title": article.get("title", ""),
        "Author Full Names": article.get("authors", ""),
        "Abstract": article.get("abstract", ""),
        "DOI": article.get("doi", ""),
    }


def count_data_rows(path):
    with path.open(encoding="utf-8") as handle:
        return sum(1 for _ in handle) - 1


def scan_public_sources(paths):
    errors = []
    allowed_emails = {
        "41898282+github-actions[bot]@users.noreply.github.com",
        "project-contact@example.org",
    }

    for relative in paths:
        relative_posix = relative.as_posix()
        if not (
            relative_posix in SOURCE_SCAN_ROOT_FILES
            or relative_posix.startswith(SOURCE_SCAN_PREFIXES)
        ):
            continue
        path = ROOT / relative
        if path.suffix.lower() not in TEXT_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        mac_user_root = "/" + "Users/"
        if mac_user_root in text or re.search(r"\b[A-Za-z]:\\Users\\", text):
            errors.append(f"{relative_posix} 含本机绝对用户路径")
        unexpected_emails = sorted(
            {email for email in EMAIL_PATTERN.findall(text) if email not in allowed_emails}
        )
        if unexpected_emails:
            errors.append(
                f"{relative_posix} 含未批准的硬编码邮箱（{len(unexpected_emails)} 个）"
            )
        if re.search(
            r"(?im)^\s*(?:OPENALEX_API_KEY|API_KEY|TOKEN|SECRET)\s*=\s*['\"][^'\"]+['\"]",
            text,
        ):
            errors.append(f"{relative_posix} 疑似硬编码凭证")
    return errors


def validate_generated(total, unique_doi):
    errors = []
    titles_path = ROOT / "lit_db" / "titles" / "all_titles.tsv"
    agent_titles_path = (
        ROOT / "agent_lit_index" / "generated" / "index" / "full_titles.tsv"
    )
    sqlite_path = ROOT / "literature.db"
    api_overview_path = ROOT / "api" / "overview.json"

    for label, path in (
        ("lit_db 标题索引", titles_path),
        ("Agent 全量标题索引", agent_titles_path),
    ):
        if not path.exists():
            errors.append(f"缺少 {label}：{path.relative_to(ROOT)}")
            continue
        rows = count_data_rows(path)
        if rows != total:
            errors.append(f"{label} 为 {rows:,} 条，主库为 {total:,} 条")

    if not sqlite_path.exists():
        errors.append("缺少部署搜索库 literature.db")
    else:
        with sqlite3.connect(sqlite_path) as connection:
            rows = connection.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        if rows != total:
            errors.append(f"literature.db 为 {rows:,} 条，主库为 {total:,} 条")

    if not api_overview_path.exists():
        errors.append("缺少生成的 api/overview.json")
    else:
        overview = json.loads(api_overview_path.read_text(encoding="utf-8"))
        summary = overview.get("summary", {})
        if summary.get("total_articles") != total:
            errors.append("api/overview.json 的记录数与主库不一致")
        if summary.get("unique_article_json") != unique_doi:
            errors.append("api/overview.json 的 DOI 端点数与主库不一致")
    return errors


def validate_api_url_contract(articles):
    """Ensure one URL decode resolves to each percent-escaped API filename."""
    errors = []
    checked = 0
    for article in articles:
        relative = doi_to_relative_path(article.get("doi"))
        if not relative or "%" not in relative.as_posix():
            continue
        physical_relative = Path("api") / relative
        public_url = build_site_url(physical_relative)
        decoded_path = unquote(urlparse(public_url).path)
        if not decoded_path.endswith("/" + physical_relative.as_posix()):
            errors.append(
                "特殊字符 DOI 的公开 URL 与物理 API 文件名不一致："
                f"{article.get('doi', '')}"
            )
            break
        checked += 1
    if checked == 0:
        errors.append("未找到可用于验证 API URL 编码的特殊字符 DOI")
    return errors


def main():
    parser = argparse.ArgumentParser(description="检查公开发布边界和派生数据")
    parser.add_argument(
        "--with-generated",
        action="store_true",
        help="同时核对 API、lit_db、Agent 索引和 SQLite",
    )
    args = parser.parse_args()

    errors = []
    articles = load_articles()
    stats = audit(articles)
    errors.extend(release_errors(stats))
    errors.extend(validate_api_url_contract(articles))

    with DATA_JSON.open(encoding="utf-8") as handle:
        legacy = json.load(handle)
    if len(legacy) != len(articles):
        errors.append(
            f"data.json 为 {len(legacy):,} 条，articles.json 为 {len(articles):,} 条"
        )
    else:
        for index, (article, legacy_row) in enumerate(zip(articles, legacy)):
            if legacy_row != expected_legacy(article):
                errors.append(f"data.json 第 {index + 1} 条与 articles.json 映射不一致")
                break

    paths = tracked_files()
    tracked_posix = {path.as_posix() for path in paths}
    forbidden_tracked = sorted(
        path
        for path in tracked_posix
        if path == "data.js"
        or path.startswith("api/")
        or (path.startswith("raw_data/") and path.lower().endswith(".xls"))
    )
    if forbidden_tracked:
        errors.append(
            "仍在跟踪部署生成物或受限原始导出："
            + "、".join(forbidden_tracked[:5])
            + ("…" if len(forbidden_tracked) > 5 else "")
        )

    errors.extend(scan_public_sources(paths))

    for path in ACTIVE_DOCS:
        if not path.exists():
            errors.append(f"缺少对外文档：{path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        if (
            "31本核心期刊、46,179" in text
            or "主数据文件（46,179" in text
            or "1896–2026" in text
        ):
            errors.append(f"{path.relative_to(ROOT)} 仍含旧版数据规模")
        if "2020_2026" in text:
            errors.append(f"{path.relative_to(ROOT)} 仍含会过期的年份分片名")

    if args.with_generated:
        errors.extend(validate_generated(stats["total"], stats["unique_doi"]))

    if errors:
        print("发布检查未通过：")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)

    print(
        "发布检查通过："
        f"{stats['total']:,} 条、{len(stats['observed_journals'])} 本期刊、"
        f"{min(stats['years'])}–{max(stats['years'])}、"
        f"{stats['unique_doi']:,} 个 DOI 端点"
    )


if __name__ == "__main__":
    main()
