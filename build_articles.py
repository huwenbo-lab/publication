"""
build_articles.py — 数据清洗与合并脚本
读取所有 .xls 文件，统一字段名，去重后输出：
  - articles.json（新格式：title/abstract/authors/journal/year/doi）
  - data.json + data.js（旧格式，保持 index.html 兼容性）
"""
import json
import re
from pathlib import Path

import xlrd

ROOT = Path(__file__).resolve().parent
RAW_DATA = ROOT / "raw_data"   # XLS 原始文件目录

# 文件名到标准期刊名映射
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

# 数据起始年（早于此年份的记录过滤掉，Annual Review of Sociology从2000起）
JOURNAL_START_YEAR = {
    "American Journal of Sociology": 2000,
    "American Sociological Review": 2000,
    "Annual Review of Sociology": 2000,
    "British Journal of Sociology": 2000,
    "British Journal of Sociology of Education": 2000,
    "Chinese Journal of Sociology": 2015,
    "Chinese Sociological Review": 2000,
    "Demographic Research": 2000,
    "Demography": 2000,
    "European Sociological Review": 2000,
    "Journal of Family Issues": 2000,
    "Journal of Marriage and Family": 2000,
    "Population and Development Review": 2000,
    "Research in Social Stratification and Mobility": 2000,
    "Social Forces": 2000,
    "Social Science Research": 2000,
    "Sociology of Education": 2000,
}


def normalize_text(v):
    text = str(v or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def get_field(row, *keys):
    for k in keys:
        v = row.get(k, "")
        if v and str(v).strip() and str(v).strip() not in ("nan", "None"):
            return str(v).strip()
    return ""


def count_populated(article):
    """统计记录的字段填充数，用于去重时选择最完整的记录"""
    score = 0
    for field in ("title", "abstract", "authors", "year", "doi"):
        if article.get(field):
            score += 1
    # 摘要更长权重更高
    ab = article.get("abstract", "")
    if ab:
        score += min(len(ab) / 500, 2)
    return score


def read_xls_to_articles(filepath, journal_name):
    """读取XLS文件，转换为统一格式的文章列表"""
    wb = xlrd.open_workbook(filepath)
    sh = wb.sheet_by_index(0)
    headers = [str(sh.cell_value(0, i)).strip() for i in range(sh.ncols)]

    articles = []
    start_year = JOURNAL_START_YEAR.get(journal_name, 2000)

    for r in range(1, sh.nrows):
        row = {headers[i]: sh.cell_value(r, i) for i in range(sh.ncols)}

        title = get_field(row, "Article Title")
        if not title:
            continue  # 跳过无标题记录

        abstract = get_field(row, "Abstract")
        authors = get_field(row, "Author Full Names", "Authors")
        doi = get_field(row, "DOI")

        # 年份处理
        year_raw = row.get("Publication Year", "")
        try:
            year = int(float(str(year_raw))) if year_raw else None
        except (ValueError, TypeError):
            year = None

        # 过滤早于起始年的记录
        if year and year < start_year:
            continue

        # DOI标准化（去掉URL前缀）
        if doi:
            doi = re.sub(r"^https?://doi\.org/", "", doi).strip()

        articles.append({
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "journal": journal_name,
            "year": year,
            "doi": doi,
        })

    return articles


def deduplicate(articles):
    """
    去重：优先按DOI，其次按标题+期刊+年份。
    保留字段最完整（得分最高）的记录。
    """
    # 按DOI分组
    doi_groups = {}
    no_doi = []

    for art in articles:
        doi = art.get("doi", "").strip().lower()
        if doi:
            if doi not in doi_groups:
                doi_groups[doi] = []
            doi_groups[doi].append(art)
        else:
            no_doi.append(art)

    result = []

    # DOI分组 → 选最完整记录
    for doi, group in doi_groups.items():
        best = max(group, key=count_populated)
        result.append(best)

    # 无DOI记录 → 按标题+期刊+年份去重
    title_groups = {}
    for art in no_doi:
        title_norm = normalize_text(art.get("title", ""))
        journal = art.get("journal", "")
        year = str(art.get("year", ""))
        key = f"{title_norm}|{journal}|{year}"
        if key not in title_groups:
            title_groups[key] = []
        title_groups[key].append(art)

    for key, group in title_groups.items():
        best = max(group, key=count_populated)
        result.append(best)

    return result


def to_legacy_format(article):
    """转换为 index.html 使用的旧格式字段名"""
    return {
        "Source Title": article.get("journal", ""),
        "Publication Year": article.get("year"),
        "Article Title": article.get("title", ""),
        "Author Full Names": article.get("authors", ""),
        "Abstract": article.get("abstract", ""),
        "DOI": article.get("doi", ""),
    }


def main():
    print("开始清洗和合并数据...")

    all_articles = []
    for filename, journal_name in sorted(FILENAME_TO_JOURNAL.items()):
        filepath = RAW_DATA / filename
        if not filepath.exists():
            print(f"  跳过（文件不存在）: {filename}")
            continue
        print(f"  读取: {filename}")
        articles = read_xls_to_articles(str(filepath), journal_name)
        print(f"    → {len(articles)} 条（过滤后）")
        all_articles.extend(articles)

    print(f"\n合并后共 {len(all_articles):,} 条，开始去重...")
    deduped = deduplicate(all_articles)
    print(f"去重后共 {len(deduped):,} 条")

    # 按期刊+年份排序
    deduped.sort(key=lambda x: (x.get("journal", ""), x.get("year") or 0))

    # 写 articles.json
    out_articles = ROOT / "articles.json"
    with open(out_articles, "w", encoding="utf-8") as f:
        json.dump(deduped, f, ensure_ascii=False, indent=2)
    print(f"已写入: {out_articles} ({len(deduped):,} 条)")

    # 写 data.json（旧格式）
    legacy = [to_legacy_format(a) for a in deduped]
    out_data_json = ROOT / "data.json"
    with open(out_data_json, "w", encoding="utf-8") as f:
        json.dump(legacy, f, ensure_ascii=False, indent=2)
    print(f"已写入: {out_data_json} ({len(legacy):,} 条)")

    # 写 data.js
    out_data_js = ROOT / "data.js"
    with open(out_data_js, "w", encoding="utf-8") as f:
        f.write("const DATA = ")
        json.dump(legacy, f, ensure_ascii=False, indent=2)
        f.write(";\n")
    print(f"已写入: {out_data_js}")

    # 统计
    from collections import Counter
    journal_counts = Counter(a["journal"] for a in deduped)
    print("\n各期刊文章数：")
    for j in sorted(journal_counts):
        print(f"  {j}: {journal_counts[j]}")

    missing_abstract = sum(1 for a in deduped if not a.get("abstract"))
    missing_doi = sum(1 for a in deduped if not a.get("doi"))
    print(f"\n缺摘要: {missing_abstract}, 缺DOI: {missing_doi}")
    print("\n完成！")


if __name__ == "__main__":
    main()
