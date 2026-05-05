# Crossref 与 OpenAlex 数据源策略建议

生成日期：2026-05-05

## 明确建议

建议采用“Crossref 作为主更新源，OpenAlex 作为补全和研究分析增强源”的组合策略，不建议完全改用 OpenAlex，也不建议只保留 Crossref。

## 判断依据

### Crossref 适合作为主更新源

- Crossref 元数据由出版社成员直接登记，特别适合按 DOI、ISSN 和期刊维度维护文章清单。
- Crossref REST API 明确支持 `/journals/{issn}/works`、`/works`、类型和日期过滤，适合当前按 25 本期刊定期抓取最新文献的流程。
- Crossref 不需要注册即可访问；polite pool 通过 `mailto` 或 `User-Agent` 标识调用方，并有明确速率和并发限制。
- Crossref 提供 DOI、标题、作者、期刊、出版日期、页码、卷期、license、references、ORCID、ROR、更新关系等出版社登记字段；这些字段对本项目后续补 `volume` / `issue` 很关键。

官方依据：

- Crossref REST API 总览：<https://www.production.crossref.org/documentation/retrieve-metadata/rest-api/>
- Crossref 访问与速率限制：<https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/>
- Crossref API 使用建议：<https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-the-crossref-rest-api/>

### OpenAlex 适合作为补全和分析增强源

- OpenAlex 不只是文献目录，还做作者、机构、来源、主题、资助、引用等实体连接和消歧，适合做作者追踪、主题探索、机构/引用/开放获取分析。
- OpenAlex 聚合多个来源，其中包括 Crossref、ORCID、ROR、DOAJ、Unpaywall、PubMed 等；因此覆盖面和关系网络比单一 Crossref 更丰富。
- OpenAlex 数据和快照是开放的，API 和 snapshot 都可用；但大规模 snapshot 体积很大，不适合当前这个轻量静态站点直接引入。
- OpenAlex API 当前需要免费 API key 才适合规模化使用；免费额度足够做补全和定期小批量查询，但不应把全量重建依赖放在无缓存的 API 调用上。

官方依据：

- OpenAlex 数据说明：<https://help.openalex.org/hc/en-us/articles/24397285563671-About-the-data>
- OpenAlex API key 与免费额度：<https://developers.openalex.org/guides/authentication>
- OpenAlex snapshot 格式与体积：<https://developers.openalex.org/download/snapshot-format>
- OpenAlex 价格和 CC0 数据说明：<https://help.openalex.org/hc/en-us/articles/24397762024087-Pricing>

## 对本项目的落地方案

1. 继续保留 `scripts/update.py` 的 Crossref 增量更新逻辑，按 ISSN 和日期抓取 25 本期刊的新 DOI。
2. Crossref 入库前继续运行非文献筛查，避免 Editorial Board、Issue Information、Book Review、Correction 等候选重新混入。
3. 新增或完善 OpenAlex dry-run 补全脚本，只对已有 DOI 做补全，不直接覆盖主数据。优先补：
   - OpenAlex work id
   - 作者 OpenAlex id / ORCID
   - institution / ROR
   - topics / concepts
   - citation count
   - open access 状态
   - referenced works / related works
4. 对 `volume` / `issue` / pages / publication date，优先使用 Crossref 和 `raw_data`，OpenAlex 只作为交叉校验来源。
5. 所有外部 API 补全都应采用 dry-run CSV、抽样复核、再 apply 的流程，避免把第三方推断字段静默写进主数据。

## 不建议完全改用 OpenAlex的原因

- 当前项目的核心是“25 本指定期刊的可审计文献数据库”，Crossref 的 DOI/ISSN/出版社登记元数据更贴近这个需求。
- OpenAlex 的优势在实体关系和分析层，而不是替代出版社原始登记元数据。
- 直接改用 OpenAlex 可能带来期刊映射、work type、作者消歧、更新延迟和字段解释差异，需要额外审计成本。

## 不建议只用 Crossref 的原因

- Crossref 的作者消歧、机构、主题、引用网络和开放获取信息不如 OpenAlex 方便。
- 本项目后续要支持作者追踪、主题发现、AI agent 研究辅助，OpenAlex 的关系型元数据更有价值。

## 结论

短期：继续 Crossref 更新，OpenAlex 做 DOI 级补全 dry-run。
中期：为 `articles.json` 增加可选增强字段，如 `openalex_id`、`author_ids`、`topics`、`cited_by_count`、`open_access`，但必须保留原 6 字段兼容。
长期：建立双源审计报告，记录每个字段来自 WoS、Crossref、OpenAlex 还是人工确认。
