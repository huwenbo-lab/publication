"""
clean_data.py — 数据清洗脚本

修复以下问题：
1. 标题末尾的脚注数字（如 "...China1", "<sup>1</sup>"）
2. 标题/摘要中的 HTML 标签（<i>, <sup>, <scp>, <b>, <sub>, <it> 等）
3. 标题/摘要中的 HTML 实体（&amp; &lt; &gt; 等）
4. 删除非研究性条目（editorial, erratum, books received, call for papers 等）
5. 删除无效摘要（reviewer list、editorial board list 等）
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from _paths import REPORTS_DIR, ROOT

ARTICLES_JSON = ROOT / "articles.json"
DATA_JSON = ROOT / "data.json"
DATA_JS = ROOT / "data.js"
CLEANUP_REPORT = REPORTS_DIR / "non_article_cleanup_report.md"


# ──────────────────────────────────────────────
# 文本清洗函数
# ──────────────────────────────────────────────

def clean_html(text):
    """去除 HTML 标签，保留文本内容"""
    if not text:
        return text
    # 先处理常见需要保留内容的标签
    text = re.sub(r'<i>(.*?)</i>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<b>(.*?)</b>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<it>(.*?)</it>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<scp>(.*?)</scp>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<sup>(.*?)</sup>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'<sub>(.*?)</sub>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)
    # 删除其余所有标签
    text = re.sub(r'<[^>]+>', '', text)
    return text


def clean_html_entities(text):
    """还原 HTML 实体"""
    if not text:
        return text
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&apos;', "'")
    text = text.replace('&#39;', "'")
    text = text.replace('&nbsp;', ' ')
    return text


def clean_title(title):
    """清洗标题"""
    if not title:
        return title
    # 1. 去除 HTML 标签
    title = clean_html(title)
    # 2. 还原 HTML 实体
    title = clean_html_entities(title)
    # 3. 去除末尾的脚注数字（字母/括号后紧跟数字，如 "China1", "Case1"）
    #    保留：年份范围末尾的数字（如 "1955-1985", "1990-2002"）
    #    保留：标题本身以数字结尾的情况（如 "Part 2", "Wave 3"）
    #    去除：英文字母直接跟数字，且数字是1-9（脚注通常是小数字）
    title = re.sub(r'([a-zA-Z\)])\s*([1-9])\s*$', r'\1', title)
    # 4. 清理多余空白
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def clean_abstract(abstract):
    """清洗摘要"""
    if not abstract:
        return abstract
    # 1. 去除 HTML 标签
    abstract = clean_html(abstract)
    # 2. 还原 HTML 实体
    abstract = clean_html_entities(abstract)
    # 3. 清理多余空白
    abstract = re.sub(r'\s+', ' ', abstract).strip()
    return abstract


# ──────────────────────────────────────────────
# 无效条目判断
# ──────────────────────────────────────────────

# 标题匹配：这些是非研究性条目，应删除
DELETE_TITLE_PATTERNS = [
    r'^erratum\b',
    r'^errata\b',
    r'^corrigendum\b',
    r'^corrigenda\b',
    r'^correction\b',                       # 单独的 correction 通知
    r'^retraction\b',                       # 撤稿通知（不含 RETRACTED: 前缀的研究文章）
    r'^withdrawal\s*[–—-]\s*administrative\s+duplicate\s+publication\b',
    r'^book\s+reviews?\b',
    r'\bbook\s+reviews?\b',
    r'^book\s+review\s+essay\b',
    r'\bbook\s+review\s+essay\b',
    r'\bbook\s+review\s+symposium\b',
    r'^from\s+the\s+book\s+review\s+editors?\b',
    r'^note\s+from\s+the\s+book\s+review\s+editors?\b',
    r'^books?\s+still\s+matter:\s+a\s+note\s+from\s+the\s+book\s+review\s+editors?\b',
    r'administrative\s+duplicate\s+publication:\s+book\s+review\b',
    r'\((eds?\.?|editors?)\)[:,;]',
    r'\b(eds?\.?)[:,;]\s',
    r'\b\d+\s*pp\.?\b',
    r'\bpp\.\s*[xivxlc\d+]+\b',
    r'\b\d+\s+pages\b',
    r'\bisbn\b',
    r'\b(hardback|paperback|cloth)\b',
    r'[\$£€]\s*\d',
    r'^review\s+essay\b',
    r'^review\s+symposium\b',
    r'^books?\s+received\b',
    r'^books?\s+reviewed\b',
    r'^books?\s+and\s+publications?\s+received\b',
    r'^books?\s+and\s+publication\s+received\b',
    r'^list\s+of\s+books?\s+and\s+publications?\s+received\b',
    r'^call\s+for\s+papers?\b',
    r'\bcall\s+for\s+.*papers\b',
    r'^subject\s+index\b',
    r'^author\s+index\b',
    r'^authors?\s+index\b',
    r'^index\s+of\s+authors?\b',
    r'^contents\b',
    r'^list\s+of\s+contributors\b',
    r'^list\s+of\s+(figures|tables)\b',
    r'^preface\b',
    r'^edited\s+by\b',
    r'^abstract\s*$',
    r'^copyright\s+page\b',
    r'^acknowledg(e)?ments?\s*$',
    r'^acknowledg(e)?ments?\s+of\s+reviewers?\b',
    r'^reviewers?\s+acknowledg(e)?ments?\b',
    r'^referees?\s+of\s+papers?\s+submitted\b',
    r'^reviewers?\s+of\s+papers?\s+submitted\b',
    r'^thanks?\s+to\s+(the\s+)?reviewers?\b',
    r'^thank\s+you\s+to\s+referees?\b',
    r'^about\s+the\s+authors?\b',
    r'^commentary\s*$',
    r'^prelim\b',
    r'^bibliography\s*$',
    r'^references\s*$',
    r'^appendix\s*$',
    r'^chapter\s+\d+\b',
    r'^part\s+[ivxlcdm]+\b',
    r'^general\s+conclusions?\b',
    r'^index\s+(to\s+|$)',                  # 期刊年度索引
    r'^index\s+to\s+volume\b',
    r'^volume\s+contents\b',
    r'^volume\s+contents\s+and\s+author\s+index\b',
    r'^(cumulative\s+)?table\s+of\s+contents\b',
    r'^issue\s+information\s*[–—-]\s*table\s+of\s+contents\b',
    r'^issue\s+information\b',
    r'^front\s+matter\b',
    r'^back\s+matter\b',
    r'^(four|five|six|seven|eight)\s+years?\s+of\s+books',  # "Four Years of Books Reviewed"
    r'^announcements?\s*$',
    r'^announcing\s+a\s+new\s+journal\b',
    r'^new\s+publications?\b',
    r'^\d{4}\s+publication\s+programme\b',
    r'^change\s+of\s+address\b',
    r'^publisher[’\']?s?\s+(note|notice|announcement)\b',
    r'^important\s+notice\s+from\s+the\s+editor\b',
    r'^notice\s*$',
    r'^in\s+memoriam\b',
    r'\bin\s+memoriam\b',
    r'^obituary\b',
    r'\bobituary\b',
    r'^[a-z]+(?:\s+[a-z]+){0,3}\s+remembered\s*$',
    r'^memorial\s*$',
    r'^note\s+from\s+the\s+editor\s*$',
    r'^from\s+the\s+editors?\b',
    r'^editors?[’\']?s?\s+note\b',
    r'^editors?[’\']?s?\s+introduction\b',
    r'^editorial\s*(board|foreword|announcement|introduction|foreword|:.*book review)?\s*$',  # editorial board/foreword等
    r'^editorial\s+board',                  # editorial board (with anything after)
    r'\beditorial\s+board\b',
    r'^editorial\s+advisory\s+board',
    r'^editorial\s+foreword',
    r'^editorial\s+announcement',
    r'^editorial\s+introduction\s*$',
    r'^ifc\.\s+editorial\s+board\b',
    r'\beditorial\s+board\s*/\s*aims\s+and\s+scope\b',
    r'^guest\s+editors?[’\']?s?\s+introduction\b',
    r'^guest\s+editors?[’\']?s?\s+note\b',
    r'^from\s+the\s+guest\s+editors?\b',
    r'^guest\s+editorial\b',
    r'^introduction\s+to\s+(this\s+|the\s+|a\s+)?special\s+issue\b',
    r'^introduction\s+to\s+.*special\s+issue\b',
    r'^introduction:\s+.*special\s+issue\b',
    r'\bintroduction\s+to\s+(this\s+|the\s+|a\s+)?special\s+issue\b',
    r'\ban\s+introduction\s+to\s+(the\s+)?special\s+issue\b',
    r'^special\s+issue\s+introduction\b',
    r'\bspecial\s+issue\s+introduction\b',
    r'^special\s+issue\s+of\b',
    r'.*\bmini\s+conference\s+and\s+special\s+issue\b',
    r'.*\bretraction\s+statement\b',
    r'^what\s+is\s+onlineearly\??\s*$',
    r'^social\s+psychology\s+quarterly\s*$',
    r'^social\s+indicators\s+research\s*$',
    r'^advances\s+in\s+life\s+course\s+research\s+a\s+books?\s+available\s+online\b',
    r'^notes?\s+to\s+authors?\b',
    r'^[A-Z][a-z]+\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)?\s+\(\d{4}-\d{4}\)\s*$',  # 人名(年份-年份) 编辑致辞
    r'^contributors\s*$',
    r'^notes\s+on\s+contributors\b',
    r'^(to\s+)?our\s+contributors\b',
    r'^list\s+of\s+(reviewers|referees)\b',
    r'^acknowledg(e)?ments?\s+to\s+(reviewers|referees)\b',
    r'^reviewers?\s+for\s+volume\b',
]

# 摘要内容无效：清空（而非删除整条）
INVALID_ABSTRACT_PATTERNS = [
    r'^list\s+of\s+(reviewer|referee)',
    r'acknowledgement\s+of\s+reviewer',
    r'^\s*retracted\s*$',                   # 摘要只有 "RETRACTED"
    r'^\s*n/a\s*$',
    r'^(journal article\s+)?editorial\s+board(\s+get\s+access)?',  # "Editorial Board Get access..."
    r'^journal article\s+editorial\s+board',
]

# 标题模式：触发删除整条（明确的非正文内容）
DELETE_TITLE_EXACT = {
    "erratum", "corrigendum", "retraction", "correction",
    "books received", "index", "announcements", "contributors",
}


def should_delete(article):
    """判断该条目是否应删除"""
    title = (article.get("title") or "").strip()
    title_lower = title.lower()

    # 精确匹配
    if title_lower in DELETE_TITLE_EXACT:
        return True, f"非研究条目: {title_lower}"

    # 模式匹配
    for pat in DELETE_TITLE_PATTERNS:
        if re.search(pat, title_lower):
            return True, f"非研究条目 ({pat}): {title}"

    return False, ""


def should_clear_abstract(article):
    """判断摘要是否应清空（内容无效）"""
    abstract = (article.get("abstract") or "").strip()
    if not abstract:
        return False

    abstract_lower = abstract.lower()
    for pat in INVALID_ABSTRACT_PATTERNS:
        if re.search(pat, abstract_lower):
            return True
    return False


def normalize_title_key(title):
    """Normalize title enough for exact duplicate detection."""
    title = clean_title(title or "").lower()
    title = re.sub(r"[’‘]", "'", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title


def article_score(article):
    """Prefer the most complete metadata when exact duplicate titles exist."""
    abstract = (article.get("abstract") or "").strip()
    doi = (article.get("doi") or "").strip().lower()
    authors = (article.get("authors") or "").strip()
    return (
        bool(abstract),
        len(abstract),
        bool(doi),
        not doi.startswith("10.2307/"),
        len(authors),
    )


def deduplicate_articles(articles):
    """Remove exact duplicates by journal + year + normalized title."""
    groups = defaultdict(list)
    for idx, article in enumerate(articles):
        key = (
            (article.get("journal") or "").strip().lower(),
            article.get("year"),
            normalize_title_key(article.get("title")),
        )
        groups[key].append((idx, article))

    keep_indices = set()
    duplicates_removed = []
    for rows in groups.values():
        if len(rows) == 1:
            keep_indices.add(rows[0][0])
            continue

        keep_idx, keep_article = max(rows, key=lambda row: (article_score(row[1]), -row[0]))
        keep_indices.add(keep_idx)
        for idx, article in rows:
            if idx != keep_idx:
                reason = (
                    "重复条目: same journal/year/title; kept "
                    f"DOI={(keep_article.get('doi') or '').strip() or '[missing]'}"
                )
                duplicates_removed.append((article, reason))

    deduped = [article for idx, article in enumerate(articles) if idx in keep_indices]
    return deduped, duplicates_removed


# ──────────────────────────────────────────────
# 保存
# ──────────────────────────────────────────────

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


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def main():
    with open(ARTICLES_JSON, encoding="utf-8") as f:
        articles = json.load(f)

    print(f"原始文章数: {len(articles):,}")

    deleted = []
    cleaned = []
    title_fixed = 0
    abstract_fixed = 0
    abstract_cleared = 0

    for a in articles:
        # 1. 判断是否删除整条
        do_delete, reason = should_delete(a)
        if do_delete:
            deleted.append((a, reason))
            continue

        # 2. 清洗标题
        original_title = a.get("title") or ""
        new_title = clean_title(original_title)
        if new_title != original_title:
            a["title"] = new_title
            title_fixed += 1

        # 3. 判断摘要是否无效 → 清空
        if should_clear_abstract(a):
            a["abstract"] = ""
            abstract_cleared += 1
        else:
            # 4. 清洗摘要
            original_ab = a.get("abstract") or ""
            new_ab = clean_abstract(original_ab)
            if new_ab != original_ab:
                a["abstract"] = new_ab
                abstract_fixed += 1

        cleaned.append(a)

    deduped, duplicates_removed = deduplicate_articles(cleaned)

    print(f"\n清洗结果：")
    print(f"  删除非研究性条目: {len(deleted):,} 篇")
    print(f"  删除重复条目: {len(duplicates_removed):,} 篇")
    print(f"  修复标题（去除HTML/脚注数字）: {title_fixed:,} 篇")
    print(f"  修复摘要（去除HTML标签/实体）: {abstract_fixed:,} 篇")
    print(f"  清空无效摘要内容: {abstract_cleared:,} 篇")
    print(f"  保留文章数: {len(deduped):,}")

    # 打印删除条目供确认
    removed = deleted + duplicates_removed
    print(f"\n删除条目详情（前 30 条）：")
    for a, reason in removed[:30]:
        print(f"  [{a['journal'][:25]}] {a['year']} | {a['title'][:60]}")
        print(f"    原因: {reason}")

    if len(removed) > 30:
        print(f"  ... 还有 {len(removed)-30} 条")

    reason_counts = Counter(reason for _, reason in removed)
    report_lines = [
        "# Non-Article Cleanup Report",
        "",
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}",
        "",
        f"- Original records: {len(articles):,}",
        f"- Non-article records deleted: {len(deleted):,}",
        f"- Duplicate records deleted: {len(duplicates_removed):,}",
        f"- Deleted records total: {len(removed):,}",
        f"- Kept records: {len(deduped):,}",
        f"- Title fixes: {title_fixed:,}",
        f"- Abstract fixes: {abstract_fixed:,}",
        f"- Invalid abstracts cleared: {abstract_cleared:,}",
        "",
        "## Deleted Reason Counts",
        "",
        "| Reason | Count |",
        "|---|---:|",
    ]
    for reason, count in reason_counts.most_common():
        report_lines.append(f"| {reason.replace('|', '/')} | {count:,} |")

    report_lines.extend([
        "",
        "## Deleted Examples",
        "",
        "| Journal | Year | Title | Reason |",
        "|---|---:|---|---|",
    ])
    for a, reason in removed[:200]:
        report_lines.append(
            f"| {a.get('journal', '').replace('|', '/')} | {a.get('year') or ''} | "
            f"{(a.get('title') or '').replace('|', '/')} | {reason.replace('|', '/')} |"
        )
    CLEANUP_REPORT.write_text("\n".join(report_lines), encoding="utf-8")
    print(f"  清理报告: {CLEANUP_REPORT}")

    save_articles(deduped)
    print(f"\n✓ 已保存至 articles.json / data.json / data.js")


if __name__ == "__main__":
    main()
