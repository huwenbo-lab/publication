#!/usr/bin/env python3
"""Audit the current public snapshot and write a shareable quality report."""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime

from _paths import REPORTS_DIR, ROOT

ARTICLES_JSON = ROOT / "articles.json"
REPORT_PATH = REPORTS_DIR / "data_quality_report.md"

EXPECTED_JOURNALS = {
    "Advances in Life Course Research",
    "American Journal of Sociology",
    "American Sociological Review",
    "Annual Review of Sociology",
    "Asian Population Studies",
    "British Journal of Sociology",
    "British Journal of Sociology of Education",
    "Chinese Journal of Sociology",
    "Chinese Sociological Review",
    "Demographic Research",
    "Demography",
    "European Journal of Population",
    "European Sociological Review",
    "Gender & Society",
    "Journal of Family Issues",
    "Journal of Family Theory & Review",
    "Journal of Marriage and Family",
    "Population Studies",
    "Population and Development Review",
    "Research in Social Stratification and Mobility",
    "Social Forces",
    "Social Indicators Research",
    "Social Psychology Quarterly",
    "Social Science Research",
    "Sociological Science",
    "Sociology",
    "Sociology Compass",
    "Sociology of Education",
    "Socius",
    "Work and Occupations",
    "Work, Employment and Society",
}

# These three cutoffs are deliberate publication-scope decisions, not missing data.
ARCHIVE_CUTOFFS = {
    "American Journal of Sociology": 1950,
    "American Sociological Review": 1960,
    "Social Forces": 1950,
}

EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w-])",
    re.IGNORECASE,
)


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_doi(value):
    doi = clean(value).lower()
    return re.sub(r"^https?://doi\.org/", "", doi)


def normalize_title(value):
    title = clean(value).lower()
    return re.sub(r"[^a-z0-9]+", " ", title).strip()


def percentage(numerator, denominator):
    return f"{numerator / denominator:.1%}" if denominator else "—"


def load_articles():
    with ARTICLES_JSON.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, list):
        raise ValueError("articles.json 顶层必须是数组")
    return payload


def audit(articles):
    journal_rows = defaultdict(list)
    doi_counts = Counter()
    title_year_counts = Counter()
    email_occurrences = 0
    invalid_years = []

    missing = Counter()
    for index, article in enumerate(articles):
        for field in ("title", "abstract", "authors", "journal", "year", "doi"):
            if not clean(article.get(field)):
                missing[field] += 1

        journal = clean(article.get("journal"))
        year = article.get("year")
        journal_rows[journal].append(article)

        doi = normalize_doi(article.get("doi"))
        if doi:
            doi_counts[doi] += 1

        title = normalize_title(article.get("title"))
        if journal and isinstance(year, int) and title:
            title_year_counts[(journal, year, title)] += 1

        for field in ("title", "abstract", "authors"):
            public_text = clean(article.get(field))
            email_occurrences += len(EMAIL_PATTERN.findall(public_text))
            if field == "abstract":
                email_occurrences += public_text.count("@")

        if not isinstance(year, int) or year < 1800 or year > datetime.now().year:
            invalid_years.append((index, year))

    years = [
        article["year"]
        for article in articles
        if isinstance(article.get("year"), int)
    ]
    duplicate_doi_groups = {
        doi: count for doi, count in doi_counts.items() if count > 1
    }
    duplicate_title_groups = {
        key: count for key, count in title_year_counts.items() if count > 1
    }
    observed_journals = {journal for journal in journal_rows if journal}
    cutoff_violations = {
        journal: sum(
            1
            for article in journal_rows.get(journal, [])
            if isinstance(article.get("year"), int) and article["year"] < cutoff
        )
        for journal, cutoff in ARCHIVE_CUTOFFS.items()
    }

    return {
        "total": len(articles),
        "years": years,
        "journal_rows": journal_rows,
        "observed_journals": observed_journals,
        "missing_journals": EXPECTED_JOURNALS - observed_journals,
        "unexpected_journals": observed_journals - EXPECTED_JOURNALS,
        "missing": missing,
        "records_with_doi": sum(doi_counts.values()),
        "unique_doi": len(doi_counts),
        "duplicate_doi_groups": duplicate_doi_groups,
        "duplicate_title_groups": duplicate_title_groups,
        "email_occurrences": email_occurrences,
        "invalid_years": invalid_years,
        "cutoff_violations": cutoff_violations,
    }


def build_report(stats):
    total = stats["total"]
    years = stats["years"]
    with_abstract = total - stats["missing"]["abstract"]
    generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")

    lines = [
        "# 数据质量检查报告",
        "",
        f"> 生成时间：{generated_at}",
        "> 审计对象：当前公开主库 `articles.json`，不是本地 Web of Science XLS 归档。",
        "",
        "## 发布快照",
        "",
        f"- 记录：**{total:,}** 条",
        f"- 收录期刊：**{len(stats['observed_journals'])}** 本",
        f"- 年份范围：**{min(years)}–{max(years)}**",
        f"- 有摘要：**{with_abstract:,}** 条（{percentage(with_abstract, total)}）",
        f"- 缺摘要：**{stats['missing']['abstract']:,}** 条",
        f"- 有 DOI：**{stats['records_with_doi']:,}** 条",
        f"- 唯一 DOI：**{stats['unique_doi']:,}** 个",
        "",
        "## 完整性与重复",
        "",
        "| 检查项 | 数量 | 说明 |",
        "|---|---:|---|",
        f"| 缺标题 | {stats['missing']['title']:,} | 应为 0 |",
        f"| 缺作者 | {stats['missing']['authors']:,} | 历史元数据可能缺失 |",
        f"| 缺年份 | {stats['missing']['year']:,} | 应为 0 |",
        f"| 缺 DOI | {stats['missing']['doi']:,} | 无 DOI 的记录不会生成单篇 API 端点 |",
        f"| DOI 重复组 | {len(stats['duplicate_doi_groups']):,} | 应为 0 |",
        f"| 同刊同年同标题候选组 | {len(stats['duplicate_title_groups']):,} | 仅作人工复核，不自动删除 |",
        f"| 非法/未来年份 | {len(stats['invalid_years']):,} | 应为 0 |",
        f"| 公开文本中的邮箱 | {stats['email_occurrences']:,} | 应为 0 |",
        "",
        "## 分刊统计",
        "",
        "| 期刊 | 记录 | 年份范围 | 有摘要 | 缺 DOI |",
        "|---|---:|---|---:|---:|",
    ]

    for journal in sorted(stats["observed_journals"]):
        rows = stats["journal_rows"][journal]
        journal_years = [
            article["year"] for article in rows if isinstance(article.get("year"), int)
        ]
        with_journal_abstract = sum(
            1 for article in rows if clean(article.get("abstract"))
        )
        missing_journal_doi = sum(
            1 for article in rows if not normalize_doi(article.get("doi"))
        )
        lines.append(
            f"| {journal} | {len(rows):,} | "
            f"{min(journal_years)}–{max(journal_years)} | "
            f"{with_journal_abstract:,} | {missing_journal_doi:,} |"
        )

    lines.extend([
        "",
        "## 有意设置的早期档案边界",
        "",
        "以下边界来自已确认的发布口径，不应被质量脚本当作缺失数据回填：",
        "",
        "| 期刊 | 保留起点 | 起点前年份记录 |",
        "|---|---:|---:|",
    ])
    for journal, cutoff in ARCHIVE_CUTOFFS.items():
        lines.append(
            f"| {journal} | {cutoff} | {stats['cutoff_violations'][journal]:,} |"
        )

    lines.extend([
        "",
        "## 自动检查结论",
        "",
    ])
    errors = release_errors(stats)
    if errors:
        lines.append("**未通过。**")
        lines.extend(f"- {error}" for error in errors)
    else:
        lines.append(
            "**通过。** 期刊集合、DOI 唯一性、年份和早期档案边界均符合当前发布口径；"
            "同刊同年同标题候选仍需按需人工复核。"
        )
    lines.append("")
    return "\n".join(lines)


def release_errors(stats):
    errors = []
    if stats["missing"]["title"]:
        errors.append(f"存在 {stats['missing']['title']:,} 条缺标题记录")
    if stats["missing"]["journal"]:
        errors.append(f"存在 {stats['missing']['journal']:,} 条缺期刊记录")
    if stats["missing"]["year"]:
        errors.append(f"存在 {stats['missing']['year']:,} 条缺年份记录")
    if stats["missing_journals"]:
        errors.append("缺少期刊：" + "、".join(sorted(stats["missing_journals"])))
    if stats["unexpected_journals"]:
        errors.append("出现未配置期刊：" + "、".join(sorted(stats["unexpected_journals"])))
    if stats["duplicate_doi_groups"]:
        errors.append(f"存在 {len(stats['duplicate_doi_groups']):,} 组重复 DOI")
    if stats["invalid_years"]:
        errors.append(f"存在 {len(stats['invalid_years']):,} 条非法或未来年份")
    if stats["email_occurrences"]:
        errors.append(f"公开文本仍包含 {stats['email_occurrences']:,} 个邮箱")
    for journal, count in stats["cutoff_violations"].items():
        if count:
            errors.append(f"{journal} 有 {count:,} 条记录早于既定保留起点")
    return errors


def main():
    articles = load_articles()
    stats = audit(articles)
    report = build_report(stats)
    REPORT_PATH.write_text(report, encoding="utf-8")
    errors = release_errors(stats)
    print(
        f"已检查 {stats['total']:,} 条、{len(stats['observed_journals'])} 本期刊；"
        f"报告：{REPORT_PATH.relative_to(ROOT)}"
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("质量门禁通过")


if __name__ == "__main__":
    main()
