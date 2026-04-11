"""
update.py — 自动更新脚本

从CrossRef抓取25本期刊的最新文章，去重后追加到数据库。

用法：
  source venv/bin/activate
  python update.py              # 默认抓取最近30天
  python update.py --days 60    # 抓取最近60天
  python update.py --dry-run    # 仅检查，不写入

脚本会自动：
  1. 查询CrossRef获取指定天数内各期刊的新文章
  2. 按DOI去重（跳过已存在的文章）
  3. 新文章追加到 articles.json，同步更新 data.json 和 data.js
  4. 在 update_log.md 中追加更新记录
"""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent
ARTICLES_JSON = ROOT / "articles.json"
DATA_JSON = ROOT / "data.json"
DATA_JS = ROOT / "data.js"
UPDATE_LOG = ROOT / "update_log.md"

MAILTO = "hwbruc@gmail.com"
SLEEP_SEC = 1.0
CROSSREF_BASE = "https://api.crossref.org"

DERIVED_BUILDERS = [
    ("AI 索引", [sys.executable, "build_lit_db.py"]),
    ("文章 API", [sys.executable, "build_article_api.py"]),
    ("全文检索库", [sys.executable, "build_search_db.py"]),
    ("质量报告", [sys.executable, "check_quality.py"]),
]

# 25本期刊配置
JOURNALS = {
    "American Journal of Sociology":                {"issn": "0002-9602", "start_year": 2000},
    "American Sociological Review":                  {"issn": "0003-1224", "start_year": 2000},
    "Annual Review of Sociology":                    {"issn": "0360-0572", "start_year": 2000},
    "Asian Population Studies":                      {"issn": "1744-1730", "start_year": 2005},
    "British Journal of Sociology":                  {"issn": "0007-1315", "start_year": 2000},
    "British Journal of Sociology of Education":     {"issn": "0142-5692", "start_year": 2000},
    "Chinese Journal of Sociology":                  {"issn": "2057-150X", "start_year": 2015},
    "Chinese Sociological Review":                   {"issn": "2162-0555", "start_year": 2000},
    "Demographic Research":                          {"issn": "1435-9871", "start_year": 2000},
    "Demography":                                    {"issn": "0070-3370", "start_year": 2000},
    "European Journal of Population":                {"issn": "0168-6577", "start_year": 2000},
    "European Sociological Review":                  {"issn": "0266-7215", "start_year": 2000},
    "Gender & Society":                              {"issn": "0891-2432", "start_year": 2000},
    "Journal of Family Issues":                      {"issn": "0192-513X", "start_year": 2000},
    "Journal of Family Theory & Review":             {"issn": "1756-2570", "start_year": 2009},
    "Journal of Marriage and Family":                {"issn": "0022-2445", "start_year": 2000},
    "Population and Development Review":             {"issn": "0098-7921", "start_year": 2000},
    "Research in Social Stratification and Mobility": {"issn": "0276-5624", "start_year": 2000},
    "Social Forces":                                 {"issn": "0037-7732", "start_year": 2000},
    "Social Science Research":                       {"issn": "0049-089X", "start_year": 2000},
    "Sociological Science":                          {"issn": "2330-6696", "start_year": 2014},
    "Sociology":                                     {"issn": "0038-0385", "start_year": 2000},
    "Sociology of Education":                        {"issn": "0038-0407", "start_year": 2000},
    "Socius":                                        {"issn": "2378-0231", "start_year": 2015},
    "Work, Employment and Society":                  {"issn": "0950-0170", "start_year": 2000},
}


def get_json(url, retries=3, timeout=30):
    headers = {
        "User-Agent": f"SociologyLitDB/1.0 (mailto:{MAILTO})",
        "Accept": "application/json",
    }
    for attempt in range(retries):
        try:
            req = Request(url, headers=headers)
            with urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            if e.code == 429:
                print(f"  [限速] 等待5秒...")
                time.sleep(5)
            elif e.code == 404:
                return None
            else:
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    return None
        except Exception:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return None
    return None


def clean_abstract(text):
    if not text:
        return ""
    text = re.sub(r"<jats:[^>]+>", "", text)
    text = re.sub(r"</jats:[^>]+>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&apos;", "'")
    return re.sub(r"\s+", " ", text).strip()


def parse_crossref_item(item, journal_name):
    title_list = item.get("title", [])
    title = title_list[0] if title_list else ""

    abstract = clean_abstract(item.get("abstract", ""))

    authors_list = []
    for a in item.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        if family and given:
            authors_list.append(f"{family}, {given}")
        elif family:
            authors_list.append(family)
    authors = "; ".join(authors_list)

    year = None
    pub_date = item.get("published") or item.get("published-print") or item.get("published-online")
    if pub_date:
        date_parts = pub_date.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]

    doi = item.get("DOI", "").strip()
    doi = re.sub(r"^https?://doi\.org/", "", doi)

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "journal": journal_name,
        "year": year,
        "doi": doi,
    }


def fetch_recent_articles(journal_name, issn, from_date_str, dry_run=False):
    """抓取指定日期之后发布的文章"""
    new_articles = []
    cursor = "*"
    page_size = 100

    filter_str = (
        f"issn:{issn},"
        f"from-index-date:{from_date_str},"
        f"type:journal-article"
    )

    while True:
        url = (
            f"{CROSSREF_BASE}/works"
            f"?filter={filter_str}"
            f"&rows={page_size}"
            f"&cursor={quote_plus(cursor)}"
            f"&mailto={MAILTO}"
            f"&select=DOI,title,abstract,author,published,published-print,published-online"
        )

        if dry_run:
            # dry run 只抓第一页看看有多少
            url_check = url.replace(f"&rows={page_size}", "&rows=0")
            data = get_json(url_check)
            time.sleep(SLEEP_SEC)
            if data and data.get("status") == "ok":
                total = data["message"].get("total-results", 0)
                return [], total
            return [], 0

        data = get_json(url)
        time.sleep(SLEEP_SEC)

        if not data or data.get("status") != "ok":
            break

        msg = data["message"]
        items = msg.get("items", [])
        next_cursor = msg.get("next-cursor")

        for item in items:
            art = parse_crossref_item(item, journal_name)
            if art["title"]:
                new_articles.append(art)

        if not items or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    return new_articles, len(new_articles)


def load_articles():
    if not ARTICLES_JSON.exists():
        return []
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        return json.load(f)


def save_articles(articles):
    articles.sort(key=lambda x: (x.get("journal", ""), x.get("year") or 0))

    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    legacy = [{
        "Source Title": a.get("journal", ""),
        "Publication Year": a.get("year"),
        "Article Title": a.get("title", ""),
        "Author Full Names": a.get("authors", ""),
        "Abstract": a.get("abstract", ""),
        "DOI": a.get("doi", ""),
    } for a in articles]

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(legacy, f, ensure_ascii=False, indent=2)

    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write("const DATA = ")
        json.dump(legacy, f, ensure_ascii=False, indent=2)
        f.write(";\n")


def append_update_log(run_date, days, journal_results, total_new, total_after):
    lines = []
    if UPDATE_LOG.exists():
        content = UPDATE_LOG.read_text(encoding="utf-8")
    else:
        content = "# 更新日志\n\n"

    entry = [f"## {run_date}（最近{days}天）\n"]
    entry.append(f"- 新增文章总数：**{total_new}**")
    entry.append(f"- 数据库总文章数：**{total_after:,}**\n")

    if journal_results:
        entry.append("| 期刊 | 新增 |")
        entry.append("|---|---|")
        for journal, count in sorted(journal_results.items()):
            if count > 0:
                entry.append(f"| {journal} | {count} |")
        entry.append("")

    new_entry = "\n".join(entry) + "\n"

    # 插入到第一个 ## 之前（最新在最上面）
    if "## " in content:
        insert_pos = content.index("## ")
        updated = content[:insert_pos] + new_entry + content[insert_pos:]
    else:
        updated = content + new_entry

    UPDATE_LOG.write_text(updated, encoding="utf-8")


def run_derived_builds():
    print("\n重建派生文件：")
    for label, command in DERIVED_BUILDERS:
        print(f"  → {label}")
        try:
            subprocess.run(command, cwd=ROOT, check=True)
        except subprocess.CalledProcessError as error:
            print(f"    [警告] {label} 失败（退出码 {error.returncode}）")
        except Exception as error:
            print(f"    [警告] {label} 失败：{error}")


def main():
    parser = argparse.ArgumentParser(description="自动更新文献数据库")
    parser.add_argument("--days", type=int, default=30,
                        help="抓取最近N天的新文章（默认30）")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅检查可用新文章数，不写入数据库")
    parser.add_argument("--skip-derived", action="store_true",
                        help="跳过 lit_db / API / 搜索库 / 质量报告的重建")
    args = parser.parse_args()

    run_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    from_date = datetime.now() - timedelta(days=args.days)
    from_date_str = from_date.strftime("%Y-%m-%d")

    print(f"更新日期：{run_date}")
    print(f"抓取范围：最近 {args.days} 天（{from_date_str} 之后）")
    if args.dry_run:
        print("[DRY RUN] 仅检查，不写入\n")

    articles = load_articles()
    print(f"当前数据库：{len(articles):,} 条文章")

    # 构建现有DOI集合（去重用）
    existing_dois = {
        a["doi"].strip().lower()
        for a in articles if a.get("doi")
    }

    journal_results = {}
    all_new = []

    for journal_name, config in sorted(JOURNALS.items()):
        issn = config["issn"]
        new_arts, count = fetch_recent_articles(
            journal_name, issn, from_date_str, dry_run=args.dry_run
        )

        if args.dry_run:
            if count > 0:
                print(f"  {journal_name}: 约 {count} 篇可用")
            journal_results[journal_name] = count
            continue

        # 去重
        filtered = []
        for art in new_arts:
            doi_norm = art["doi"].strip().lower() if art["doi"] else ""
            if doi_norm and doi_norm in existing_dois:
                continue
            filtered.append(art)
            if doi_norm:
                existing_dois.add(doi_norm)

        journal_results[journal_name] = len(filtered)
        all_new.extend(filtered)

        if filtered:
            print(f"  {journal_name}: 新增 {len(filtered)} 篇")

    if args.dry_run:
        total_potential = sum(journal_results.values())
        print(f"\n[DRY RUN] 预计可新增约 {total_potential} 篇文章")
        return

    if all_new:
        articles.extend(all_new)
        save_articles(articles)
        total_new = len(all_new)
        print(f"\n共新增 {total_new} 篇，数据库现有 {len(articles):,} 条")
        append_update_log(run_date, args.days, journal_results, total_new, len(articles))
        print(f"已更新 update_log.md")
        if not args.skip_derived:
            run_derived_builds()
    else:
        total_new = 0
        print(f"\n没有新文章")
        append_update_log(run_date, args.days, {}, 0, len(articles))

    print("完成！")


if __name__ == "__main__":
    main()
