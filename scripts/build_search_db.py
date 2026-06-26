"""
build_search_db.py — 构建 SQLite FTS5 全文检索数据库
读取 articles.json，建立可搜索的 literature.db

使用方法：
    python scripts/build_search_db.py          # 构建索引
    python scripts/build_search_db.py --search "education inequality China"
    python scripts/build_search_db.py --search "marriage fertility" --limit 10
    python scripts/build_search_db.py --search "stratification" --journal "American Journal of Sociology"
    python scripts/build_search_db.py --search "labor market" --year-from 2015 --year-to 2023
"""

import json
import sqlite3
import argparse
import re
import unicodedata

from _paths import ROOT

DB_PATH = ROOT / "literature.db"
ARTICLES_PATH = ROOT / "articles.json"


def strip_diacritics(text):
    normalized = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def normalize_name_part(text):
    text = strip_diacritics(text).lower()
    text = re.sub(r"[^a-z0-9\s-]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def initials_from_given(given):
    parts = [part for part in re.split(r"[\s-]+", normalize_name_part(given)) if part]
    return "".join(part[0] for part in parts)


def build_author_search_text(authors_text):
    """为作者检索生成保守变体，处理“Smith, John”和“John Smith”等顺序差异。"""
    variants = set()
    for item in str(authors_text or "").split(";"):
        raw = item.strip()
        if not raw:
            continue
        variants.add(raw)
        if "," in raw:
            family, given = [part.strip() for part in raw.split(",", 1)]
        else:
            parts = raw.split()
            if len(parts) >= 2:
                given = " ".join(parts[:-1])
                family = parts[-1]
            else:
                given = ""
                family = raw
        initials = initials_from_given(given)
        variants.update({
            f"{given} {family}".strip(),
            f"{family} {given}".strip(),
            f"{family}, {initials}".strip().strip(","),
            f"{initials} {family}".strip(),
        })
    normalized = {normalize_name_part(variant) for variant in variants if normalize_name_part(variant)}
    return " ".join(sorted(variants | normalized))


# ─────────────────────────────────────────────
# 构建索引
# ─────────────────────────────────────────────

def build(verbose=True):
    """从 articles.json 构建 SQLite FTS5 全文检索数据库"""
    if not ARTICLES_PATH.exists():
        print(f"错误：找不到 {ARTICLES_PATH}")
        return

    with open(ARTICLES_PATH, encoding="utf-8") as f:
        articles = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 删除旧表
    cur.execute("DROP TABLE IF EXISTS articles")
    cur.execute("DROP TABLE IF EXISTS articles_meta")

    # FTS5 虚拟表：
    # - title / abstract / authors 保留原始展示字段
    # - author_search / journal_search / year_search 用于科研检索模式
    # - journal / year / doi 仅存储展示和过滤字段
    cur.execute("""
        CREATE VIRTUAL TABLE articles USING fts5(
            title,
            abstract,
            authors,
            author_search,
            journal_search,
            year_search,
            journal    UNINDEXED,
            year       UNINDEXED,
            doi        UNINDEXED,
            tokenize   = 'unicode61 remove_diacritics 2'
        )
    """)

    # 元数据表（用于按期刊/年份过滤，不参与全文索引）
    cur.execute("""
        CREATE TABLE articles_meta (
            rowid   INTEGER PRIMARY KEY,
            journal TEXT,
            year    INTEGER,
            doi     TEXT
        )
    """)
    cur.execute("CREATE INDEX idx_meta_journal ON articles_meta(journal)")
    cur.execute("CREATE INDEX idx_meta_year    ON articles_meta(year)")

    # 插入数据
    rows = []
    for a in articles:
        journal = (a.get("journal") or "").strip()
        year = str(a.get("year") or "")
        authors = (a.get("authors") or "").strip()
        rows.append((
            (a.get("title")    or "").strip(),
            (a.get("abstract") or "").strip(),
            authors,
            build_author_search_text(authors),
            normalize_name_part(journal),
            year,
            journal,
            year,
            (a.get("doi")      or "").strip(),
        ))

    cur.executemany(
        """
        INSERT INTO articles(
            title, abstract, authors, author_search, journal_search, year_search,
            journal, year, doi
        ) VALUES (?,?,?,?,?,?,?,?,?)
        """,
        rows
    )

    # 同步写入 meta 表（rowid 与 FTS 表对应）
    cur.execute("""
        INSERT INTO articles_meta(rowid, journal, year, doi)
        SELECT rowid, journal,
               CAST(year AS INTEGER),
               doi
        FROM articles
    """)

    conn.commit()
    conn.close()

    db_size_mb = DB_PATH.stat().st_size / 1024 / 1024
    if verbose:
        print(f"✓ 已建索引：{len(rows):,} 篇文章 → {DB_PATH.name} ({db_size_mb:.1f} MB)")


# ─────────────────────────────────────────────
# 搜索
# ─────────────────────────────────────────────

def search(query, limit=20, journal=None, year_from=None, year_to=None):
    """
    全文检索，返回 (title, journal, year, doi, abstract_snippet) 列表

    query    — 搜索词，支持 AND/OR/NOT/短语（同 SQLite FTS5 语法）
    limit    — 最多返回条数
    journal  — 按期刊名过滤（精确匹配）
    year_from/year_to — 按年份范围过滤
    """
    if not DB_PATH.exists():
        print("索引不存在，请先运行：python scripts/build_search_db.py")
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 构建过滤条件
    filters = []
    params = [query]
    if journal:
        filters.append("m.journal = ?")
        params.append(journal)
    if year_from:
        filters.append("m.year >= ?")
        params.append(int(year_from))
    if year_to:
        filters.append("m.year <= ?")
        params.append(int(year_to))

    where_extra = ("AND " + " AND ".join(filters)) if filters else ""
    params.append(limit)

    sql = f"""
        SELECT a.title,
               a.journal,
               a.year,
               a.doi,
               snippet(articles, 1, '[', ']', '...', 32) AS abstract_snippet,
               a.authors
        FROM articles a
        JOIN articles_meta m ON m.rowid = a.rowid
        WHERE articles MATCH ?
          {where_extra}
        ORDER BY rank
        LIMIT ?
    """

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def print_results(results, query):
    """格式化打印搜索结果"""
    if not results:
        print(f'未找到与 "{query}" 相关的文章。')
        return

    print(f'\n搜索："{query}"  共 {len(results)} 条结果\n')
    print("─" * 80)
    for i, r in enumerate(results, 1):
        print(f"[{i}] {r['title']}")
        print(f"    {r['journal']}  {r['year']}  DOI: {r['doi'] or '—'}")
        if r.get("abstract_snippet"):
            print(f"    摘要: {r['abstract_snippet']}")
        print()


# ─────────────────────────────────────────────
# 命令行入口
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="构建或查询文献全文检索数据库",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python scripts/build_search_db.py
  python scripts/build_search_db.py --search "education inequality"
  python scripts/build_search_db.py --search "marriage fertility" --limit 10
  python scripts/build_search_db.py --search "stratification" --journal "American Journal of Sociology"
  python scripts/build_search_db.py --search "labor market" --year-from 2015 --year-to 2023
        """
    )
    parser.add_argument("--search",    metavar="QUERY",   help="搜索关键词")
    parser.add_argument("--limit",     type=int, default=20, metavar="N", help="最多返回条数（默认 20）")
    parser.add_argument("--journal",   metavar="NAME",    help="按期刊名过滤")
    parser.add_argument("--year-from", type=int, metavar="YEAR", help="起始年份")
    parser.add_argument("--year-to",   type=int, metavar="YEAR", help="截止年份")
    parser.add_argument("--rebuild",   action="store_true", help="强制重建索引（不搜索）")

    args = parser.parse_args()

    # 仅构建 or 强制重建
    if args.rebuild or not args.search:
        build()
        return

    # 搜索前若索引不存在自动构建
    if not DB_PATH.exists():
        print("索引不存在，正在自动构建...")
        build()

    results = search(
        query=args.search,
        limit=args.limit,
        journal=args.journal,
        year_from=args.year_from,
        year_to=args.year_to,
    )
    print_results(results, args.search)


if __name__ == "__main__":
    main()
