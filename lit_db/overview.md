# 社会学与人口学文献数据库概览

> 生成时间：2026-05-04  
> 总计：**35,922** 篇 | **25** 本期刊 | 1896–2026

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
| American Journal of Sociology | 991 | 1896–2026 | 191 |
| American Sociological Review | 1,185 | 1940–2026 | 228 |
| Annual Review of Sociology | 577 | 1975–2026 | 120 |
| Asian Population Studies | 451 | 2005–2026 | 138 |
| British Journal of Sociology | 1,823 | 1950–2026 | 427 |
| British Journal of Sociology of Education | 1,712 | 1980–2026 | 477 |
| Chinese Journal of Sociology | 267 | 2015–2026 | 148 |
| Chinese Sociological Review | 272 | 2011–2026 | 142 |
| Demographic Research | 1,846 | 1999–2026 | 510 |
| Demography | 1,987 | 1964–2026 | 547 |
| European Journal of Population | 866 | 1985–2026 | 213 |
| European Sociological Review | 1,570 | 1985–2026 | 409 |
| Gender & Society | 2,285 | 1987–2026 | 519 |
| Journal of Family Issues | 2,347 | 1980–2026 | 746 |
| Journal of Family Theory & Review | 842 | 2009–2026 | 343 |
| Journal of Marriage and Family | 2,547 | 1966–2026 | 536 |
| Population and Development Review | 1,051 | 1976–2026 | 280 |
| Research in Social Stratification and Mobility | 867 | 2001–2026 | 369 |
| Social Forces | 2,902 | 1926–2026 | 505 |
| Social Science Research | 2,263 | 1972–2026 | 533 |
| Sociological Science | 397 | 2014–2026 | 203 |
| Sociology | 2,907 | 1975–2026 | 580 |
| Sociology of Education | 592 | 1963–2026 | 119 |
| Socius | 1,021 | 2016–2026 | 732 |
| Work, Employment and Society | 2,354 | 1990–2026 | 525 |

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