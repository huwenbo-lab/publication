# 社会学与人口学文献数据库概览

> 生成时间：2026-04-02  
> 总计：**34,105** 篇 | **24** 本期刊 | 2000–2026

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
| American Journal of Sociology | 799 | 2000–2025 | 185 |
| American Sociological Review | 986 | 2000–2025 | 225 |
| Annual Review of Sociology | 428 | 2000–2025 | 97 |
| British Journal of Sociology | 1,739 | 2000–2025 | 415 |
| British Journal of Sociology of Education | 1,669 | 2000–2026 | 459 |
| Chinese Journal of Sociology | 254 | 2015–2025 | 135 |
| Chinese Sociological Review | 268 | 2011–2025 | 138 |
| Demographic Research | 1,833 | 2000–2025 | 501 |
| Demography | 1,931 | 2000–2025 | 533 |
| European Journal of Population | 850 | 2000–2026 | 219 |
| European Sociological Review | 1,543 | 2000–2025 | 401 |
| Gender & Society | 2,190 | 2000–2026 | 519 |
| Journal of Family Issues | 2,255 | 2000–2026 | 725 |
| Journal of Family Theory & Review | 842 | 2009–2026 | 337 |
| Journal of Marriage and Family | 2,467 | 2000–2025 | 531 |
| Population and Development Review | 932 | 2000–2025 | 269 |
| Research in Social Stratification and Mobility | 855 | 2001–2025 | 350 |
| Social Forces | 2,800 | 2000–2025 | 488 |
| Social Science Research | 2,259 | 2000–2026 | 524 |
| Sociological Science | 392 | 2014–2026 | 198 |
| Sociology | 2,931 | 2000–2026 | 579 |
| Sociology of Education | 457 | 2000–2026 | 113 |
| Socius | 1,039 | 2015–2026 | 744 |
| Work, Employment and Society | 2,386 | 2000–2026 | 525 |

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