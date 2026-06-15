# 社会学与人口学文献数据库概览

> 生成时间：2026-06-15  
> 总计：**34,131** 篇 | **25** 本期刊 | 1896–2026

## 数据字段

| 字段 | 说明 |
|---|---|
| `title` | 文章标题 |
| `abstract` | 摘要（部分早期文章可能为空） |
| `authors` | 作者，格式：`姓, 名; 姓, 名` |
| `journal` | 期刊名称 |
| `year` | 发表年份 |
| `doi` | DOI标识符 |

## 研究方向

- **社会分层**：不平等、阶级、流动性、教育机会
- **婚姻与家庭**：婚育行为、家庭结构、性别角色、亲密关系
- **人口学**：生育率、死亡率、人口流动、老龄化
- **教育社会学**：学校教育、学业成就、教育不平等
- **劳动与职业**：就业、工资、工作条件
- **性别与社会**：性别不平等、女性主义、LGBTQ+

## 各期刊文章统计

| 期刊 | 文章数 | 年份范围 | 近6年(2020+) |
|---|---|---|---|
| American Journal of Sociology | 1,094 | 1896–2026 | 196 |
| American Sociological Review | 1,259 | 1936–2026 | 229 |
| Annual Review of Sociology | 628 | 1975–2026 | 128 |
| Asian Population Studies | 433 | 2005–2026 | 140 |
| British Journal of Sociology | 1,850 | 1950–2026 | 434 |
| British Journal of Sociology of Education | 1,724 | 1980–2026 | 496 |
| Chinese Journal of Sociology | 265 | 2015–2026 | 150 |
| Chinese Sociological Review | 273 | 2011–2026 | 143 |
| Demographic Research | 1,844 | 1999–2026 | 515 |
| Demography | 2,011 | 1964–2026 | 548 |
| European Journal of Population | 848 | 1985–2026 | 215 |
| European Sociological Review | 1,529 | 1986–2026 | 411 |
| Gender & Society | 1,260 | 1987–2026 | 215 |
| Journal of Family Issues | 2,357 | 1980–2026 | 753 |
| Journal of Family Theory & Review | 764 | 2009–2026 | 324 |
| Journal of Marriage and Family | 2,567 | 1965–2026 | 534 |
| Population and Development Review | 1,110 | 1976–2026 | 285 |
| Research in Social Stratification and Mobility | 859 | 2001–2026 | 375 |
| Social Forces | 2,950 | 1926–2026 | 512 |
| Social Science Research | 2,227 | 1972–2026 | 548 |
| Sociological Science | 399 | 2014–2026 | 206 |
| Sociology | 2,319 | 1968–2026 | 480 |
| Sociology of Education | 639 | 1963–2026 | 127 |
| Socius | 1,024 | 2016–2026 | 739 |
| Work, Employment and Society | 1,898 | 1987–2026 | 446 |

## 如何查阅文献

### 两步检索法

**第一步：标题初筛**
加载 `titles/by_journal/[期刊名].md`，快速浏览所有文章标题，
找出可能相关的文章（记下标题和年份）。

**第二步：摘要精读**
根据标题所在年份，加载对应的摘要文件：
- 2020年至今 → `abstracts/2020_2026/[期刊名].md`
- 2010–2019年 → `abstracts/2010_2019/[期刊名].md`
- 2000–2009年 → `abstracts/2000_2009/[期刊名].md`

### 文件索引

| 文件/目录 | 内容 | 大小估计 | 适用场景 |
|---|---|---|---|
| `overview.md` | 数据库概况（本文件） | ~30KB | 了解全局 |
| `titles/all_titles.tsv` | 全量标题索引，可grep | ~5MB | 本地关键词搜索 |
| `titles/by_journal/*.md` | 按期刊分的标题列表 | 50–300KB/文件 | 标题初筛 |
| `abstracts/2020_2026/*.md` | 近6年摘要，按期刊 | 50–250KB/文件 | 摘要精读 |
| `abstracts/2010_2019/*.md` | 2010–2019年摘要 | 50–400KB/文件 | 摘要精读 |
| `abstracts/2000_2009/*.md` | 2000–2009年摘要 | 50–300KB/文件 | 摘要精读 |

### GitHub 原始文件 URL

```
https://raw.githubusercontent.com/huwenbo-lab/publication/main/lit_db/overview.md
https://raw.githubusercontent.com/huwenbo-lab/publication/main/lit_db/titles/by_journal/Sociology.md
https://raw.githubusercontent.com/huwenbo-lab/publication/main/lit_db/abstracts/2020_2026/Sociology.md
```

### 完整数据（含全文摘要）

完整的 `articles.json`（34k条，32MB）：
```
https://raw.githubusercontent.com/huwenbo-lab/publication/main/articles.json
```