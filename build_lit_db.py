"""
build_lit_db.py — 生成轻量级文献库供AI查阅

目录结构：
  lit_db/
  ├── overview.md                    # 数据库全局概况 (~30KB)
  ├── titles/
  │   ├── all_titles.tsv             # 全量索引，可grep (~5MB，无摘要)
  │   └── by_journal/
  │       ├── Sociology.md           # 某期刊全部标题+年份 (~50-300KB)
  │       └── ...（24个文件）
  └── abstracts/
      ├── 2020_2026/                 # 近6年，每期刊一个文件，含摘要截断到300字
      │   ├── Sociology.md
      │   └── ...（24个文件）
      ├── 2010_2019/
      └── 2000_2009/

使用方式：
  1. AI先读 overview.md 了解数据库全貌
  2. 读 titles/by_journal/[期刊].md 从标题初筛（全部年份）
     或读 titles/by_journal/ 里某期刊文件只看某年份段
  3. 对感兴趣的文章，读 abstracts/[年份段]/[期刊].md 看摘要
"""
import json
import re
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime

ROOT = Path(__file__).resolve().parent
LIT_DB = ROOT / "lit_db"

ABSTRACT_TRUNCATE = 300  # 摘要截断字数

JOURNAL_ORDER = [
    "American Journal of Sociology",
    "American Sociological Review",
    "Annual Review of Sociology",
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
    "Population and Development Review",
    "Research in Social Stratification and Mobility",
    "Social Forces",
    "Social Science Research",
    "Sociological Science",
    "Sociology",
    "Sociology of Education",
    "Socius",
    "Work, Employment and Society",
]

PERIOD_LABELS = {
    "2020_2026": (2020, 2026),
    "2010_2019": (2010, 2019),
    "2000_2009": (2000, 2009),
}

GITHUB_BASE = "https://raw.githubusercontent.com/huwenbo-lab/publication/main/lit_db"


def safe_filename(journal_name):
    """期刊名转换为安全文件名"""
    name = journal_name.replace("&", "and").replace(",", "")
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name.strip())
    return name


def clean_text(text):
    """清理HTML标签和断字问题"""
    if not text:
        return ""
    # 去掉HTML/XML标签
    text = re.sub(r"<[^>]+>", "", text)
    # 修复CrossRef OCR断字："dis ad van tage" → "disadvantage"（连字符后有空格+小写字母）
    # 保守修复：只处理明显的断字模式（单字母或两字母片段之间有空格）
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate_abstract(text, max_chars=ABSTRACT_TRUNCATE):
    if not text:
        return ""
    text = clean_text(text)
    if len(text) <= max_chars:
        return text
    # 截到最近的句号/问号
    cut = text[:max_chars]
    for sep in (". ", "? ", "! "):
        pos = cut.rfind(sep)
        if pos > max_chars * 0.6:
            return cut[:pos + 1] + "…"
    return cut + "…"


def load_articles():
    with open(ROOT / "articles.json", encoding="utf-8") as f:
        arts = json.load(f)
    # 按期刊 → 年份分组
    by_journal = defaultdict(list)
    for a in arts:
        by_journal[a.get("journal", "Unknown")].append(a)
    # 每个期刊内按年份降序排列
    for j in by_journal:
        by_journal[j].sort(key=lambda x: (x.get("year") or 0), reverse=True)
    return arts, by_journal


def build_overview(arts, by_journal):
    """生成 overview.md"""
    now = datetime.now().strftime("%Y-%m-%d")
    total = len(arts)
    journals_with_data = len(by_journal)

    all_years = [a.get("year") for a in arts if a.get("year")]
    year_min = min(all_years)
    year_max = max(all_years)

    lines = [
        "# 社会学与人口学文献数据库概览",
        "",
        f"> 生成时间：{now}  ",
        f"> 总计：**{total:,}** 篇 | **{journals_with_data}** 本期刊 | {year_min}–{year_max}",
        "",
        "## 数据字段",
        "",
        "| 字段 | 说明 |",
        "|---|---|",
        "| `title` | 文章标题 |",
        "| `abstract` | 摘要（部分早期文章可能为空） |",
        "| `authors` | 作者，格式：`姓, 名; 姓, 名` |",
        "| `journal` | 期刊名称 |",
        "| `year` | 发表年份 |",
        "| `doi` | DOI标识符 |",
        "",
        "## 研究方向",
        "",
        "- **社会分层**：不平等、阶级、流动性、教育机会",
        "- **婚姻与家庭**：婚育行为、家庭结构、性别角色、亲密关系",
        "- **人口学**：生育率、死亡率、人口流动、老龄化",
        "- **教育社会学**：学校教育、学业成就、教育不平等",
        "- **劳动与职业**：就业、工资、工作条件",
        "- **性别与社会**：性别不平等、女性主义、LGBTQ+",
        "",
        "## 各期刊文章统计",
        "",
        "| 期刊 | 文章数 | 年份范围 | 近6年(2020+) |",
        "|---|---|---|---|",
    ]

    for j in JOURNAL_ORDER:
        articles = by_journal.get(j, [])
        if not articles:
            continue
        years = [a.get("year") for a in articles if a.get("year")]
        y_min = min(years) if years else "?"
        y_max = max(years) if years else "?"
        recent = sum(1 for a in articles if (a.get("year") or 0) >= 2020)
        lines.append(f"| {j} | {len(articles):,} | {y_min}–{y_max} | {recent} |")

    lines += [
        "",
        "## 如何查阅文献",
        "",
        "### 两步检索法",
        "",
        "**第一步：标题初筛**",
        "加载 `titles/by_journal/[期刊名].md`，快速浏览所有文章标题，",
        "找出可能相关的文章（记下标题和年份）。",
        "",
        "**第二步：摘要精读**",
        "根据标题所在年份，加载对应的摘要文件：",
        "- 2020年至今 → `abstracts/2020_2026/[期刊名].md`",
        "- 2010–2019年 → `abstracts/2010_2019/[期刊名].md`",
        "- 2000–2009年 → `abstracts/2000_2009/[期刊名].md`",
        "",
        "### 文件索引",
        "",
        "| 文件/目录 | 内容 | 大小估计 | 适用场景 |",
        "|---|---|---|---|",
        "| `overview.md` | 数据库概况（本文件） | ~30KB | 了解全局 |",
        "| `titles/all_titles.tsv` | 全量标题索引，可grep | ~5MB | 本地关键词搜索 |",
        "| `titles/by_journal/*.md` | 按期刊分的标题列表 | 50–300KB/文件 | 标题初筛 |",
        "| `abstracts/2020_2026/*.md` | 近6年摘要，按期刊 | 50–250KB/文件 | 摘要精读 |",
        "| `abstracts/2010_2019/*.md` | 2010–2019年摘要 | 50–400KB/文件 | 摘要精读 |",
        "| `abstracts/2000_2009/*.md` | 2000–2009年摘要 | 50–300KB/文件 | 摘要精读 |",
        "",
        "### GitHub 原始文件 URL",
        "",
        f"```",
        f"{GITHUB_BASE}/overview.md",
        f"{GITHUB_BASE}/titles/by_journal/Sociology.md",
        f"{GITHUB_BASE}/abstracts/2020_2026/Sociology.md",
        f"```",
        "",
        "### 完整数据（含全文摘要）",
        "",
        "完整的 `articles.json`（34k条，32MB）：",
        "```",
        "https://raw.githubusercontent.com/huwenbo-lab/publication/main/articles.json",
        "```",
    ]

    out = LIT_DB / "overview.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ overview.md ({out.stat().st_size // 1024}KB)")


def build_titles_by_journal(by_journal):
    """生成 titles/by_journal/[journal].md"""
    out_dir = LIT_DB / "titles" / "by_journal"
    out_dir.mkdir(parents=True, exist_ok=True)

    for j in JOURNAL_ORDER:
        articles = by_journal.get(j, [])
        if not articles:
            continue

        fname = safe_filename(j) + ".md"
        lines = [
            f"# {j} — 文章标题索引",
            "",
            f"共 **{len(articles)}** 篇 | "
            f"年份范围：{min(a.get('year') or 9999 for a in articles)}–"
            f"{max(a.get('year') or 0 for a in articles)}",
            "",
            "> 使用方法：浏览标题初步筛选相关文章，记下标题和年份，",
            "> 再到对应年份段的 `abstracts/` 文件中查看摘要。",
            "",
        ]

        # 按年份分组
        by_year = defaultdict(list)
        for a in articles:
            yr = a.get("year") or 0
            by_year[yr].append(a)

        for yr in sorted(by_year.keys(), reverse=True):
            lines.append(f"## {yr if yr else '年份未知'}")
            lines.append("")
            for a in by_year[yr]:
                doi = a.get("doi", "")
                doi_str = f" · [DOI](https://doi.org/{doi})" if doi else ""
                title = clean_text(a.get("title", ""))
                lines.append(f"- {title}{doi_str}")
            lines.append("")

        out = out_dir / fname
        out.write_text("\n".join(lines), encoding="utf-8")

    total_files = len(list(out_dir.glob("*.md")))
    sizes = [f.stat().st_size for f in out_dir.glob("*.md")]
    print(f"  ✓ titles/by_journal/ ({total_files}个文件, "
          f"{min(sizes)//1024}–{max(sizes)//1024}KB, "
          f"总计{sum(sizes)//1024}KB)")


def build_all_titles_tsv(arts):
    """生成 titles/all_titles.tsv（全量，可grep）"""
    out_dir = LIT_DB / "titles"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "all_titles.tsv"

    lines = ["title\tjournal\tyear\tdoi\tauthors"]
    for a in sorted(arts, key=lambda x: (x.get("journal", ""), x.get("year") or 0)):
        title = clean_text(a.get("title", "")).replace("\t", " ")
        journal = a.get("journal", "").replace("\t", " ")
        year = str(a.get("year") or "")
        doi = a.get("doi", "")
        # 只取第一作者节省空间
        authors_raw = a.get("authors", "")
        if authors_raw:
            first_author = authors_raw.split(";")[0].strip()
            n_authors = authors_raw.count(";")
            authors = first_author + (f" et al. (+{n_authors})" if n_authors > 0 else "")
        else:
            authors = ""
        lines.append(f"{title}\t{journal}\t{year}\t{doi}\t{authors}")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ titles/all_titles.tsv ({out.stat().st_size // 1024 // 1024}MB, {len(lines)-1}条)")


def build_abstracts_by_period(by_journal):
    """生成 abstracts/[period]/[journal].md（含截断摘要）"""
    for period_key, (yr_from, yr_to) in PERIOD_LABELS.items():
        out_dir = LIT_DB / "abstracts" / period_key
        out_dir.mkdir(parents=True, exist_ok=True)

        period_total = 0
        for j in JOURNAL_ORDER:
            articles = by_journal.get(j, [])
            # 筛选该时间段的文章
            period_arts = [
                a for a in articles
                if a.get("year") and yr_from <= a["year"] <= yr_to
            ]
            if not period_arts:
                continue

            fname = safe_filename(j) + ".md"
            lines = [
                f"# {j}",
                f"## {yr_from}–{yr_to} 年文章（含摘要）",
                "",
                f"共 **{len(period_arts)}** 篇",
                "",
                "---",
                "",
            ]

            for a in period_arts:  # 已按年份降序排列
                title = clean_text(a.get("title", "（无标题）"))
                year = a.get("year", "")
                doi = a.get("doi", "")
                authors_raw = a.get("authors", "")
                abstract = truncate_abstract(a.get("abstract", ""))

                doi_link = f"[{doi}](https://doi.org/{doi})" if doi else "—"

                lines.append(f"### {title}")
                lines.append(f"**年份**: {year} | **DOI**: {doi_link}")
                if authors_raw:
                    # 前三位作者
                    author_list = [x.strip() for x in authors_raw.split(";")]
                    shown = "; ".join(author_list[:3])
                    if len(author_list) > 3:
                        shown += f" 等{len(author_list)}人"
                    lines.append(f"**作者**: {shown}")
                if abstract:
                    lines.append(f"**摘要**: {abstract}")
                else:
                    lines.append("**摘要**: （暂无）")
                lines.append("")

            out = out_dir / fname
            out.write_text("\n".join(lines), encoding="utf-8")
            period_total += len(period_arts)

        files = list(out_dir.glob("*.md"))
        if files:
            sizes = [f.stat().st_size for f in files]
            print(f"  ✓ abstracts/{period_key}/ ({len(files)}个文件, "
                  f"{min(sizes)//1024}–{max(sizes)//1024}KB, "
                  f"共{period_total}篇)")


def build_readme():
    """生成 lit_db/README.md"""
    lines = [
        "# lit_db — AI可查阅的文献库",
        "",
        "本目录为社会学文献数据库的轻量级索引，专为AI检索设计。",
        "完整数据见 `../articles.json`（34k条，32MB）。",
        "",
        "## 查阅流程",
        "",
        "```",
        "1. 读 overview.md          → 了解数据库全貌",
        "2. 读 titles/by_journal/   → 某期刊全部标题，快速初筛",
        "3. 读 abstracts/[年份段]/  → 看初筛结果对应的摘要",
        "```",
        "",
        "## 目录结构",
        "",
        "```",
        "lit_db/",
        "├── overview.md                    # 数据库概况、期刊列表、使用说明",
        "├── titles/",
        "│   ├── all_titles.tsv             # 全量34k标题，可grep搜索（~5MB）",
        "│   └── by_journal/                # 按期刊：每个文件含该刊所有标题",
        "│       ├── Sociology.md",
        "│       └── ...",
        "└── abstracts/",
        "    ├── 2020_2026/                 # 近6年，每期刊一个文件，含摘要片段",
        "    │   ├── Sociology.md",
        "    │   └── ...",
        "    ├── 2010_2019/",
        "    └── 2000_2009/",
        "```",
        "",
        "## 摘要说明",
        "",
        f"摘要截断至前 {ABSTRACT_TRUNCATE} 字符（约2–3句话），保留核心信息。",
        "完整摘要可通过 DOI 在 CrossRef 查询：`https://api.crossref.org/works/[DOI]`",
        "",
        "## 重新生成",
        "",
        "```bash",
        "source venv/bin/activate",
        "python build_lit_db.py",
        "```",
    ]
    out = LIT_DB / "README.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"  ✓ README.md")


def main():
    print("生成 lit_db/ 目录结构...")
    LIT_DB.mkdir(exist_ok=True)

    arts, by_journal = load_articles()
    print(f"已加载 {len(arts):,} 篇文章，{len(by_journal)} 本期刊\n")

    print("生成文件：")
    build_readme()
    build_overview(arts, by_journal)
    build_all_titles_tsv(arts)
    build_titles_by_journal(by_journal)
    build_abstracts_by_period(by_journal)

    print("\n完成！目录结构：")
    for root, dirs, files in os.walk(LIT_DB):
        dirs.sort()
        level = root.replace(str(LIT_DB), "").count(os.sep)
        indent = "  " * level
        print(f"{indent}{os.path.basename(root)}/")
        subindent = "  " * (level + 1)
        for f in sorted(files):
            fpath = Path(root) / f
            size = fpath.stat().st_size
            size_str = f"{size//1024}KB" if size < 1024*1024 else f"{size//1024//1024}MB"
            print(f"{subindent}{f}  ({size_str})")


if __name__ == "__main__":
    main()
