# 数据质量检查报告

> 生成时间：2026-07-30 12:10 CST
> 审计对象：当前公开主库 `articles.json`，不是本地 Web of Science XLS 归档。

## 发布快照

- 记录：**56,019** 条
- 收录期刊：**31** 本
- 年份范围：**1947–2026**
- 有摘要：**43,276** 条（77.3%）
- 缺摘要：**12,743** 条
- 有 DOI：**55,946** 条
- 唯一 DOI：**55,946** 个

## 完整性与重复

| 检查项 | 数量 | 说明 |
|---|---:|---|
| 缺标题 | 0 | 应为 0 |
| 缺作者 | 316 | 历史元数据可能缺失 |
| 缺年份 | 0 | 应为 0 |
| 缺 DOI | 73 | 无 DOI 的记录不会生成单篇 API 端点 |
| DOI 重复组 | 0 | 应为 0 |
| 同刊同年同标题候选组 | 178 | 仅作人工复核，不自动删除 |
| 非法/未来年份 | 0 | 应为 0 |
| 公开文本中的邮箱 | 0 | 应为 0 |

## 分刊统计

| 期刊 | 记录 | 年份范围 | 有摘要 | 缺 DOI |
|---|---:|---|---:|---:|
| Advances in Life Course Research | 638 | 2000–2026 | 212 | 0 |
| American Journal of Sociology | 3,152 | 1950–2026 | 2,899 | 0 |
| American Sociological Review | 3,775 | 1960–2026 | 3,041 | 0 |
| Annual Review of Sociology | 1,178 | 1975–2026 | 1,139 | 0 |
| Asian Population Studies | 436 | 2005–2026 | 417 | 0 |
| British Journal of Sociology | 1,746 | 1950–2026 | 1,245 | 0 |
| British Journal of Sociology of Education | 1,630 | 1980–2026 | 1,513 | 0 |
| Chinese Journal of Sociology | 265 | 2015–2026 | 263 | 0 |
| Chinese Sociological Review | 273 | 2011–2026 | 268 | 0 |
| Demographic Research | 1,862 | 1999–2026 | 1,822 | 6 |
| Demography | 3,406 | 1964–2026 | 3,357 | 0 |
| European Journal of Population | 765 | 1985–2026 | 297 | 0 |
| European Sociological Review | 1,421 | 1986–2026 | 1,388 | 0 |
| Gender & Society | 1,072 | 1987–2026 | 989 | 0 |
| Journal of Family Issues | 2,359 | 1980–2026 | 2,311 | 0 |
| Journal of Family Theory & Review | 753 | 2009–2026 | 540 | 0 |
| Journal of Marriage and Family | 2,578 | 1965–2026 | 2,331 | 0 |
| Population Studies | 3,715 | 1947–2026 | 2,059 | 0 |
| Population and Development Review | 1,124 | 1976–2026 | 866 | 67 |
| Research in Social Stratification and Mobility | 860 | 2001–2026 | 677 | 0 |
| Social Forces | 4,568 | 1950–2026 | 4,059 | 0 |
| Social Indicators Research | 5,938 | 1974–2026 | 942 | 0 |
| Social Psychology Quarterly | 1,320 | 1979–2026 | 1,175 | 0 |
| Social Science Research | 2,237 | 1972–2026 | 1,111 | 0 |
| Sociological Science | 403 | 2014–2026 | 390 | 0 |
| Sociology | 1,926 | 1968–2026 | 1,744 | 0 |
| Sociology Compass | 1,798 | 2007–2026 | 1,761 | 0 |
| Sociology of Education | 1,291 | 1963–2026 | 1,145 | 0 |
| Socius | 1,032 | 2016–2026 | 1,032 | 0 |
| Work and Occupations | 935 | 1982–2026 | 846 | 0 |
| Work, Employment and Society | 1,563 | 1987–2026 | 1,437 | 0 |

## 有意设置的早期档案边界

以下边界来自已确认的发布口径，不应被质量脚本当作缺失数据回填：

| 期刊 | 保留起点 | 起点前年份记录 |
|---|---:|---:|
| American Journal of Sociology | 1950 | 0 |
| American Sociological Review | 1960 | 0 |
| Social Forces | 1950 | 0 |

## 自动检查结论

**通过。** 期刊集合、DOI 唯一性、年份和早期档案边界均符合当前发布口径；同刊同年同标题候选仍需按需人工复核。
