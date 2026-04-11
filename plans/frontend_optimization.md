# 前端优化与功能扩展计划

> 本文档为活文档，记录文献数据库网页端的优化方向与改进路线。
> 创建：2026-04-11
> 最近更新：2026-04-11

---

## 背景

当前 `index.html` 是一个极简的三级浏览页面（期刊 → 年份 → 文章卡片），使用纯 JS + 自定义 CSS，无任何框架。它一次性同步加载 40MB 的 `data.js`，没有任何搜索/筛选/排序/分页功能；DOI 字段存在于数据中但前端从未显示；后端虽然已经构建了 `literature.db`（SQLite FTS5，64MB），但只能通过 Python CLI 使用，网页端完全没有接入。

**目标**：让数据库**同时对 AI 友好和对人类友好**——日常想查文献的时候能直接在网页上搜（按作者、按主题），而不是每次都要打开终端跑 Python。

本文档列出可改进的方向，按"必须先做"→"高价值"→"锦上添花"分层组织，便于挑选优先级。

---

## 当前状态速览

| 项目 | 现状 | 问题 |
|---|---|---|
| 入口 | `index.html` 14KB，纯 JS | 功能极简 |
| 数据加载 | 同步加载 `data.js` (40MB) | 首屏阻塞，移动端尤甚 |
| 导航 | 期刊 → 年份 → 文章（三级点击） | 没法跨期刊找文献 |
| 搜索 | 无 | ❌ 用户痛点 |
| 字段展示 | 标题、作者、摘要 | DOI 数据有但不显示 |
| 已有资源 | `literature.db` (FTS5)、`articles.json`、`lit_db/` | 网页端均未利用 |

---

## 改进方向（按优先级分层）

### 🔴 优先级 1：性能瓶颈修复（其他所有功能的前置条件）

**问题**：`data.js` 40MB 同步加载，首屏 5–15 秒空白，移动端容易崩。任何新功能加在这上面都只会让卡顿更严重。

**三种可行方案**（任选其一）：

| 方案 | 实现复杂度 | 后续扩展性 | 备注 |
|---|---|---|---|
| **A. SQL.js + literature.db** | 中 | ⭐⭐⭐ 极佳 | 浏览器内运行 SQLite，直接复用现有 FTS5 索引；首次加载 64MB 但只下一次（可缓存到 IndexedDB）。所有搜索都走 FTS5，毫秒级。 |
| **B. 拆分 JSON + 索引** | 低 | ⭐⭐ 中等 | 把 `data.js` 按期刊拆成 25 个文件（每个 1–2MB），按需加载；额外做一个轻量 lunr.js 索引（~5MB）支持搜索。 |
| **C. Pagefind / MiniSearch** | 低 | ⭐⭐ 中等 | 用现成的静态站点搜索引擎构建预生成索引，分块下载。Pagefind 专门为 GitHub Pages 这类静态站设计。 |

**推荐：方案 A（SQL.js + literature.db）**——最大化复用已有工作、性能最好、用户体验最接近"真正的搜索引擎"。

### 🔴 优先级 2：搜索与筛选（用户的核心诉求）

性能修复后即可实现，所有功能都基于已有的 `literature.db`：

1. **顶部全局搜索框**（最重要）
   - 默认在标题 + 摘要中搜索（FTS5 已索引）
   - 支持 FTS5 语法：精确短语 `"social mobility"`、AND/OR/NOT、前缀 `educat*`
   - 输入即搜，结果按相关性排序

2. **作者搜索**
   - 单独的作者搜索框（或全局搜索的一个 tab）
   - 需要在 `build_search_db.py` 中给 `authors` 字段加 FTS5 索引（当前只索引了 title + abstract，需扩展）
   - 支持模糊匹配（"Hu Wenbo" 也能搜到 "Wenbo Hu"）

3. **多维筛选侧栏**
   - 期刊（多选 checkbox，按学科分组：综合社会学/人口学/家庭/性别/教育/中国）
   - 年份范围（双滑块 2000–2026）
   - 是否有摘要（针对早期数据）
   - 筛选条件 URL 持久化（`?journal=ASR&year_from=2015`），便于分享

4. **结果页面**
   - 列表式而非现在的"卡片墙"，每页 50 条 + 虚拟滚动
   - 关键词高亮（FTS5 的 `snippet()` / `highlight()` 函数）
   - 右上角排序：相关性 / 年份新→旧 / 期刊

5. **主题/学科入口**
   - 在首页顶部加 6 个学科色块（社会分层、婚姻家庭、人口学、教育、性别、劳动），点击进入预设筛选页
   - 学科 → 期刊 的映射可硬编码（CLAUDE.md 已有分类）

### 🟡 优先级 3：文章详情与可操作性

1. **文章详情页 / 弹窗**
   - 点击文章卡片打开模态框，显示完整摘要 + 所有元数据
   - **DOI 链接**（数据已有但前端没显示）：`https://doi.org/{doi}` 一键跳转
   - **Google Scholar 直达**：`https://scholar.google.com/scholar?q={title}` 找全文
   - **复制引用**：BibTeX / APA / MLA 格式导出（简单 JS 模板）
   - **唯一 URL**：`#doi/10.1086/xxxxx` 形式，便于书签、分享、给 AI

2. **批量收藏 / 笔记夹**
   - localStorage 暂存"收藏的文章"
   - 顶部"我的收藏"入口，可批量导出 BibTeX / CSV
   - 满足"做文献综述时收集 30 篇候选"的工作流

### 🟡 优先级 4：UX / 移动端 / 可访问性

1. **深色模式**：CSS 已使用 CSS 变量，加一个 toggle + `prefers-color-scheme` 检测即可
2. **键盘快捷键**：`/` 聚焦搜索框、`Esc` 清空、`↑↓` 选择结果、`Enter` 打开详情
3. **响应式重做**：当前只在 600px 改一行，需要在中屏（768/1024）下重新设计侧栏 → 抽屉
4. **加载状态优化**：FTS5 索引加载进度条（"正在加载检索引擎... 32MB / 64MB"）+ Service Worker 缓存

### 🟢 优先级 5：AI 友好性增强（让 AI 工具更容易抓取你的数据）

1. **每篇文章的独立可分享 URL**（同上 #doi/xxx），便于把单篇链接发给 ChatGPT/Claude
2. **JSON-LD 结构化数据**：在文章详情页注入 `schema.org/ScholarlyArticle`，提升 Google Scholar 可见度
3. **OpenSearch 描述文件**（`/opensearch.xml`）：浏览器地址栏可直接搜你的库
4. **机器可读 API 端点**：把 `articles.json` 切片成 `api/articles/{doi}.json`，让 AI 工具可通过 URL 直接拿到结构化数据
5. **`lit_db/` 暴露在前端导航里**：加一个 "AI 读这个" 入口，列出所有 markdown 索引文件的 raw URL 供复制

### 🟢 优先级 6：数据可视化（仪表盘）

1. **首页仪表盘**：
   - 25 本期刊的发文量年度趋势图（小型 sparkline）
   - 摘要覆盖率热图
   - 总篇数 / 已补全 / 缺失等指标
2. **关键词云**：从所有标题做高频词统计（去停用词），可视化"热门议题"
3. **作者排行**：发文量前 50 的作者（顺便发现领域内"高产学者"）
4. 实现库：D3.js 太重，建议 Chart.js 或纯 SVG 自绘

### 🟢 优先级 7：架构与可维护性

1. **拆分单文件**：当前 `index.html` 把 HTML/CSS/JS 都塞在一起，搜索功能加上后会爆炸
   - 拆为 `index.html` + `app.js` + `style.css` + `search.js`
   - 不引入构建工具，保持 GitHub Pages 直接部署
2. **去掉 `data.js` 与 `data.json` 重复**：如果走方案 A，`data.json/data.js` 彻底淘汰，只留 `literature.db`
3. **CI**：加一个 GitHub Action，每周跑 `update.py` + `build_search_db.py` 并自动 commit，实现"被动更新"

---

## 推荐的落地路线图

如果按照"最小可用→逐步增强"推进，建议这样排：

**Phase 1（必须先做）**：性能修复 + 基础搜索
- 在 `build_search_db.py` 中补上 `authors` FTS5 字段
- 实现方案 A：SQL.js + literature.db 加载到浏览器
- 做一个全局搜索框（标题+摘要+作者），结果列表分页

**Phase 2（一周内可见效）**：筛选 + 详情
- 期刊多选 / 年份滑块 / URL 持久化
- 文章详情模态框，加 DOI 链接 + Google Scholar + 复制 BibTeX
- 关键词高亮

**Phase 3（按兴趣增量）**：收藏夹、深色模式、快捷键、移动端、首页学科色块

**Phase 4（"博士论文级"）**：仪表盘、关键词云、JSON-LD、OpenSearch、CI 自动更新

---

## 关键文件清单

### 需要修改的现有文件
- `index.html` — 整体重构
- `build_search_db.py` — 给 FTS5 表添加 `authors` 字段
- `.gitignore` — 是否纳入 `literature.db`（前端要用就必须入库或构建时生成）
- `README.md` — 同步更新使用说明
- `使用指南.md` — 同步更新

### 可能新增的文件
- `app.js` / `search.js` / `style.css` — 拆分后的前端代码
- `sql-wasm.js` + `sql-wasm.wasm` — SQL.js 运行时（CDN 也可）
- `.github/workflows/update.yml` — 自动更新 CI

### 已有但当前未利用的资源
- `literature.db`（64MB，FTS5 索引）
- `lit_db/`（AI 检索目录）
- `articles.json`（主数据）

---

## 关键决策点（待用户确认）

1. **是否接受把 `literature.db` (64MB) 提交到 git / GitHub Pages？**
   - 接受 → 走方案 A，开发最快，用户体验最好
   - 不接受 → 走方案 B/C（拆分 JSON + 静态索引）
   - 折中 → 用 GitHub Releases 托管 `literature.db`，前端从 release URL 拉

2. **是否要保留现有的"期刊 → 年份"浏览模式？**
   - 保留作为辅助入口（推荐）
   - 还是完全用搜索取代

3. **从 Phase 1 哪一步开始动手？**
   - 全部一次性大改造（PR 体量大）
   - 还是先单独做"加一个搜索框"作为 MVP（增量小步走）

---

## 验证方案

每个 Phase 完成后的验证标准：

- **Phase 1**：在 GitHub Pages 上打开页面，5 秒内可输入搜索；搜索"education inequality China"返回结果与 `python build_search_db.py --search "education inequality China"` 一致
- **Phase 2**：从搜索结果点开任意文章，能跳转到正确的 DOI；BibTeX 导出格式可直接粘贴到 Zotero
- **Phase 3**：手机访问页面，搜索/筛选/详情三个核心功能可用且不卡
- **Phase 4**：访问 `https://huwenbo-lab.github.io/publication/api/articles/10.xxx.json` 能拿到单篇 JSON

---

## 迭代记录

- **2026-04-11**：初版，列出 7 个优先级方向 + 4 阶段路线图，等待用户对 3 个决策点的回复
