# Agent 交接文档
## 社会学与人口学期刊文献数据库 — 当前进度与待续任务

> 本文档供接手的 AI agent 阅读，用于了解项目全貌、已完成工作和下一步任务。
> 最后更新：2026-04-03

---

## 一、项目概况

**目标**：构建一个社会学与人口学领域的学术文献元数据数据库，供研究人员通过全文检索和 AI 辅助查阅，用于日常科研（文献综述、研究空白识别、选题参考）。

**GitHub 仓库**：`https://github.com/huwenbo-lab/publication`
**GitHub Pages 在线浏览**：`https://huwenbo-lab.github.io/publication/`
**本地路径**：`/Users/wenbohu/Downloads/文献库/期刊文献/`

**当前数据库规模**（截至 2026-04-03）：
- 总文章数：**33,771 篇**
- 收录期刊：**24 本**（社会学 + 人口学核心期刊）
- 年份覆盖：**2000–2026**
- 摘要覆盖率：**79.8%**（26,955 篇有摘要，6,816 篇缺失）
- DOI 覆盖率：**99.8%**（仅 73 篇无 DOI）

---

## 二、文件结构

```
期刊文献/
├── articles.json          ← 主数据文件（新格式，每条含 title/abstract/authors/journal/year/doi）
├── data.json              ← 旧格式（供 index.html 使用，字段名为 Source Title 等）
├── data.js                ← JavaScript 版 data.json（const DATA = [...]）
├── index.html             ← GitHub Pages 前端页面
│
├── build_articles.py      ← 从 raw_data/*.xls 重建 articles.json
├── enrich_crossref.py     ← CrossRef API 四阶段补全（摘要、DOI、历史数据、缺失期刊）
├── enrich_openalex.py     ← OpenAlex + Semantic Scholar 二次补全摘要
├── clean_data.py          ← 数据清洗（删非研究条目、修标题/摘要 HTML、脚注数字）
├── build_lit_db.py        ← 生成 lit_db/ 目录（AI 两步检索索引）
├── build_search_db.py     ← 构建 SQLite FTS5 全文检索数据库 → literature.db
├── update.py              ← 定期从 CrossRef 抓取新文章
├── check_quality.py       ← 数据质量检查报告
│
├── raw_data/              ← 17 本期刊的 WoS 原始 Excel 导出文件（归档，不改动）
│   └── *.xls
│
├── lit_db/                ← AI 查阅索引（两步检索结构）
│   ├── overview.md        ← 数据库概况，供 AI 先读（~3KB）
│   ├── titles/
│   │   ├── all_titles.tsv ← 全量标题索引（~5MB，可 grep）
│   │   └── by_journal/    ← 每本期刊的标题文件（24 个 .md）
│   └── abstracts/
│       ├── 2020_2026/     ← 近 6 年，按期刊（24 个 .md）
│       ├── 2010_2019/     ← 2010–2019 年
│       └── 2000_2009/     ← 2000–2009 年
│
├── literature.db          ← SQLite FTS5 检索库（63MB，生成文件，不入 git）
├── venv/                  ← Python 虚拟环境
├── CLAUDE.md              ← 项目说明（供 Claude Code 使用）
├── README.md              ← 项目文档（面向人类）
├── 使用指南.md             ← 面向社科生的小白操作手册
└── AGENT_HANDOFF.md       ← 本文件
```

---

## 三、数据格式说明

### articles.json 字段

```json
{
  "title": "文章标题（已清洗，无 HTML 标签）",
  "abstract": "摘要（可能为空字符串）",
  "authors": "姓, 名; 姓, 名",
  "journal": "期刊名（Title Case，与下表 JOURNALS 字典一致）",
  "year": 2023,
  "doi": "10.xxxx/xxxxx"
}
```

### 25 本期刊列表（含 ISSN）

| 期刊名 | ISSN | 数据起始年 |
|---|---|---|
| American Journal of Sociology | 0002-9602 | 2000 |
| American Sociological Review | 0003-1224 | 2000 |
| Annual Review of Sociology | 0360-0572 | 2000 |
| Asian Population Studies | 1744-1730 | 2005 |
| British Journal of Sociology | 0007-1315 | 2000 |
| British Journal of Sociology of Education | 0142-5692 | 2000 |
| Chinese Journal of Sociology | 2057-150X | 2015 |
| Chinese Sociological Review | 2162-0555 | 2000 |
| Demographic Research | 1435-9871 | 2000 |
| Demography | 0070-3370 | 2000 |
| European Journal of Population | 0168-6577 | 2000 |
| European Sociological Review | 0266-7215 | 2000 |
| Gender & Society | 0891-2432 | 2000 |
| Journal of Family Issues | 0192-513X | 2000 |
| Journal of Family Theory & Review | 1756-2570 | 2009 |
| Journal of Marriage and Family | 0022-2445 | 2000 |
| Population and Development Review | 0098-7921 | 2000 |
| Research in Social Stratification and Mobility | 0276-5624 | 2000 |
| Social Forces | 0037-7732 | 2000 |
| Social Science Research | 0049-089X | 2000 |
| Sociological Science | 2330-6696 | 2014 |
| Sociology | 0038-0385 | 2000 |
| Sociology of Education | 0038-0407 | 2000 |
| Socius | 2378-0231 | 2015 |
| Work, Employment and Society | 0950-0170 | 2000 |

---

## 四、已完成的工作

### 4.1 数据采集

- **WoS Excel 导出**：17 本期刊通过 Web of Science 手动导出 .xls 文件（存于 `raw_data/`），经 `build_articles.py` 清洗合并
- **CrossRef API 全量抓取**（`enrich_crossref.py`，4 个阶段）：
  - Phase 1：有 DOI 无摘要 → 直接查 CrossRef 补摘要
  - Phase 2：无 DOI → 按标题搜索 CrossRef 补 DOI
  - Phase 3：已有 Excel 的期刊补历史缺口年份（2000 年起）
  - Phase 4：8 本无 Excel 的期刊从 CrossRef 全量抓取（新增 Asian Population Studies 后共 8 本）
- **OpenAlex + Semantic Scholar**（`enrich_openalex.py`）：对 CrossRef 仍缺摘要的 9,718 篇研究论文二次补全，新增 5,650 篇摘要

### 4.2 数据清洗（`clean_data.py`，最近完成）

- **删除 334 条非研究性条目**：erratum、corrigendum、correction、editorial board、books received、call for papers、index、in memoriam、obituary 等
- **修复 2,234 篇文章标题**：
  - 去除 HTML 标签（`<i>`, `<sup>`, `<scp>`, `<b>`, `<sub>`）
  - 去除末尾脚注上标数字（如 `China1` → `China`，`<sup>1</sup>` 末尾）
  - 解码 HTML 实体（`&amp;` → `&`，`&gt;` → `>` 等）
- **修复 66 篇摘要**：清除残留 HTML 标签和实体
- **清空 2 条无效摘要**：reviewer list、纯 "RETRACTED" 字样

### 4.3 检索功能

- **SQLite FTS5 全文检索**（`literature.db`，63MB）：对标题 + 摘要建全文索引，毫秒级搜索，支持关键词/期刊/年份过滤
- **lit_db/ 两步检索索引**：供 AI agent 直接读取——先加载标题文件初筛，再按需读摘要文件

### 4.4 周边文档

- `README.md`：完整项目文档（期刊表、文件结构、更新/检索命令）
- `使用指南.md`：面向社科生的零门槛操作手册（5 个使用场景 + AI 提问示例）
- `CLAUDE.md`：供 Claude Code 使用的项目规范文档

---

## 五、当前已知问题与待续任务

### 5.1 摘要缺失（最主要的遗留问题）

**现状**：6,816 篇文章缺摘要（20.2%），分布如下：

| 期刊 | 缺摘要 | 缺失率 | 主要原因 |
|---|---|---|---|
| Gender & Society | 1,282 | 59% | 书评占比高 + Sage 封锁早期摘要 |
| Social Science Research | 1,219 | 55% | Elsevier 封锁，需机构网络访问 |
| Sociology | 1,020 | 36% | 书评 + 早期 Sage/Wiley 封锁 |
| Work, Employment and Society | 841 | 36% | 同上 |
| European Journal of Population | 541 | 65% | Springer 早期封锁 |
| British Journal of Sociology | 509 | 29% | Wiley 封锁 |

**可尝试的补救方案**：
1. **Elsevier API（校园网/VPN）**：Social Science Research 是 Elsevier 期刊，免费开发者 key（`a6f1926e981760a3854cb1d519ae5193`）已注册，但需要机构 IP 认证才能获取摘要。从学校 VPN 运行 `enrich_elsevier.py`（脚本尚未写，需新建）即可。
2. **Springer API**：European Journal of Population 是 Springer 旗下，Springer Nature 提供免费 API（需注册），可补 EJP 的早期摘要。
3. **直接爬取**：Demographic Research、Sociological Science、Socius 均为完全开放获取期刊，可直接解析 HTML 抓取摘要。

### 5.2 尚未实现的 Elsevier 补全脚本

需新建 `enrich_elsevier.py`，逻辑如下：

```python
# 已有 API key，在机构 VPN 下可获取摘要
API_KEY = "a6f1926e981760a3854cb1d519ae5193"

# 目标期刊（均为 Elsevier）
ELSEVIER_JOURNALS = {
    "Social Science Research",      # ISSN 0049-089X，缺 1,219 篇
    "Research in Social Stratification and Mobility",  # ISSN 0276-5624，缺 189 篇
}

# 端点
url = f"https://api.elsevier.com/content/abstract/doi/{doi}?apiKey={API_KEY}"
# 返回 JSON，摘要在：data["abstracts-retrieval-response"]["coredata"]["dc:description"]
```

### 5.3 日常更新

`update.py` 已可用，从 CrossRef 抓取最新文章（默认 30 天内）。每次更新后需同步重建：

```bash
source venv/bin/activate
python update.py
python build_search_db.py --rebuild
python build_lit_db.py
```

### 5.4 数据质量的遗留小问题

- 少量书评文章仍在库中（只删除了标题含明显书评标志的，但标题无法识别的书评无法批量处理）
- 少量文章标题包含非 ASCII 特殊字符（破折号样式不统一），影响不大，暂不处理
- `data_quality_report.md` 是基于原始 XLS 文件的报告，已不反映当前 articles.json 的状态，可用 `python check_quality.py` 重新生成（但该脚本读 raw_data/*.xls，不读 articles.json）

---

## 六、运行环境

```bash
# Python 版本
python3 --version   # 3.9+（系统自带）或 venv 内的版本

# 激活虚拟环境
source venv/bin/activate   # Mac/Linux

# 主要依赖（均为标准库或已安装）
# - xlrd：读取 .xls 文件（build_articles.py 用）
# - sqlite3：标准库，FTS5 检索
# - urllib.request：标准库，API 请求（不依赖 requests）
```

**API 配置**（硬编码在各脚本中，无需额外设置）：
- CrossRef：使用 polite pool，`mailto=hwbruc@gmail.com`，速率 1 秒/请求
- OpenAlex：`mailto=hwbruc@gmail.com`，批量查询，速率 0.2 秒/批次
- Semantic Scholar：POST `/paper/batch`，速率 1 秒/批次
- Elsevier：`API_KEY=a6f1926e981760a3854cb1d519ae5193`，需机构 IP 解锁摘要

**Git**：
- 远程：`https://github.com/huwenbo-lab/publication.git`
- 推送大文件需设置：`git config http.postBuffer 524288000`
- `literature.db` 已加入 `.gitignore`，不入库

---

## 七、快速上手命令

```bash
cd /Users/wenbohu/Downloads/文献库/期刊文献
source venv/bin/activate

# 全文检索测试
python3 build_search_db.py --search "education inequality China"

# 抓取最新文章
python3 update.py --days 30

# 重建所有索引
python3 build_search_db.py --rebuild
python3 build_lit_db.py

# 查看数据质量
python3 - <<'EOF'
import json
with open("articles.json") as f: a = json.load(f)
missing = sum(1 for x in a if not x.get("abstract","").strip())
print(f"总文章: {len(a):,}，缺摘要: {missing:,} ({missing/len(a)*100:.1f}%)")
EOF
```

---

## 八、优先级建议

下一个 agent 接手后，建议按以下优先级处理：

1. **【高优先级】运行日常更新**：执行 `python3 update.py` 补充最近新发表的文章，然后重建检索库
2. **【中优先级】Elsevier 摘要补全**：在学校 VPN 环境下，新建 `enrich_elsevier.py`，对 Social Science Research（~1,219 篇）和 RSSM（~189 篇）补充摘要
3. **【低优先级】Springer 摘要补全**：注册 Springer Nature API，补充 European Journal of Population 的早期摘要
4. **【可选】开放获取期刊爬取**：Demographic Research、Sociological Science、Socius 均可直接抓取全文摘要

---

*本文档由 Claude Sonnet 4.6 于 2026-04-03 根据完整对话记录生成。*
