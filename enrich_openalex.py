"""
enrich_openalex.py — 用 OpenAlex + Semantic Scholar 补全缺失摘要

背景：CrossRef 对早期文章的摘要覆盖不完整（尤其 2000-2014 年），
OpenAlex 能额外覆盖约 40% 的缺失，Semantic Scholar 再补约 10%。

分两轮：
  Round 1: OpenAlex（免费、无限速、命中率高）
  Round 2: Semantic Scholar（对 OpenAlex 未命中的文章二次尝试）

用法：
  python enrich_openalex.py                # 执行全部
  python enrich_openalex.py --round 1      # 仅 OpenAlex
  python enrich_openalex.py --round 2      # 仅 Semantic Scholar
  python enrich_openalex.py --dry-run      # 仅统计，不写入
  python enrich_openalex.py --skip-reviews # 跳过疑似书评
"""

import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(__file__).resolve().parent
ARTICLES_JSON = ROOT / "articles.json"
DATA_JSON = ROOT / "data.json"
DATA_JS = ROOT / "data.js"
PROGRESS_FILE = ROOT / "openalex_progress.json"

MAILTO = "hwbruc@gmail.com"

# 书评/编辑类文章标题关键词（这些文章通常没有摘要）
REVIEW_KEYWORDS = [
    "book review", "review of ", "reviewed by", "book notice",
    "review essay", "commentary on", "reply to", "response to",
    "erratum", "corrigendum", "correction to", "retraction",
    "editor's note", "editorial introduction", "editorial:",
    "foreword", "introduction to the special", "in memoriam",
    "obituary", "books received", "notes on contributors",
]


# ──────────────────────────────────────────────
# 通用工具
# ──────────────────────────────────────────────

def is_likely_review(title):
    """判断标题是否像书评/勘误/编辑说明"""
    t = (title or "").lower()
    return any(kw in t for kw in REVIEW_KEYWORDS)


def clean_abstract(text):
    """清理 HTML/JATS 标签"""
    if not text:
        return ""
    text = re.sub(r"<jats:[^>]+>", "", text)
    text = re.sub(r"</jats:[^>]+>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&apos;", "'")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_json(url, retries=3, timeout=15):
    """发送 GET 请求，返回 JSON，失败时重试"""
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
            if e.code == 404:
                return None
            if e.code == 429:
                wait = 5 * (attempt + 1)
                print(f"    [限速] 等待 {wait}s...")
                time.sleep(wait)
            else:
                if attempt < retries - 1:
                    time.sleep(2)
                else:
                    return None
        except (URLError, Exception) as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                return None
    return None


# ──────────────────────────────────────────────
# 数据加载/保存
# ──────────────────────────────────────────────

def load_articles():
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        return json.load(f)


def save_articles(articles):
    articles.sort(key=lambda x: (x.get("journal", ""), x.get("year") or 0))

    with open(ARTICLES_JSON, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

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


def load_progress():
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"round1_done": set(), "round2_done": set()}


def save_progress(progress):
    serializable = {
        "round1_done": list(progress.get("round1_done", set())),
        "round2_done": list(progress.get("round2_done", set())),
    }
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f)


# ──────────────────────────────────────────────
# OpenAlex 摘要重建
# ──────────────────────────────────────────────

def reconstruct_abstract(inverted_index):
    """
    OpenAlex 用倒排索引存摘要：{"word": [pos1, pos2, ...], ...}
    需要重建为正常文本。
    """
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    words = {}
    for word, positions in inverted_index.items():
        if isinstance(positions, list):
            for pos in positions:
                words[pos] = word
    if not words:
        return ""
    return " ".join(words[i] for i in sorted(words))


# ──────────────────────────────────────────────
# Round 1: OpenAlex
# ──────────────────────────────────────────────

def round1_openalex(articles, targets, dry_run=False, progress=None):
    """用 OpenAlex API 补摘要（按 DOI 查询）"""
    print("\n" + "=" * 60)
    print("Round 1: OpenAlex API 补全摘要")
    print("=" * 60)

    done_dois = set(progress.get("round1_done", []))

    # 过滤已完成的
    todo = [(i, a) for i, a in targets if a["doi"].strip().lower() not in done_dois]
    print(f"  总目标: {len(targets)} 篇")
    print(f"  已完成: {len(done_dois)} 篇")
    print(f"  本次待查: {len(todo)} 篇")

    if dry_run:
        return 0

    enriched = 0
    failed = 0
    batch_size = 50  # OpenAlex 支持批量查询，每次最多 50 个

    # 逐批查询（OpenAlex 支持用 | 分隔多个 DOI filter）
    for batch_start in range(0, len(todo), batch_size):
        batch = todo[batch_start:batch_start + batch_size]
        dois_in_batch = [a["doi"].strip() for _, a in batch]

        # 用 filter 批量查询
        doi_filter = "|".join(f"https://doi.org/{d}" for d in dois_in_batch)
        url = (
            f"https://api.openalex.org/works"
            f"?filter=doi:{quote(doi_filter, safe='')}"
            f"&per_page={batch_size}"
            f"&select=doi,abstract_inverted_index"
            f"&mailto={MAILTO}"
        )

        data = get_json(url, timeout=30)
        time.sleep(0.2)

        if not data or "results" not in data:
            # 批量失败，逐个重试
            for idx, art in batch:
                doi = art["doi"].strip()
                single_url = (
                    f"https://api.openalex.org/works/https://doi.org/{doi}"
                    f"?select=doi,abstract_inverted_index&mailto={MAILTO}"
                )
                single_data = get_json(single_url)
                time.sleep(0.2)

                doi_lower = doi.lower()
                if single_data:
                    ab = reconstruct_abstract(single_data.get("abstract_inverted_index"))
                    ab = clean_abstract(ab)
                    if ab and len(ab) > 30:
                        articles[idx]["abstract"] = ab
                        enriched += 1

                done_dois.add(doi_lower)
            progress["round1_done"] = done_dois
        else:
            # 批量成功：建立 DOI → abstract 的映射
            results_map = {}
            for r in data.get("results", []):
                rdoi = (r.get("doi") or "").replace("https://doi.org/", "").strip().lower()
                if rdoi:
                    ab = reconstruct_abstract(r.get("abstract_inverted_index"))
                    ab = clean_abstract(ab)
                    if ab and len(ab) > 30:
                        results_map[rdoi] = ab

            for idx, art in batch:
                doi_lower = art["doi"].strip().lower()
                if doi_lower in results_map:
                    articles[idx]["abstract"] = results_map[doi_lower]
                    enriched += 1
                done_dois.add(doi_lower)

            progress["round1_done"] = done_dois

        # 定期保存
        processed = batch_start + len(batch)
        if processed % 500 == 0 or processed == len(todo):
            save_progress(progress)
            save_articles(articles)
            pct = processed / len(todo) * 100
            print(f"  进度: {processed}/{len(todo)} ({pct:.0f}%) | 已补: {enriched}")

    save_progress(progress)
    save_articles(articles)
    print(f"\nRound 1 完成: OpenAlex 补全 {enriched}/{len(todo)} 篇摘要")
    return enriched


# ──────────────────────────────────────────────
# Round 2: Semantic Scholar
# ──────────────────────────────────────────────

def round2_semantic_scholar(articles, targets, dry_run=False, progress=None):
    """对 OpenAlex 未命中的文章，用 Semantic Scholar 二次尝试"""
    print("\n" + "=" * 60)
    print("Round 2: Semantic Scholar API 补全摘要")
    print("=" * 60)

    # 只处理 Round 1 之后仍缺摘要的
    still_missing = [(i, a) for i, a in targets if not articles[i].get("abstract", "").strip()]
    done_dois = set(progress.get("round2_done", []))

    todo = [(i, a) for i, a in still_missing if a["doi"].strip().lower() not in done_dois]
    print(f"  Round 1 后仍缺摘要: {len(still_missing)} 篇")
    print(f"  已完成: {len(done_dois)} 篇")
    print(f"  本次待查: {len(todo)} 篇")

    if dry_run:
        return 0

    enriched = 0

    # Semantic Scholar 支持批量查询 (POST /paper/batch)，每次最多 500 个
    batch_size = 100  # 保守一些

    for batch_start in range(0, len(todo), batch_size):
        batch = todo[batch_start:batch_start + batch_size]
        ids = [f"DOI:{a['doi'].strip()}" for _, a in batch]

        url = "https://api.semanticscholar.org/graph/v1/paper/batch"
        payload = json.dumps({"ids": ids}).encode("utf-8")

        headers = {
            "User-Agent": f"SociologyLitDB/1.0 (mailto:{MAILTO})",
            "Content-Type": "application/json",
        }

        try:
            req = Request(url + "?fields=externalIds,abstract", data=payload, headers=headers, method="POST")
            with urlopen(req, timeout=30) as resp:
                results = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"    [S2 批量请求失败] {e}")
            results = [None] * len(batch)
            time.sleep(3)

        time.sleep(1)

        for (idx, art), result in zip(batch, results):
            doi_lower = art["doi"].strip().lower()
            if result and result.get("abstract"):
                ab = clean_abstract(result["abstract"])
                if ab and len(ab) > 30:
                    articles[idx]["abstract"] = ab
                    enriched += 1
            done_dois.add(doi_lower)

        progress["round2_done"] = done_dois

        processed = batch_start + len(batch)
        if processed % 500 == 0 or processed == len(todo):
            save_progress(progress)
            save_articles(articles)
            pct = processed / len(todo) * 100
            print(f"  进度: {processed}/{len(todo)} ({pct:.0f}%) | 已补: {enriched}")

    save_progress(progress)
    save_articles(articles)
    print(f"\nRound 2 完成: Semantic Scholar 补全 {enriched}/{len(todo)} 篇摘要")
    return enriched


# ──────────────────────────────────────────────
# 主函数
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="用 OpenAlex + Semantic Scholar 补全缺失摘要",
        epilog="示例：python enrich_openalex.py --round 1 --skip-reviews"
    )
    parser.add_argument("--round", type=str, default="1,2",
                        help="执行哪几轮（1=OpenAlex, 2=Semantic Scholar），默认 1,2")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅统计，不发送请求、不写入文件")
    parser.add_argument("--skip-reviews", action="store_true",
                        help="跳过疑似书评/编辑说明类文章（这些文章通常不存在摘要）")
    parser.add_argument("--reset", action="store_true",
                        help="清除进度记录，从头开始")
    args = parser.parse_args()

    rounds = [int(r.strip()) for r in args.round.split(",")]
    dry_run = args.dry_run
    skip_reviews = args.skip_reviews

    if args.reset and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        print("已清除进度记录。\n")

    if dry_run:
        print("[DRY RUN 模式]\n")

    # 加载数据
    articles = load_articles()
    print(f"文章总数: {len(articles):,}")

    # 找出所有有 DOI 但缺摘要的文章
    targets = []
    skipped_reviews = 0
    for i, a in enumerate(articles):
        if a.get("doi", "").strip() and not a.get("abstract", "").strip():
            if skip_reviews and is_likely_review(a.get("title", "")):
                skipped_reviews += 1
                continue
            targets.append((i, a))

    print(f"有 DOI 但缺摘要: {len(targets) + skipped_reviews:,} 篇")
    if skip_reviews:
        print(f"  跳过疑似书评: {skipped_reviews:,} 篇")
    print(f"  实际处理目标: {len(targets):,} 篇")

    progress = load_progress() if not args.reset else {"round1_done": set(), "round2_done": set()}
    # 把 list 转回 set
    progress["round1_done"] = set(progress.get("round1_done", []))
    progress["round2_done"] = set(progress.get("round2_done", []))

    total_enriched = 0

    if 1 in rounds:
        n = round1_openalex(articles, targets, dry_run=dry_run, progress=progress)
        total_enriched += n

    if 2 in rounds:
        n = round2_semantic_scholar(articles, targets, dry_run=dry_run, progress=progress)
        total_enriched += n

    # 最终统计
    if not dry_run:
        save_articles(articles)
        missing_after = sum(1 for a in articles if not a.get("abstract", "").strip())
        print(f"\n{'=' * 60}")
        print(f"补全完成")
        print(f"  本次补全: {total_enriched} 篇")
        print(f"  剩余缺摘要: {missing_after:,} 篇 ({missing_after/len(articles)*100:.1f}%)")
        print(f"{'=' * 60}")

    # 清理进度文件
    if not dry_run and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        print("已清理进度文件。")

    print("\n完成！")


if __name__ == "__main__":
    main()
