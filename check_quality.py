"""
check_quality.py — 数据质量检查脚本
读取所有 .xls 文件，生成 data_quality_report.md（中文报告）
"""
import os
import re
from datetime import datetime
from pathlib import Path

import xlrd

ROOT = Path(__file__).resolve().parent
RAW_DATA = ROOT / "raw_data"   # XLS 原始文件目录

# 文件名到标准期刊名的映射（处理拼写错误等）
FILENAME_TO_JOURNAL = {
    "American Journal of Sociology.xls": "American Journal of Sociology",
    "American Sociological Review.xls": "American Sociological Review",
    "Annual Review of Sociology.xls": "Annual Review of Sociology",
    "British Journal of Sociology.xls": "British Journal of Sociology",
    "British of Journal of Sociology of Education.xls": "British Journal of Sociology of Education",
    "Chinese Journal of Sociology.xls": "Chinese Journal of Sociology",
    "Chinese Sociological Review.xls": "Chinese Sociological Review",
    "Demographic Research.xls": "Demographic Research",
    "Demography.xls": "Demography",
    "European Sociological Review.xls": "European Sociological Review",
    "Journal of Family Issues.xls": "Journal of Family Issues",
    "Journal of Marriage and Family.xls": "Journal of Marriage and Family",
    "Population and Development Review.xls": "Population and Development Review",
    "Research in Social Stratification and Mobility.xls": "Research in Social Stratification and Mobility",
    "Social Forces.xls": "Social Forces",
    "Social Science Research.xls": "Social Science Research",
    "Sociology of Education.xls": "Sociology of Education",
}

# 25本目标期刊及其数据起始年
TARGET_JOURNALS = {
    "American Journal of Sociology": 2000,
    "American Sociological Review": 2000,
    "Annual Review of Sociology": 2000,
    "Asian Population Studies": 2005,
    "British Journal of Sociology": 2000,
    "British Journal of Sociology of Education": 2000,
    "Chinese Journal of Sociology": 2015,
    "Chinese Sociological Review": 2000,
    "Demographic Research": 2000,
    "Demography": 2000,
    "European Journal of Population": 2000,
    "European Sociological Review": 2000,
    "Gender & Society": 2000,
    "Journal of Family Issues": 2000,
    "Journal of Family Theory & Review": 2009,
    "Journal of Marriage and Family": 2000,
    "Population and Development Review": 2000,
    "Research in Social Stratification and Mobility": 2000,
    "Social Forces": 2000,
    "Social Science Research": 2000,
    "Sociological Science": 2014,
    "Sociology": 2000,
    "Sociology of Education": 2000,
    "Socius": 2015,
    "Work, Employment and Society": 2000,
}

CURRENT_YEAR = datetime.now().year


def normalize_text(v):
    text = str(v or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def read_xls(filepath):
    """读取WoS格式的XLS文件，返回(headers, rows)"""
    wb = xlrd.open_workbook(filepath)
    sh = wb.sheet_by_index(0)
    headers = [str(sh.cell_value(0, i)).strip() for i in range(sh.ncols)]
    rows = []
    for r in range(1, sh.nrows):
        row = {headers[i]: sh.cell_value(r, i) for i in range(sh.ncols)}
        rows.append(row)
    return headers, rows


def get_field(row, *keys):
    for k in keys:
        v = row.get(k, "")
        if v and str(v).strip():
            return str(v).strip()
    return ""


def check_journal(journal_name, rows):
    """检查单本期刊的数据质量"""
    total = len(rows)

    years = []
    missing_year = 0
    missing_abstract = 0
    missing_doi = 0
    missing_authors = 0

    doi_set = set()
    title_key_set = set()
    doi_dups = 0
    title_dups = 0

    for row in rows:
        title = get_field(row, "Article Title")
        abstract = get_field(row, "Abstract")
        authors = get_field(row, "Author Full Names", "Authors")
        doi = get_field(row, "DOI")
        year_raw = row.get("Publication Year", "")

        # 年份
        try:
            year = int(float(str(year_raw))) if year_raw else None
        except (ValueError, TypeError):
            year = None

        if year:
            years.append(year)
        else:
            missing_year += 1

        if not abstract:
            missing_abstract += 1
        if not doi:
            missing_doi += 1
        if not authors:
            missing_authors += 1

        # 重复检测（按DOI）
        if doi:
            doi_norm = doi.strip().lower()
            if doi_norm in doi_set:
                doi_dups += 1
            else:
                doi_set.add(doi_norm)

        # 重复检测（按标题+年份）
        if title and year:
            key = normalize_text(title) + str(year)
            if key in title_key_set:
                title_dups += 1
            else:
                title_key_set.add(key)

    year_min = min(years) if years else None
    year_max = max(years) if years else None

    target_start = TARGET_JOURNALS.get(journal_name, 2000)
    gap_years = []
    if year_min and year_min > target_start:
        gap_years = list(range(target_start, year_min))

    # WoS导出上限判断
    hit_wos_limit = total >= 1000

    return {
        "total": total,
        "year_min": year_min,
        "year_max": year_max,
        "missing_year": missing_year,
        "missing_abstract": missing_abstract,
        "missing_doi": missing_doi,
        "missing_authors": missing_authors,
        "doi_dups": doi_dups,
        "title_dups": title_dups,
        "gap_years": gap_years,
        "hit_wos_limit": hit_wos_limit,
        "target_start": target_start,
    }


def main():
    print("开始检查数据质量...")

    # 找到所有XLS文件
    xls_files = sorted([
        f for f in os.listdir(RAW_DATA)
        if f.endswith(".xls") and f in FILENAME_TO_JOURNAL
    ])

    results = {}
    all_rows_count = 0

    for filename in xls_files:
        journal_name = FILENAME_TO_JOURNAL[filename]
        filepath = RAW_DATA / filename
        print(f"  读取: {filename}")
        _, rows = read_xls(str(filepath))
        stats = check_journal(journal_name, rows)
        results[journal_name] = stats
        all_rows_count += stats["total"]

    # 识别缺失期刊
    missing_journals = [j for j in TARGET_JOURNALS if j not in results]

    # 生成报告
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.append("# 数据质量检查报告")
    lines.append(f"\n生成时间：{now_str}\n")

    lines.append("## 一、总体概况\n")
    lines.append(f"- 目标期刊总数：**25本**")
    lines.append(f"- 已有Excel数据期刊：**{len(results)}本**")
    lines.append(f"- 缺失期刊（需从CrossRef全量抓取）：**{len(missing_journals)}本**")
    lines.append(f"- Excel文件中文章总数：**{all_rows_count:,}条**\n")

    lines.append("## 二、已有Excel数据的期刊（逐本详情）\n")
    lines.append("| 期刊名称 | 文章数 | 时间范围 | 缺摘要 | 缺DOI | 缺作者 | DOI重复 | 标题重复 | 备注 |")
    lines.append("|---|---|---|---|---|---|---|---|---|")

    for journal_name in sorted(results.keys()):
        s = results[journal_name]
        year_range = f"{s['year_min']}–{s['year_max']}" if s["year_min"] else "未知"
        notes = []
        if s["hit_wos_limit"]:
            notes.append("⚠ 达WoS导出上限(1000条)")
        if s["gap_years"]:
            notes.append(f"缺{s['target_start']}–{s['year_min']-1}年数据")
        if s["missing_year"] > 0:
            notes.append(f"缺年份{s['missing_year']}条")
        note_str = "；".join(notes) if notes else "—"

        lines.append(
            f"| {journal_name} | {s['total']:,} | {year_range} | "
            f"{s['missing_abstract']} | {s['missing_doi']} | {s['missing_authors']} | "
            f"{s['doi_dups']} | {s['title_dups']} | {note_str} |"
        )

    lines.append("\n### 各期刊数据缺口详情\n")
    has_gap = False
    for journal_name in sorted(results.keys()):
        s = results[journal_name]
        issues = []
        if s["gap_years"]:
            issues.append(f"**年份缺口**：需补充 {s['target_start']}–{s['year_min']-1} 年共 {len(s['gap_years'])} 年的历史数据（将从CrossRef抓取）")
        if s["hit_wos_limit"]:
            issues.append("**达WoS导出上限**：该期刊在当前年份范围内文章数超过1000条，导出数据不完整，需CrossRef补全")
        if s["missing_abstract"] > 0:
            issues.append(f"**摘要缺失**：{s['missing_abstract']} 篇（将用CrossRef/DOI补全）")
        if s["missing_doi"] > 0:
            issues.append(f"**DOI缺失**：{s['missing_doi']} 篇（将按标题在CrossRef中查找）")
        if issues:
            has_gap = True
            lines.append(f"**{journal_name}**")
            for issue in issues:
                lines.append(f"- {issue}")
            lines.append("")

    if not has_gap:
        lines.append("所有已有期刊数据完整，无明显缺口。\n")

    lines.append("## 三、缺失期刊（需从CrossRef全量抓取）\n")
    lines.append("以下期刊没有Excel文件，将通过CrossRef API按ISSN全量抓取：\n")
    lines.append("| 期刊名称 | ISSN | 数据起始年 | 说明 |")
    lines.append("|---|---|---|---|")
    missing_info = {
        "Asian Population Studies": ("1744-1730", 2005, "2005年创刊"),
        "European Journal of Population": ("0168-6577", 2000, "正常创刊"),
        "Gender & Society": ("0891-2432", 2000, "正常创刊"),
        "Journal of Family Theory & Review": ("1756-2570", 2009, "2009年创刊"),
        "Sociology": ("0038-0385", 2000, "正常创刊"),
        "Work, Employment and Society": ("0950-0170", 2000, "正常创刊"),
        "Sociological Science": ("2330-6696", 2014, "2014年创刊"),
        "Socius": ("2378-0231", 2015, "2015年创刊"),
    }
    for j in sorted(missing_journals):
        info = missing_info.get(j, ("未知", TARGET_JOURNALS.get(j, 2000), ""))
        lines.append(f"| {j} | {info[0]} | {info[1]} | {info[2]} |")

    lines.append("\n## 四、数据问题汇总\n")

    total_missing_ab = sum(s["missing_abstract"] for s in results.values())
    total_missing_doi = sum(s["missing_doi"] for s in results.values())
    total_missing_year = sum(s["missing_year"] for s in results.values())
    total_doi_dups = sum(s["doi_dups"] for s in results.values())
    total_title_dups = sum(s["title_dups"] for s in results.values())
    journals_with_gap = [j for j, s in results.items() if s["gap_years"]]
    journals_hit_limit = [j for j, s in results.items() if s["hit_wos_limit"]]

    lines.append("| 问题类型 | 数量 |")
    lines.append("|---|---|")
    lines.append(f"| 缺摘要（总计） | {total_missing_ab} 篇 |")
    lines.append(f"| 缺DOI（总计） | {total_missing_doi} 篇 |")
    lines.append(f"| 缺年份（总计） | {total_missing_year} 篇 |")
    lines.append(f"| DOI重复（总计） | {total_doi_dups} 条 |")
    lines.append(f"| 标题重复（总计） | {total_title_dups} 条 |")
    lines.append(f"| 达WoS导出上限期刊 | {len(journals_hit_limit)} 本 |")
    lines.append(f"| 存在年份缺口期刊 | {len(journals_with_gap)} 本 |")
    lines.append(f"| 缺失期刊（无Excel） | {len(missing_journals)} 本 |")

    if journals_hit_limit:
        lines.append(f"\n达WoS导出上限的期刊：{', '.join(sorted(journals_hit_limit))}")
    if journals_with_gap:
        lines.append(f"\n存在年份缺口的期刊：{', '.join(sorted(journals_with_gap))}")

    lines.append("\n## 五、后续处理建议\n")
    lines.append("1. **Step 2（数据清洗）**：合并17个XLS文件，统一字段名（title/abstract/authors/journal/year/doi），按DOI去重，输出 `articles.json`")
    lines.append("2. **Step 3（CrossRef补全）**：")
    lines.append("   - 补全缺失摘要（有DOI者直接查CrossRef）")
    lines.append("   - 补全缺失DOI（按标题搜索CrossRef）")
    lines.append("   - 抓取历史缺口年份数据（按ISSN+年份范围查CrossRef）")
    lines.append("   - 全量抓取8本缺失期刊的数据")
    lines.append("3. **Step 4（自动更新）**：运行 `python update.py` 可定期从CrossRef获取最新文章")

    report_path = ROOT / "data_quality_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n报告已生成: {report_path}")
    print(f"总计: {len(results)} 本期刊, {all_rows_count:,} 条记录")
    print(f"缺失期刊: {len(missing_journals)} 本")
    print(f"缺摘要: {total_missing_ab}, 缺DOI: {total_missing_doi}, DOI重复: {total_doi_dups}")


if __name__ == "__main__":
    main()
