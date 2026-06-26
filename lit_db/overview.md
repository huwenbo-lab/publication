# 社会学与人口学文献数据库概览

> 生成时间：2026-06-27
> 总计：**44,614** 篇 | **31** 本期刊 | 1896–2026

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
| American Journal of Sociology | 928 | 1896–2026 | 188 |
| American Sociological Review | 1,110 | 1940–2026 | 226 |
| Annual Review of Sociology | 534 | 1975–2025 | 108 |
| Asian Population Studies | 432 | 2005–2026 | 137 |
| British Journal of Sociology | 1,638 | 1950–2026 | 421 |
| British Journal of Sociology of Education | 1,568 | 1980–2026 | 468 |
| Chinese Journal of Sociology | 256 | 2015–2026 | 142 |
| Chinese Sociological Review | 269 | 2011–2026 | 139 |
| Demographic Research | 1,830 | 1999–2026 | 502 |
| Demography | 1,840 | 1964–2026 | 532 |
| European Journal of Population | 751 | 1985–2026 | 205 |
| European Sociological Review | 1,393 | 1986–2026 | 405 |
| Gender & Society | 1,008 | 1987–2026 | 208 |
| Journal of Family Issues | 2,268 | 1981–2026 | 731 |
| Journal of Family Theory & Review | 732 | 2009–2026 | 289 |
| Journal of Marriage and Family | 2,447 | 1966–2026 | 532 |
| Population Studies | 3,715 | 1947–2026 | 216 |
| Population and Development Review | 1,002 | 1976–2026 | 274 |
| Research in Social Stratification and Mobility | 848 | 2001–2026 | 364 |
| Social Indicators Research | 5,938 | 1974–2026 | 1410 |
| Social Forces | 1,894 | 1929–2026 | 490 |
| Social Psychology Quarterly | 1,320 | 1979–2026 | 162 |
| Social Science Research | 2,201 | 1972–2026 | 528 |
| Sociology Compass | 1,798 | 2007–2026 | 653 |
| Sociological Science | 393 | 2014–2026 | 199 |
| Sociology | 1,843 | 1975–2026 | 474 |
| Sociology of Education | 548 | 1963–2026 | 118 |
| Socius | 1,015 | 2016–2026 | 726 |
| Advances in Life Course Research | 638 | 2000–2026 | 240 |
| Work and Occupations | 935 | 1982–2026 | 171 |
| Work, Employment and Society | 1,522 | 1990–2026 | 435 |

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