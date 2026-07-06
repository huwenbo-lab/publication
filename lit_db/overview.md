# 社会学与人口学文献数据库概览

> 生成时间：2026-07-06
> 总计：**46,409** 篇 | **31** 本期刊 | 1896–2026

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
| American Journal of Sociology | 1,128 | 1896–2026 | 201 |
| American Sociological Review | 1,270 | 1936–2026 | 230 |
| Annual Review of Sociology | 641 | 1975–2026 | 126 |
| Asian Population Studies | 437 | 2005–2026 | 142 |
| British Journal of Sociology | 1,768 | 1950–2026 | 443 |
| British Journal of Sociology of Education | 1,640 | 1980–2026 | 502 |
| Chinese Journal of Sociology | 266 | 2015–2026 | 152 |
| Chinese Sociological Review | 275 | 2011–2026 | 145 |
| Demographic Research | 1,864 | 1999–2026 | 525 |
| Demography | 1,929 | 1964–2026 | 550 |
| European Journal of Population | 776 | 1985–2026 | 211 |
| European Sociological Review | 1,429 | 1986–2026 | 412 |
| Gender & Society | 1,076 | 1987–2026 | 209 |
| Journal of Family Issues | 2,370 | 1980–2026 | 761 |
| Journal of Family Theory & Review | 755 | 2009–2026 | 312 |
| Journal of Marriage and Family | 2,542 | 1965–2026 | 538 |
| Population Studies | 3,718 | 1947–2026 | 219 |
| Population and Development Review | 1,142 | 1976–2026 | 289 |
| Research in Social Stratification and Mobility | 865 | 2001–2026 | 381 |
| Social Indicators Research | 5,942 | 1974–2026 | 1412 |
| Social Forces | 2,032 | 1926–2026 | 517 |
| Social Psychology Quarterly | 1,320 | 1979–2026 | 162 |
| Social Science Research | 2,247 | 1972–2026 | 550 |
| Sociology Compass | 1,798 | 2007–2026 | 653 |
| Sociological Science | 404 | 2014–2026 | 210 |
| Sociology | 1,937 | 1968–2026 | 476 |
| Sociology of Education | 659 | 1963–2026 | 123 |
| Socius | 1,035 | 2016–2026 | 746 |
| Advances in Life Course Research | 638 | 2000–2026 | 240 |
| Work and Occupations | 935 | 1982–2026 | 171 |
| Work, Employment and Society | 1,571 | 1987–2026 | 440 |

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