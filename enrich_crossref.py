"""
enrich_crossref.py — CrossRef API 数据补全脚本

分四个阶段：
  Phase 1: 有DOI但缺摘要 → 直接用DOI查CrossRef
  Phase 2: 无DOI → 用标题搜索CrossRef获取DOI（并顺便补摘要）
  Phase 3: 已有期刊补历史数据 → 按ISSN+年份范围抓取缺失年份
  Phase 4: 8本缺失期刊全量抓取 → 按ISSN全量分页抓取

用法：
  source venv/bin/activate
  python enrich_crossref.py                    # 全部阶段
  python enrich_crossref.py --phase 1          # 仅执行某阶段
  python enrich_crossref.py --phase 3,4        # 执行阶段3和4
  python enrich_crossref.py --phase 4 --journal "Asian Population Studies"  # 仅抓指定期刊
  python enrich_crossref.py --dry-run          # 仅显示计划，不执行
"""
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent
ARTICLES_JSON = ROOT / "articles.json"
DATA_JSON = ROOT / "data.json"
DATA_JS = ROOT / "data.js"
PROGRESS_FILE = ROOT / "enrich_progress.json"

MAILTO = "hwbruc@gmail.com"
SLEEP_SEC = 1.0
CROSSREF_BASE = "https://api.crossref.org"

# 25本期刊配置：标准名 → {issn, start_year}
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

# 8本缺失期刊（需全量抓取）
MISSING_JOURNALS = {
    "Asian Population Studies",
    "European Journal of Population",
    "Gender & Society",
    "Journal of Family Theory & Review",
    "Sociological Science",
    "Sociology",
    "Socius",
    "Work, Employment and Society",
}

# 已有Excel但年份不完整的期刊，记录其Excel最早年份
EXISTING_JOURNAL_GAPS = {
    "British Journal of Sociology": 2015,
    "British Journal of Sociology of Education": 2015,
    "Chinese Journal of Sociology": 2020,
    "Chinese Sociological Review": 2011,
    "Demographic Research": 2015,
    "Demography": 2015,
    "European Sociological Review": 2015,
    "Journal of Family Issues": 2018,
    "Journal of Marriage and Family": 2015,
    "Research in Social Stratification and Mobility": 2010,
    "Social Forces": 2015,
    "Social Science Research": 2016,
}


# ──────────────────────────────────────────────
# HTTP / CrossRef 工具函数
# ──────────────────────────────────────────────

def get_json(url, retries=3, timeout=30):
    """发送GET请求，返回解析后的JSON，失败时重试"""
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
                print(f"    [限速] 等待5秒后重试...")
                time.sleep(5)
            elif e.code == 404:
                return None
            else:
                print(f"    [HTTP {e.code}] {url[:80]}")
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    return None
        except (URLError, Exception) as e:
            print(f"    [请求失败] {e} — {url[:80]}")
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return None
    return None


def clean_abstract(text):
    """清理CrossRef返回的JATS XML标签"""
    if not text:
        return ""
    # 去除JATS标签
    text = re.sub(r"<jats:[^>]+>", "", text)
    text = re.sub(r"</jats:[^>]+>", "", text)
    # 去除其他XML/HTML标签
    text = re.sub(r"<[^>]+>", "", text)
    # 清理实体
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&apos;", "'")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_text(v):
    text = str(v or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def text_similarity(a, b):
    sa = set(normalize_text(a).split())
    sb = set(normalize_text(b).split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def parse_crossref_item(item, journal_name=None):
    """从CrossRef work item中提取文章信息"""
    title_list = item.get("title", [])
    title = title_list[0] if title_list else ""

    abstract = clean_abstract(item.get("abstract", ""))

    # 作者
    authors_list = []
    for a in item.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        if family and given:
            authors_list.append(f"{family}, {given}")
        elif family:
            authors_list.append(family)
    authors = "; ".join(authors_list)

    # 年份
    year = None
    pub_date = item.get("published") or item.get("published-print") or item.get("published-online")
    if pub_date:
        date_parts = pub_date.get("date-parts", [[]])
        if date_parts and date_parts[0]:
            year = date_parts[0][0]

    doi = item.get("DOI", "").strip()
    if doi:
        doi = re.sub(r"^https?://doi\.org/", "", doi)

    # 期刊名
    if not journal_name:
        container = item.get("container-title", [])
        journal_name = container[0] if container else ""

    return {
        "title": title,
        "abstract": abstract,
        "authors": authors,
        "journal": journal_name,
        "year": year,
        "doi": doi,
    }


# ──────────────────────────────────────────────
# 进度管理
# ──────────────────────────────────────────────

def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_progress(progress):
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def parse_selected_journals(journal_args):
    """解析 --journal 参数，支持多次传入或逗号分隔"""
    if not journal_args:
        return None

    selected = set()
    for raw in journal_args:
        for name in raw.split(","):
            name = name.strip()
            if name:
                selected.add(name)

    invalid = sorted(j for j in selected if j not in JOURNALS)
    if invalid:
        raise SystemExit(f"未知期刊: {', '.join(invalid)}")
    return selected


# ──────────────────────────────────────────────
# 主数据加载/保存
# ──────────────────────────────────────────────

def load_articles():
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        return json.load(f)


def save_articles(articles):
    # 按期刊+年份排序
    articles.sort(key=lambda x: (x.get("journal", ""), x.get("year") or 0))

    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

    # 同步更新 data.json + data.js
    legacy = []
    for a in articles:
        legacy.append({
            "Source Title": a.get("journal", ""),
            "Publication Year": a.get("year"),
            "Article Title": a.get("title", ""),
            "Author Full Names": a.get("authors", ""),
            "Abstract": a.get("abstract", ""),
            "DOI": a.get("doi", ""),
        })

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(legacy, f, ensure_ascii=False, indent=2)

    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write("const DATA = ")
        json.dump(legacy, f, ensure_ascii=False, indent=2)
        f.write(";\n")


def build_doi_index(articles):
    """构建DOI → 文章位置的索引"""
    return {
        a["doi"].strip().lower(): i
        for i, a in enumerate(articles)
        if a.get("doi")
    }


def build_title_index(articles):
    """构建 normalize(title)+journal+year → 位置 的索引"""
    idx = {}
    for i, a in enumerate(articles):
        t = normalize_text(a.get("title", ""))
        j = a.get("journal", "")
        y = str(a.get("year", ""))
        key = f"{t}|{j}|{y}"
        if key not in idx:
            idx[key] = i
    return idx


# ──────────────────────────────────────────────
# Phase 1: 有DOI但缺摘要 → 用DOI查CrossRef
# ──────────────────────────────────────────────

def phase1_enrich_abstracts(articles, dry_run=False):
    print("\n=== Phase 1: 补全缺失摘要（有DOI） ===")
    targets = [
        (i, a) for i, a in enumerate(articles)
        if a.get("doi") and not a.get("abstract")
    ]
    print(f"需要补摘要的文章：{len(targets)} 篇")

    if dry_run:
        return articles

    enriched = 0
    for idx, (i, art) in enumerate(targets):
        doi = art["doi"].strip()
        url = f"{CROSSREF_BASE}/works/{quote_plus(doi)}?mailto={MAILTO}"
        data = get_json(url)
        time.sleep(SLEEP_SEC)

        if data and data.get("status") == "ok":
            item = data["message"]
            abstract = clean_abstract(item.get("abstract", ""))
            if abstract:
                articles[i]["abstract"] = abstract
                enriched += 1

        if (idx + 1) % 50 == 0:
            print(f"  进度: {idx+1}/{len(targets)}，已补 {enriched} 篇")
            save_articles(articles)

    save_articles(articles)
    print(f"Phase 1 完成：补全 {enriched}/{len(targets)} 篇摘要")
    return articles


# ──────────────────────────────────────────────
# Phase 2: 无DOI → 按标题搜索CrossRef
# ──────────────────────────────────────────────

def phase2_find_dois(articles, dry_run=False):
    print("\n=== Phase 2: 补全缺失DOI（按标题搜索） ===")
    targets = [
        (i, a) for i, a in enumerate(articles)
        if not a.get("doi") and a.get("title")
    ]
    print(f"需要查找DOI的文章：{len(targets)} 篇")

    if dry_run:
        return articles

    found_doi = 0
    found_abstract = 0

    for idx, (i, art) in enumerate(targets):
        title = art["title"]
        journal = art.get("journal", "")
        year = art.get("year")

        # 去掉标题中的特殊字符再搜索（冒号、问号等会导致CrossRef 400错误）
        title_clean = re.sub(r"[^\w\s]", " ", title)
        title_clean = re.sub(r"\s+", " ", title_clean).strip()[:100]
        q = quote_plus(title_clean)

        # CrossRef不支持query.title与多个filter同时使用，用query代替
        # ISSN filter单独加，不加日期filter（靠相似度匹配过滤）
        url = f"{CROSSREF_BASE}/works?query={q}&rows=5&mailto={MAILTO}"
        if journal:
            issn = JOURNALS.get(journal, {}).get("issn")
            if issn:
                url += f"&filter=issn:{issn}"

        data = get_json(url)
        time.sleep(SLEEP_SEC)

        if data and data.get("status") == "ok":
            items = data["message"].get("items", [])
            for item in items:
                item_title = (item.get("title") or [""])[0]
                sim = text_similarity(title, item_title)
                if sim >= 0.85:
                    doi = item.get("DOI", "").strip()
                    doi = re.sub(r"^https?://doi\.org/", "", doi)
                    if doi:
                        articles[i]["doi"] = doi
                        found_doi += 1
                    abstract = clean_abstract(item.get("abstract", ""))
                    if abstract and not articles[i].get("abstract"):
                        articles[i]["abstract"] = abstract
                        found_abstract += 1
                    break

        if (idx + 1) % 50 == 0:
            print(f"  进度: {idx+1}/{len(targets)}，找到DOI {found_doi}，摘要 {found_abstract}")
            save_articles(articles)

    save_articles(articles)
    print(f"Phase 2 完成：找到DOI {found_doi}/{len(targets)} 篇，顺带补摘要 {found_abstract} 篇")
    return articles


# ──────────────────────────────────────────────
# CrossRef按ISSN分页抓取文章
# ──────────────────────────────────────────────

def fetch_by_issn(issn, from_year, until_year, journal_name, existing_dois):
    """
    从CrossRef按ISSN抓取指定年份范围的所有文章。
    策略：按年逐年抓取 + offset分页，避免cursor分页在某些查询下过早停止。
    existing_dois: set of lowercase DOI strings（用于去重）
    返回 (新文章列表, 是否发生API失败)。
    """
    new_articles = []
    page_size = 100
    total_new = 0
    had_api_failure = False

    # 先查询总数以便显示
    probe_url = (
        f"{CROSSREF_BASE}/works"
        f"?filter=issn:{issn},from-pub-date:{from_year}-01-01"
        f",until-pub-date:{until_year}-12-31,type:journal-article"
        f"&rows=0&mailto={MAILTO}"
    )
    probe = get_json(probe_url)
    time.sleep(SLEEP_SEC)
    if probe and probe.get("status") == "ok":
        total_results = probe["message"].get("total-results", "?")
    else:
        total_results = "?"
        had_api_failure = True
        print("    [警告] CrossRef 探测请求失败，本次不会标记为完成")
    print(f"    CrossRef报告共 {total_results} 条记录")

    for year in range(from_year, until_year + 1):
        filter_str = (
            f"issn:{issn},"
            f"from-pub-date:{year}-01-01,"
            f"until-pub-date:{year}-12-31,"
            f"type:journal-article"
        )
        offset = 0
        year_fetched = 0

        while True:
            url = (
                f"{CROSSREF_BASE}/works"
                f"?filter={filter_str}"
                f"&rows={page_size}"
                f"&offset={offset}"
                f"&mailto={MAILTO}"
                f"&select=DOI,title,abstract,author,published,published-print,published-online"
            )

            data = get_json(url)
            time.sleep(SLEEP_SEC)

            if not data:
                had_api_failure = True
                print(f"    [警告] {year}年请求失败，提前结束该年份抓取")
                break
            if data.get("status") != "ok":
                had_api_failure = True
                print(f"    [警告] {year}年返回状态异常，提前结束该年份抓取")
                break

            items = data["message"].get("items", [])
            if not items:
                break

            for item in items:
                art = parse_crossref_item(item, journal_name)
                if not art["title"]:
                    continue
                doi_norm = art["doi"].strip().lower() if art["doi"] else ""
                if doi_norm and doi_norm in existing_dois:
                    continue
                new_articles.append(art)
                total_new += 1
                if doi_norm:
                    existing_dois.add(doi_norm)

            year_fetched += len(items)
            offset += len(items)

            if len(items) < page_size:
                break  # 最后一页

        if year_fetched > 0 and (year % 5 == 0 or year == until_year):
            print(f"    {year}年: {year_fetched} 条 | 累计新增: {total_new}")

    return new_articles, had_api_failure


# ──────────────────────────────────────────────
# Phase 3: 补已有期刊的历史缺口年份
# ──────────────────────────────────────────────

def phase3_fill_gaps(articles, dry_run=False, progress=None, selected_journals=None):
    print("\n=== Phase 3: 补已有期刊历史缺口 ===")

    if progress is None:
        progress = {}
    p3 = progress.get("phase3", {})

    existing_dois = {
        a["doi"].strip().lower()
        for a in articles if a.get("doi")
    }

    total_new = 0

    for journal_name, excel_start_year in sorted(EXISTING_JOURNAL_GAPS.items()):
        if selected_journals and journal_name not in selected_journals:
            continue

        target_start = JOURNALS[journal_name]["start_year"]
        issn = JOURNALS[journal_name]["issn"]
        until_year = excel_start_year - 1

        if until_year < target_start:
            continue

        if p3.get(journal_name) == "done":
            print(f"  跳过（已完成）: {journal_name}")
            continue

        print(f"  {journal_name}: 抓取 {target_start}–{until_year} (ISSN {issn})")

        if dry_run:
            continue

        new_arts, had_api_failure = fetch_by_issn(
            issn, target_start, until_year, journal_name, existing_dois
        )
        print(f"    → 新增 {len(new_arts)} 篇")
        articles.extend(new_arts)
        total_new += len(new_arts)

        save_articles(articles)
        if had_api_failure:
            print(f"    [警告] {journal_name} 存在请求失败，未标记为 done，可稍后重跑")
            continue

        p3[journal_name] = "done"
        progress["phase3"] = p3
        save_progress(progress)

    if not dry_run:
        print(f"Phase 3 完成：共新增 {total_new} 篇历史文章")
    return articles, progress


# ──────────────────────────────────────────────
# Phase 4: 全量抓取8本缺失期刊
# ──────────────────────────────────────────────

def phase4_fetch_missing_journals(articles, dry_run=False, progress=None, selected_journals=None):
    print("\n=== Phase 4: 全量抓取缺失期刊 ===")

    if progress is None:
        progress = {}
    p4 = progress.get("phase4", {})

    existing_dois = {
        a["doi"].strip().lower()
        for a in articles if a.get("doi")
    }

    total_new = 0

    for journal_name in sorted(MISSING_JOURNALS):
        if selected_journals and journal_name not in selected_journals:
            continue

        config = JOURNALS[journal_name]
        issn = config["issn"]
        start_year = config["start_year"]
        current_year = datetime.now().year

        if p4.get(journal_name) == "done":
            print(f"  跳过（已完成）: {journal_name}")
            continue

        print(f"  {journal_name}: 全量抓取 {start_year}–{current_year} (ISSN {issn})")

        if dry_run:
            continue

        new_arts, had_api_failure = fetch_by_issn(
            issn, start_year, current_year, journal_name, existing_dois
        )
        print(f"    → 新增 {len(new_arts)} 篇")
        articles.extend(new_arts)
        total_new += len(new_arts)

        save_articles(articles)
        if had_api_failure:
            print(f"    [警告] {journal_name} 存在请求失败，未标记为 done，可稍后重跑")
            continue

        p4[journal_name] = "done"
        progress["phase4"] = p4
        save_progress(progress)

    if not dry_run:
        print(f"Phase 4 完成：共新增 {total_new} 篇文章")
    return articles, progress


# ──────────────────────────────────────────────
# 主函数
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="CrossRef API 数据补全脚本")
    parser.add_argument("--phase", type=str, default="1,2,3,4",
                        help="执行哪些阶段，逗号分隔，如 --phase 1,2 或 --phase 3")
    parser.add_argument("--journal", action="append",
                        help="仅处理指定期刊；可多次传入，或在一次参数中用逗号分隔")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅显示计划，不发送API请求，不写入文件")
    args = parser.parse_args()

    phases = [int(p.strip()) for p in args.phase.split(",")]
    selected_journals = parse_selected_journals(args.journal)
    dry_run = args.dry_run

    if dry_run:
        print("[DRY RUN 模式] 不会发送请求或写入文件\n")

    print(f"执行阶段: {phases}")
    if selected_journals:
        print(f"限定期刊: {', '.join(sorted(selected_journals))}")
    articles = load_articles()
    print(f"已加载 {len(articles):,} 条文章")

    progress = load_progress()

    if 1 in phases:
        articles = phase1_enrich_abstracts(articles, dry_run=dry_run)

    if 2 in phases:
        articles = phase2_find_dois(articles, dry_run=dry_run)

    if 3 in phases:
        articles, progress = phase3_fill_gaps(
            articles,
            dry_run=dry_run,
            progress=progress,
            selected_journals=selected_journals,
        )

    if 4 in phases:
        articles, progress = phase4_fetch_missing_journals(
            articles,
            dry_run=dry_run,
            progress=progress,
            selected_journals=selected_journals,
        )

    if not dry_run:
        save_articles(articles)
        print(f"\n最终数据库：{len(articles):,} 条文章")
        missing_ab = sum(1 for a in articles if not a.get("abstract"))
        missing_doi = sum(1 for a in articles if not a.get("doi"))
        print(f"缺摘要: {missing_ab}, 缺DOI: {missing_doi}")

    print("\n完成！")


if __name__ == "__main__":
    main()
