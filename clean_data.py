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
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARTICLES_JSON = ROOT / "articles.json"
DATA_JSON = ROOT / "data.json"
DATA_JS = ROOT / "data.js"


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
    r'^corrigendum\b',
    r'^correction\b',                       # 单独的 correction 通知
    r'^retraction\b',                       # 撤稿通知（不含 RETRACTED: 前缀的研究文章）
    r'^books?\s+received\b',
    r'^call\s+for\s+papers?\b',
    r'^index\s+(to\s+|$)',                  # 期刊年度索引
    r'^(four|five|six|seven|eight)\s+years?\s+of\s+books',  # "Four Years of Books Reviewed"
    r'^announcements?\s*$',
    r'^in\s+memoriam\b',
    r'^obituary\b',
    r'^note\s+from\s+the\s+editor\s*$',
    r'^editorial\s*(board|foreword|announcement|introduction|foreword|:.*book review)?\s*$',  # editorial board/foreword等
    r'^editorial\s+board',                  # editorial board (with anything after)
    r'^editorial\s+foreword',
    r'^editorial\s+announcement',
    r'^editorial\s+introduction\s*$',
    r'^[A-Z][a-z]+\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)?\s+\(\d{4}-\d{4}\)\s*$',  # 人名(年份-年份) 编辑致辞
    r'^contributors\s*$',
    r'^(to\s+)?our\s+contributors\b',
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

    print(f"\n清洗结果：")
    print(f"  删除非研究性条目: {len(deleted):,} 篇")
    print(f"  修复标题（去除HTML/脚注数字）: {title_fixed:,} 篇")
    print(f"  修复摘要（去除HTML标签/实体）: {abstract_fixed:,} 篇")
    print(f"  清空无效摘要内容: {abstract_cleared:,} 篇")
    print(f"  保留文章数: {len(cleaned):,}")

    # 打印删除条目供确认
    print(f"\n删除条目详情（前 30 条）：")
    for a, reason in deleted[:30]:
        print(f"  [{a['journal'][:25]}] {a['year']} | {a['title'][:60]}")
        print(f"    原因: {reason}")

    if len(deleted) > 30:
        print(f"  ... 还有 {len(deleted)-30} 条")

    save_articles(cleaned)
    print(f"\n✓ 已保存至 articles.json / data.json / data.js")


if __name__ == "__main__":
    main()
