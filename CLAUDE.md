# 社会学与人口学期刊文献数据库

## 项目介绍

本项目是一个社会学与人口学领域的学术文献数据库，收录24本核心期刊2000年至今的文章元数据（标题、摘要、作者、DOI等）。研究方向涵盖社会分层、婚姻与家庭、人口学。

数据来源：Web of Science导出 + CrossRef API补全。前端为静态HTML页面，部署在GitHub Pages。

## 期刊列表（24本）

| 期刊名称 | ISSN | 数据起始年 |
|---|---|---|
| American Journal of Sociology | 0002-9602 | 2000 |
| American Sociological Review | 0003-1224 | 2000 |
| Annual Review of Sociology | 0360-0572 | 2000 |
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

## 数据字段说明

`articles.json` 中每条记录包含以下字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `title` | string | 文章标题 |
| `abstract` | string | 摘要（部分文章可能为空） |
| `authors` | string | 作者列表，格式：`姓, 名; 姓, 名` |
| `journal` | string | 期刊名称（Title Case） |
| `year` | int/null | 发表年份 |
| `doi` | string | DOI标识符 |

`data.json` / `data.js` 使用旧格式字段名（`Source Title`, `Publication Year`, `Article Title`, `Author Full Names`, `Abstract`），供 `index.html` 前端使用。

## 文件结构

```
articles.json          # 主数据文件（新格式，含DOI）
data.json / data.js    # 旧格式数据（供index.html使用）
index.html             # 前端展示页面
*.xls                  # Web of Science原始导出文件（存档用）
check_quality.py       # 数据质量检查，生成 data_quality_report.md
build_articles.py      # 从XLS清洗合并为 articles.json
enrich_crossref.py     # CrossRef API补全摘要/DOI/缺失数据
update.py              # 定期更新脚本
update_log.md          # 更新日志
```

## 如何更新数据库

### 日常更新（抓取最新文章）

```bash
source venv/bin/activate
python update.py              # 默认抓取最近30天新文章
python update.py --days 60    # 抓取最近60天
python update.py --dry-run    # 仅检查，不写入
```

脚本会自动：
1. 从CrossRef查询24本期刊的最新文章
2. 按DOI去重，避免重复录入
3. 新文章追加到 `articles.json`，同步更新 `data.json` 和 `data.js`
4. 在 `update_log.md` 中记录更新详情

### 全量重建

```bash
source venv/bin/activate
python build_articles.py      # 从XLS重建（仅已有Excel的17本期刊）
python enrich_crossref.py     # CrossRef补全（摘要、DOI、历史数据、缺失期刊）
```

## 注意事项

- **API限速**: CrossRef API使用 `mailto` 参数进入polite pool，请求间隔1秒。全量补全可能需要较长时间。
- **Sociological Science**: 2014年创刊，数据从2014年开始。
- **Socius**: 2015年创刊，数据从2015年开始。
- **Chinese Journal of Sociology**: 2015年创刊（英文版），数据从2015年开始。中文期刊的英文摘要可能不完整。
- **Journal of Family Theory & Review**: 2009年创刊，数据从2009年开始。
- **摘要缺失**: 部分早期文章（尤其是书评、编辑说明等）在CrossRef中无摘要，属正常现象。
- **文件名拼写**: `British of Journal of Sociology of Education.xls` 文件名有拼写错误（多了"of"），已在处理脚本中修正映射。
- **WoS导出上限**: Web of Science单次导出最多1000条记录，部分期刊的Excel数据可能不完整。
