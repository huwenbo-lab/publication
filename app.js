const SQL_JS_BASE = "vendor/sqljs";
const PAGE_SIZE = 50;
const FAVORITES_STORAGE_KEY = "publication:favorites:v1";
const THEME_STORAGE_KEY = "publication:theme:v1";
const RAW_BASE = "https://raw.githubusercontent.com/huwenbo-lab/publication/main";

const JOURNAL_GROUPS = [
    {
        label: "综合社会学",
        journals: [
            "American Journal of Sociology",
            "American Sociological Review",
            "Annual Review of Sociology",
            "British Journal of Sociology",
            "European Sociological Review",
            "Social Forces",
            "Social Science Research",
            "Sociological Science",
            "Sociology",
            "Socius",
        ],
    },
    {
        label: "人口学",
        journals: [
            "Asian Population Studies",
            "Demographic Research",
            "Demography",
            "European Journal of Population",
            "Population and Development Review",
        ],
    },
    {
        label: "婚姻与家庭",
        journals: [
            "Journal of Family Issues",
            "Journal of Family Theory & Review",
            "Journal of Marriage and Family",
        ],
    },
    {
        label: "教育",
        journals: [
            "British Journal of Sociology of Education",
            "Sociology of Education",
        ],
    },
    {
        label: "性别",
        journals: ["Gender & Society"],
    },
    {
        label: "中国研究",
        journals: [
            "Chinese Journal of Sociology",
            "Chinese Sociological Review",
        ],
    },
    {
        label: "劳动与分层",
        journals: [
            "Research in Social Stratification and Mobility",
            "Work, Employment and Society",
        ],
    },
];

const DISCIPLINE_COPY = {
    "综合社会学": "先收敛到综合社会学核心刊，再搜理论、方法或一般性经验议题。",
    "人口学": "适合直接进入生育、死亡、迁移、家庭人口结构等人口学主题。",
    "婚姻与家庭": "聚焦婚姻、伴侣关系、代际支持、家庭形成与照料分工。",
    "教育": "优先查看教育分层、学校制度、教育机会与代际再生产。",
    "性别": "把结果限定在性别不平等、照料劳动、性别规范与交叉性研究。",
    "中国研究": "先切到中国相关英文期刊，再缩小到具体主题。",
    "劳动与分层": "适合查职业流动、阶层再生产、劳动力市场与雇佣关系。",
};

const QUICK_SEARCH_PRESETS = [
    { label: "社会流动", query: '"social mobility"' },
    { label: "生育", query: "fertility" },
    { label: "教育不平等", query: '"education inequality"' },
    { label: "婚姻家庭", query: "marriage family" },
    { label: "中国研究", query: "China stratification" },
];

const app = {
    db: null,
    facets: null,
    meta: null,
    dashboard: null,
    fallbackData: null,
    articleCache: new Map(),
    favorites: new Map(),
    engine: "loading",
    engineMessage: "正在连接浏览器内检索引擎…",
    sqliteInitError: "",
    staticIndexesLoaded: false,
    theme: "light",
    state: {
        mode: "search",
        q: "",
        journals: [],
        journalFacetQuery: "",
        yearFrom: "",
        yearTo: "",
        hasAbstractOnly: false,
        sort: "relevance",
        page: 1,
        browseJournal: "",
        browseYear: "",
        browseJournalQuery: "",
        activeArticleKey: "",
        activeArticleDoi: "",
        favoritesOpen: false,
        activeResultKey: "",
        dashboardOpen: false,
    },
};

const dom = {};
let searchDebounceId = null;

function $(id) {
    return document.getElementById(id);
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function renderHighlightedSnippet(text) {
    const tokenized = String(text ?? "")
        .replaceAll("<mark>", "%%MARK_OPEN%%")
        .replaceAll("</mark>", "%%MARK_CLOSE%%");
    return escapeHtml(tokenized)
        .replaceAll("%%MARK_OPEN%%", "<mark>")
        .replaceAll("%%MARK_CLOSE%%", "</mark>");
}

function formatNumber(value) {
    return new Intl.NumberFormat("zh-CN").format(value ?? 0);
}

function formatPercent(value) {
    const numeric = Number(value || 0);
    const percent = numeric * 100;
    const digits = Math.abs(percent - Math.round(percent)) < 0.05 ? 0 : 1;
    return `${percent.toFixed(digits)}%`;
}

function formatTimestamp(value) {
    if (!value) {
        return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return String(value);
    }
    return new Intl.DateTimeFormat("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    }).format(date);
}

function normalizeText(value) {
    return String(value ?? "")
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim();
}

function truncateText(value, maxChars = 280) {
    const text = String(value ?? "").trim();
    if (!text) {
        return "";
    }
    if (text.length <= maxChars) {
        return text;
    }
    return `${text.slice(0, maxChars).trim()}…`;
}

function buildDoiUrl(doi) {
    const clean = String(doi ?? "").trim();
    return clean ? `https://doi.org/${encodeURIComponent(clean)}` : "";
}

function buildScholarUrl(title) {
    return `https://scholar.google.com/scholar?q=${encodeURIComponent(title ?? "")}`;
}

function buildShareUrl(article) {
    const url = new URL(window.location.href);
    url.hash = article?.doi ? `doi/${encodeURIComponent(article.doi)}` : "";
    return url.toString();
}

function buildAppBaseUrl() {
    return new URL(".", window.location.href);
}

function safeJournalFilename(name) {
    return String(name ?? "")
        .replaceAll("&", "and")
        .replaceAll(",", "")
        .replace(/[^\w\s-]/g, "")
        .trim()
        .replace(/\s+/g, "_");
}

function getPeriodKey(year) {
    const numericYear = Number(year || 0);
    if (numericYear >= 2020 && numericYear <= 2026) {
        return "2020_2026";
    }
    if (numericYear >= 2010 && numericYear <= 2019) {
        return "2010_2019";
    }
    if (numericYear >= 2000 && numericYear <= 2009) {
        return "2000_2009";
    }
    return "";
}

function buildRepoRawUrl(relativePath) {
    return `${RAW_BASE}/${relativePath}`;
}

function buildArticleApiPath(doi) {
    const clean = String(doi ?? "")
        .replace(/^https?:\/\/doi\.org\//i, "")
        .toLowerCase()
        .trim();
    if (!clean) {
        return "";
    }
    const segments = clean
        .split("/")
        .filter(Boolean)
        .map((segment) => encodeURIComponent(segment));
    if (!segments.length) {
        return "";
    }
    const last = `${segments.pop()}.json`;
    return `api/articles/${[...segments, last].join("/")}`;
}

function buildArticleApiUrl(doi) {
    const relativePath = buildArticleApiPath(doi);
    return relativePath ? new URL(relativePath, buildAppBaseUrl()).toString() : "";
}

async function fetchJsonResource(relativePath) {
    const response = await fetch(relativePath, { cache: "no-cache" });
    if (!response.ok) {
        throw new Error(`${relativePath} 不可用 (${response.status})`);
    }
    return response.json();
}

function buildAiResourceLinks(article) {
    const journalSlug = safeJournalFilename(article.journal);
    const period = getPeriodKey(article.year);
    return {
        overview: buildRepoRawUrl("lit_db/overview.md"),
        journalTitles: journalSlug
            ? buildRepoRawUrl(`lit_db/titles/by_journal/${journalSlug}.md`)
            : "",
        journalAbstracts: journalSlug && period
            ? buildRepoRawUrl(`lit_db/abstracts/${period}/${journalSlug}.md`)
            : "",
        articleJson: buildArticleApiUrl(article.doi),
    };
}

function buildAiPrompt(article, resources) {
    const lines = [
        "请基于以下资料分析这篇文章，并优先引用文章 JSON 中的结构化字段：",
    ];
    if (resources.articleJson) {
        lines.push(`1. 文章 JSON：${resources.articleJson}`);
    }
    if (resources.journalTitles) {
        lines.push(`2. 本刊标题索引：${resources.journalTitles}`);
    }
    if (resources.journalAbstracts) {
        lines.push(`3. 同年份段摘要索引：${resources.journalAbstracts}`);
    }
    lines.push(`4. 数据库总览：${resources.overview}`);
    lines.push("");
    lines.push(`文章：${article.title || "无标题"}${article.year ? `（${article.year}）` : ""}`);
    return lines.join("\n");
}

function clearArticleSchema() {
    if (dom.articleSchema) {
        dom.articleSchema.textContent = "";
    }
}

function renderArticleSchema(article, shareUrl, apiUrl) {
    if (!dom.articleSchema) {
        return;
    }
    const doiUrl = buildDoiUrl(article.doi);
    const schema = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        headline: article.title || "无标题",
        name: article.title || "无标题",
        abstract: article.abstract || "",
        author: parseAuthorList(article.authors).map((author) => ({
            "@type": "Person",
            name: author,
        })),
        isPartOf: {
            "@type": "Periodical",
            name: article.journal || "未知期刊",
        },
        datePublished: article.year ? String(article.year) : "",
        identifier: article.doi ? [{
            "@type": "PropertyValue",
            propertyID: "DOI",
            value: article.doi,
        }] : [],
        url: shareUrl || apiUrl || doiUrl || "",
        sameAs: doiUrl || apiUrl || "",
    };
    dom.articleSchema.textContent = JSON.stringify(schema, null, 2);
}

function readStorage(key) {
    try {
        return window.localStorage.getItem(key);
    } catch {
        return null;
    }
}

function writeStorage(key, value) {
    try {
        window.localStorage.setItem(key, value);
    } catch {
        return;
    }
}

function normalizeArticleRecord(record) {
    return {
        title: String(record.title ?? "").trim(),
        authors: String(record.authors ?? "").trim(),
        journal: String(record.journal ?? "").trim(),
        year: record.year ? Number(record.year) : "",
        doi: String(record.doi ?? "").trim(),
        abstract: String(record.abstract ?? "").trim(),
    };
}

function buildArticleKey(article) {
    if (article.doi) {
        return `doi:${article.doi.toLowerCase()}`;
    }
    return `local:${normalizeText(article.journal)}|${article.year || ""}|${normalizeText(article.title)}`;
}

function rememberArticle(record) {
    const article = normalizeArticleRecord(record);
    const key = buildArticleKey(article);
    app.articleCache.set(key, article);
    return key;
}

function compareArticles(a, b) {
    const yearDiff = Number(b.year || 0) - Number(a.year || 0);
    if (yearDiff !== 0) {
        return yearDiff;
    }
    const journalDiff = String(a.journal || "").localeCompare(String(b.journal || ""));
    if (journalDiff !== 0) {
        return journalDiff;
    }
    return String(a.title || "").localeCompare(String(b.title || ""));
}

function loadFavoritesFromStorage() {
    app.favorites.clear();
    const raw = readStorage(FAVORITES_STORAGE_KEY);
    if (!raw) {
        return;
    }
    try {
        const items = JSON.parse(raw);
        if (!Array.isArray(items)) {
            return;
        }
        for (const item of items) {
            const article = normalizeArticleRecord(item);
            const key = buildArticleKey(article);
            app.favorites.set(key, article);
            app.articleCache.set(key, article);
        }
    } catch {
        return;
    }
}

function saveFavoritesToStorage() {
    writeStorage(
        FAVORITES_STORAGE_KEY,
        JSON.stringify([...app.favorites.values()].sort(compareArticles))
    );
}

function getFavoriteArticles() {
    return [...app.favorites.values()].sort(compareArticles);
}

function isFavorite(articleKey) {
    return app.favorites.has(articleKey);
}

function toggleFavorite(recordOrKey) {
    const article = typeof recordOrKey === "string"
        ? app.articleCache.get(recordOrKey)
        : normalizeArticleRecord(recordOrKey);
    if (!article) {
        return false;
    }
    const key = buildArticleKey(article);
    app.articleCache.set(key, article);
    if (app.favorites.has(key)) {
        app.favorites.delete(key);
        saveFavoritesToStorage();
        return false;
    }
    app.favorites.set(key, article);
    saveFavoritesToStorage();
    return true;
}

function escapeCsvCell(value) {
    const text = String(value ?? "");
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function buildFavoritesBibtex() {
    return getFavoriteArticles().map(formatBibtex).join("\n\n");
}

function buildFavoritesCsv() {
    const rows = [
        ["title", "authors", "journal", "year", "doi", "abstract"],
        ...getFavoriteArticles().map((article) => ([
            article.title,
            article.authors,
            article.journal,
            article.year,
            article.doi,
            article.abstract,
        ])),
    ];
    return rows.map((row) => row.map(escapeCsvCell).join(",")).join("\n");
}

function buildExportFilename(ext) {
    const stamp = new Date().toISOString().slice(0, 10);
    return `favorites-${stamp}.${ext}`;
}

function downloadTextFile(filename, text, mimeType) {
    const blob = new Blob([text], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

function detectPreferredTheme() {
    return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function renderThemeToggle() {
    if (!dom.themeToggle) {
        return;
    }
    dom.themeToggle.textContent = `主题：${app.theme === "dark" ? "深色" : "浅色"}`;
    dom.themeToggle.setAttribute("aria-pressed", app.theme === "dark" ? "true" : "false");
}

function applyTheme(theme) {
    app.theme = theme === "dark" ? "dark" : "light";
    document.body.dataset.theme = app.theme;
    renderThemeToggle();
}

function loadClientPreferences() {
    loadFavoritesFromStorage();
    const storedTheme = readStorage(THEME_STORAGE_KEY);
    applyTheme(storedTheme === "dark" || storedTheme === "light" ? storedTheme : detectPreferredTheme());
}

function parseAuthorList(authors) {
    return String(authors || "")
        .split(";")
        .map((item) => item.trim())
        .filter(Boolean);
}

function formatAuthorInitials(author) {
    const [familyRaw = "", givenRaw = ""] = String(author || "").split(",").map((item) => item.trim());
    if (!familyRaw) {
        return author;
    }
    const initials = givenRaw
        .split(/\s+/)
        .filter(Boolean)
        .map((part) => `${part[0]?.toUpperCase() || ""}.`)
        .join(" ");
    return initials ? `${familyRaw}, ${initials}` : familyRaw;
}

function formatApaAuthors(authors) {
    const names = parseAuthorList(authors).map(formatAuthorInitials);
    if (!names.length) {
        return "未知作者";
    }
    if (names.length === 1) {
        return names[0];
    }
    if (names.length === 2) {
        return `${names[0]} & ${names[1]}`;
    }
    return `${names.slice(0, -1).join(", ")}, & ${names[names.length - 1]}`;
}

function formatMlaAuthors(authors) {
    const names = parseAuthorList(authors);
    if (!names.length) {
        return "未知作者";
    }
    if (names.length === 1) {
        return names[0];
    }
    if (names.length === 2) {
        return `${names[0]}, and ${names[1]}`;
    }
    return `${names[0]}, et al.`;
}

function buildCitationKey(article) {
    const firstAuthor = parseAuthorList(article.authors)[0] || "article";
    const family = (firstAuthor.split(",")[0] || "article").replace(/[^\w]+/g, "");
    const titleWord = (normalizeText(article.title).split(/\s+/)[0] || "entry").replace(/[^\w]+/g, "");
    return `${family || "article"}${article.year || "nd"}${titleWord || "entry"}`;
}

function formatBibtex(article) {
    const lines = [
        `@article{${buildCitationKey(article)},`,
        `  title = {${article.title || "Untitled"}},`,
        `  author = {${parseAuthorList(article.authors).join(" and ") || "Unknown"}},`,
        `  journal = {${article.journal || "Unknown Journal"}},`,
    ];
    if (article.year) {
        lines.push(`  year = {${article.year}},`);
    }
    if (article.doi) {
        lines.push(`  doi = {${article.doi}},`);
        lines.push(`  url = {${buildDoiUrl(article.doi)}}`);
    } else {
        lines[lines.length - 1] = lines[lines.length - 1].replace(/,$/, "");
    }
    lines.push("}");
    return lines.join("\n");
}

function formatApa(article) {
    const parts = [
        `${formatApaAuthors(article.authors)}.`,
        article.year ? ` (${article.year}).` : "",
        ` ${article.title || "无标题"}.`,
        article.journal ? ` ${article.journal}.` : "",
        article.doi ? ` ${buildDoiUrl(article.doi)}` : "",
    ];
    return parts.join("").replace(/\s+/g, " ").trim();
}

function formatMla(article) {
    const parts = [
        `${formatMlaAuthors(article.authors)}.`,
        ` "${article.title || "无标题"}."`,
        article.journal ? ` ${article.journal},` : "",
        article.year ? ` ${article.year},` : "",
        article.doi ? ` ${buildDoiUrl(article.doi)}.` : "",
    ];
    return parts.join("").replace(/\s+/g, " ").trim();
}

async function copyText(text) {
    if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return;
    }
    const area = document.createElement("textarea");
    area.value = text;
    document.body.append(area);
    area.select();
    document.execCommand("copy");
    area.remove();
}

function cacheDom() {
    dom.datasetMeta = $("dataset-meta");
    dom.engineBadge = $("engine-badge");
    dom.engineMessage = $("engine-message");
    dom.themeToggle = $("theme-toggle");
    dom.favoritesToggle = $("favorites-toggle");
    dom.dashboardToggle = $("dashboard-toggle");
    dom.disciplineGrid = $("discipline-grid");
    dom.dashboardPanel = $("dashboard-panel");
    dom.dashboardClose = $("dashboard-close");
    dom.dashboardGeneratedAt = $("dashboard-generated-at");
    dom.dashboardSummary = $("dashboard-summary");
    dom.dashboardTrendMeta = $("dashboard-trend-meta");
    dom.dashboardTrend = $("dashboard-trend");
    dom.dashboardKeywords = $("dashboard-keywords");
    dom.dashboardAuthors = $("dashboard-authors");
    dom.dashboardJournals = $("dashboard-journals");
    dom.tabbar = $("tabbar");
    dom.searchView = $("view-search");
    dom.browseView = $("view-browse");
    dom.searchForm = $("search-form");
    dom.searchInput = $("search-input");
    dom.quickSearches = $("quick-searches");
    dom.sortSelect = $("sort-select");
    dom.yearFrom = $("year-from");
    dom.yearTo = $("year-to");
    dom.hasAbstractOnly = $("has-abstract-only");
    dom.journalFilterQuery = $("journal-filter-query");
    dom.journalFilterSummary = $("journal-filter-summary");
    dom.filterContainer = $("journal-filters");
    dom.activeFilters = $("active-filters");
    dom.resultSummary = $("result-summary");
    dom.resultList = $("result-list");
    dom.pagination = $("pagination");
    dom.clearFilters = $("clear-filters");
    dom.clearQuery = $("clear-query");
    dom.searchNotice = $("search-notice");
    dom.browseStatus = $("browse-status");
    dom.browseBreadcrumbs = $("browse-breadcrumbs");
    dom.browseJournalQuery = $("browse-journal-query");
    dom.browseJournalSummary = $("browse-journal-summary");
    dom.journalRail = $("journal-rail");
    dom.yearGrid = $("year-grid");
    dom.articleList = $("browse-article-list");
    dom.browseReset = $("browse-reset");
    dom.modal = $("article-modal");
    dom.modalTitle = $("modal-title");
    dom.modalKicker = $("modal-kicker");
    dom.modalMeta = $("modal-meta");
    dom.modalAuthors = $("modal-authors");
    dom.modalActions = $("modal-actions");
    dom.modalAbstract = $("modal-abstract");
    dom.modalClose = $("modal-close");
    dom.citationBibtex = $("citation-bibtex");
    dom.citationApa = $("citation-apa");
    dom.citationMla = $("citation-mla");
    dom.aiLinks = $("ai-links");
    dom.aiPrompt = $("ai-prompt");
    dom.articleSchema = $("article-schema");
    dom.favoritesModal = $("favorites-modal");
    dom.favoritesSummary = $("favorites-summary");
    dom.favoritesList = $("favorites-list");
    dom.favoritesClose = $("favorites-close");
    dom.copyFavoritesBibtex = $("copy-favorites-bibtex");
    dom.exportFavoritesBibtex = $("export-favorites-bibtex");
    dom.exportFavoritesCsv = $("export-favorites-csv");
    dom.clearFavorites = $("clear-favorites");
}

function renderFavoriteButton(articleKey, label = "") {
    const active = isFavorite(articleKey);
    const buttonLabel = label || (active ? "已收藏" : "收藏");
    return `
        <button
            type="button"
            class="result-link button-link favorite-toggle ${active ? "active" : ""}"
            data-favorite-article="${escapeHtml(articleKey)}"
            aria-pressed="${active ? "true" : "false"}"
        >${escapeHtml(buttonLabel)}</button>
    `;
}

function getAvailableJournalsForGroup(group) {
    if (!app.facets) {
        return [...group.journals];
    }
    const allowed = new Set(app.facets.map((facet) => facet.journal));
    return group.journals.filter((journal) => allowed.has(journal));
}

function renderDisciplinePresets() {
    if (!dom.disciplineGrid) {
        return;
    }
    dom.disciplineGrid.innerHTML = JOURNAL_GROUPS.map((group) => {
        const journals = getAvailableJournalsForGroup(group);
        const stats = app.facets
            ? app.facets.filter((facet) => journals.includes(facet.journal))
            : [];
        const articleCount = stats.reduce((sum, item) => sum + Number(item.total || 0), 0);
        const meta = articleCount
            ? `${formatNumber(articleCount)} 篇 · ${journals.length} 本期刊`
            : `${journals.length} 本期刊`;
        return `
            <button type="button" class="discipline-card" data-discipline-filter="${escapeHtml(group.label)}">
                <span class="discipline-kicker">预设筛选</span>
                <strong>${escapeHtml(group.label)}</strong>
                <span class="discipline-body">${escapeHtml(DISCIPLINE_COPY[group.label] || "按学科快速限定期刊范围。")}</span>
                <span class="discipline-meta">${escapeHtml(meta)}</span>
            </button>
        `;
    }).join("");
}

function renderQuickSearches() {
    if (!dom.quickSearches) {
        return;
    }
    dom.quickSearches.innerHTML = QUICK_SEARCH_PRESETS.map((item) => `
        <button type="button" class="quick-search-chip" data-quick-query="${escapeHtml(item.query)}">
            <strong>${escapeHtml(item.label)}</strong>
            <span>${escapeHtml(item.query)}</span>
        </button>
    `).join("");
}

function clearActiveNavigationSelection() {
    app.state.activeResultKey = "";
}

function getNavigationButtons() {
    if (app.state.favoritesOpen) {
        return [...dom.favoritesList.querySelectorAll("[data-nav-article]")];
    }
    if (app.state.mode === "search") {
        return [...dom.resultList.querySelectorAll("[data-nav-article]")];
    }
    if (app.state.mode === "browse") {
        return [...dom.articleList.querySelectorAll("[data-nav-article]")];
    }
    return [];
}

function syncActiveNavigationButtons() {
    const buttons = getNavigationButtons();
    let matched = false;
    buttons.forEach((button) => {
        const active = button.dataset.navArticle === app.state.activeResultKey;
        button.classList.toggle("is-selected", active);
        button.setAttribute("aria-current", active ? "true" : "false");
        if (active) {
            matched = true;
        }
    });
    if (!matched) {
        app.state.activeResultKey = "";
    }
}

function setActiveNavigationKey(articleKey, options = {}) {
    const { focus = false, behavior = "smooth" } = options;
    app.state.activeResultKey = articleKey || "";
    syncActiveNavigationButtons();
    if (!focus || !articleKey) {
        return;
    }
    const button = getNavigationButtons().find((item) => item.dataset.navArticle === articleKey);
    if (!button) {
        return;
    }
    button.focus({ preventScroll: true });
    button.scrollIntoView({ block: "nearest", behavior });
}

function moveActiveNavigation(direction) {
    const buttons = getNavigationButtons();
    if (!buttons.length) {
        return false;
    }
    const currentIndex = buttons.findIndex((button) => button.dataset.navArticle === app.state.activeResultKey);
    const nextIndex = currentIndex === -1
        ? (direction > 0 ? 0 : buttons.length - 1)
        : Math.max(0, Math.min(buttons.length - 1, currentIndex + direction));
    setActiveNavigationKey(buttons[nextIndex].dataset.navArticle, { focus: true });
    return true;
}

function hydrateStateFromUrl() {
    const params = new URLSearchParams(window.location.search);
    app.state.mode = params.get("mode") === "browse" ? "browse" : "search";
    app.state.q = params.get("q") ?? "";
    app.state.journals = params.getAll("journal").filter(Boolean);
    app.state.yearFrom = params.get("year_from") ?? "";
    app.state.yearTo = params.get("year_to") ?? "";
    app.state.hasAbstractOnly = params.get("has_abstract") === "1";
    app.state.sort = params.get("sort") || "relevance";
    app.state.page = Math.max(1, Number.parseInt(params.get("page") || "1", 10));
    app.state.browseJournal = params.get("browse_journal") ?? "";
    app.state.browseYear = params.get("browse_year") ?? "";
    app.state.activeArticleDoi = parseArticleHash();
    app.state.activeArticleKey = app.state.activeArticleDoi
        ? `doi:${app.state.activeArticleDoi.toLowerCase()}`
        : "";
    app.state.favoritesOpen = false;
    app.state.activeResultKey = "";
}

function syncUrl() {
    const params = new URLSearchParams();
    if (app.state.mode !== "search") {
        params.set("mode", app.state.mode);
    }
    if (app.state.q.trim()) {
        params.set("q", app.state.q.trim());
    }
    app.state.journals.forEach((journal) => params.append("journal", journal));
    if (app.state.yearFrom) {
        params.set("year_from", app.state.yearFrom);
    }
    if (app.state.yearTo) {
        params.set("year_to", app.state.yearTo);
    }
    if (app.state.hasAbstractOnly) {
        params.set("has_abstract", "1");
    }
    if (app.state.sort && app.state.sort !== "relevance") {
        params.set("sort", app.state.sort);
    }
    if (app.state.page > 1) {
        params.set("page", String(app.state.page));
    }
    if (app.state.browseJournal) {
        params.set("browse_journal", app.state.browseJournal);
    }
    if (app.state.browseYear) {
        params.set("browse_year", String(app.state.browseYear));
    }
    const queryPart = params.toString() ? `?${params.toString()}` : "";
    const hashPart = app.state.activeArticleDoi
        ? `#doi/${encodeURIComponent(app.state.activeArticleDoi)}`
        : "";
    const next = `${window.location.pathname}${queryPart}${hashPart}`;
    window.history.replaceState({}, "", next);
}

function parseArticleHash() {
    const hash = window.location.hash || "";
    if (!hash.startsWith("#doi/")) {
        return "";
    }
    try {
        return decodeURIComponent(hash.slice(5));
    } catch {
        return "";
    }
}

async function initSqliteEngine() {
    if (typeof initSqlJs !== "function") {
        throw new Error("SQL.js runtime 未加载。");
    }
    const SQL = await initSqlJs({
        locateFile: (file) => `${SQL_JS_BASE}/${file}`,
    });
    const response = await fetch("literature.db", { cache: "no-cache" });
    if (!response.ok) {
        throw new Error(`literature.db 不可用 (${response.status})`);
    }
    const bytes = new Uint8Array(await response.arrayBuffer());
    app.db = new SQL.Database(bytes);
    app.meta = loadMetaFromDb();
    app.facets = loadFacetsFromDb();
    app.engine = "sqlite";
    app.engineMessage = "已启用浏览器内 SQLite FTS5，可直接搜标题、摘要和作者。";
    app.sqliteInitError = "";
}

function buildSqliteFailureMessage(error) {
    const message = String(error?.message || "").trim();
    if (!message) {
        return "浏览器内 SQLite 初始化失败，页面已回退到备用 JSON 模式。";
    }
    if (message.includes("literature.db 不可用")) {
        return `当前部署没有成功提供 literature.db。${message}`;
    }
    if (message.includes("SQL.js runtime 未加载")) {
        return "SQLite 运行时没有正常加载，页面已回退到备用 JSON 模式。";
    }
    return `浏览器内 SQLite 初始化失败，页面已回退到备用 JSON 模式。${message}`;
}

function queryDb(sql, params = {}) {
    const statement = app.db.prepare(sql);
    const rows = [];
    try {
        statement.bind(params);
        while (statement.step()) {
            rows.push(statement.getAsObject());
        }
    } finally {
        statement.free();
    }
    return rows;
}

function loadMetaFromDb() {
    const row = queryDb(`
        SELECT
            COUNT(*) AS total,
            COUNT(DISTINCT m.journal) AS journals,
            MIN(m.year) AS min_year,
            MAX(m.year) AS max_year,
            SUM(CASE WHEN TRIM(COALESCE(articles.abstract, '')) <> '' THEN 1 ELSE 0 END) AS with_abstract
        FROM articles
        JOIN articles_meta m ON m.rowid = articles.rowid
    `)[0];

    const total = Number(row.total || 0);
    const withAbstract = Number(row.with_abstract || 0);
    return {
        total,
        journals: Number(row.journals || 0),
        minYear: Number(row.min_year || 0),
        maxYear: Number(row.max_year || 0),
        withAbstract,
        missingAbstract: total - withAbstract,
    };
}

function loadFacetsFromDb() {
    const rows = queryDb(`
        SELECT
            journal,
            COUNT(*) AS total,
            MIN(year) AS min_year,
            MAX(year) AS max_year
        FROM articles_meta
        GROUP BY journal
        ORDER BY journal COLLATE NOCASE ASC
    `);

    return rows.map((row) => ({
        journal: row.journal,
        total: Number(row.total || 0),
        minYear: Number(row.min_year || 0),
        maxYear: Number(row.max_year || 0),
    }));
}

function buildMetaFromSummary(summary) {
    if (!summary) {
        return null;
    }
    return {
        total: Number(summary.total_articles || 0),
        journals: Number(summary.total_journals || 0),
        minYear: Number(summary.year_min || 0),
        maxYear: Number(summary.year_max || 0),
        withAbstract: Number(summary.articles_with_abstract || 0),
        missingAbstract: Number(summary.articles_missing_abstract || 0),
    };
}

function buildFacetsFromStaticIndex(payload) {
    const journals = payload?.journals;
    if (!Array.isArray(journals)) {
        return null;
    }
    return journals.map((item) => ({
        journal: item.journal,
        total: Number(item.count || 0),
        minYear: Number(item.year_min || 0),
        maxYear: Number(item.year_max || 0),
    }));
}

async function loadStaticIndexes() {
    if (app.staticIndexesLoaded) {
        return;
    }
    app.staticIndexesLoaded = true;
    const [overviewResult, journalsResult, dashboardResult] = await Promise.allSettled([
        fetchJsonResource("api/overview.json"),
        fetchJsonResource("api/journals.json"),
        fetchJsonResource("api/dashboard.json"),
    ]);

    if (dashboardResult.status === "fulfilled") {
        app.dashboard = dashboardResult.value;
    }

    if (!app.meta) {
        const summary = app.dashboard?.summary ||
            (overviewResult.status === "fulfilled" ? overviewResult.value?.summary : null);
        app.meta = buildMetaFromSummary(summary);
    }

    if (!app.facets && journalsResult.status === "fulfilled") {
        app.facets = buildFacetsFromStaticIndex(journalsResult.value);
    }
}

async function ensureFallbackData() {
    if (app.fallbackData) {
        return;
    }
    app.engineMessage = "正在加载备用 JSON 数据（约 40MB）…";
    renderEngineStatus();
    const response = await fetch("data.json", { cache: "no-cache" });
    if (!response.ok) {
        throw new Error(`data.json 不可用 (${response.status})`);
    }

    app.fallbackData = await response.json();
    const journalStats = new Map();
    let withAbstract = 0;
    let minYear = Number.POSITIVE_INFINITY;
    let maxYear = Number.NEGATIVE_INFINITY;

    for (const item of app.fallbackData) {
        const journal = String(item["Source Title"] || "").trim();
        const year = Number.parseInt(item["Publication Year"], 10);
        const hasAbstract = String(item["Abstract"] || "").trim().length > 0;
        if (hasAbstract) {
            withAbstract += 1;
        }
        if (!Number.isNaN(year)) {
            minYear = Math.min(minYear, year);
            maxYear = Math.max(maxYear, year);
        }
        if (!journal) {
            continue;
        }
        if (!journalStats.has(journal)) {
            journalStats.set(journal, {
                journal,
                total: 0,
                minYear: Number.POSITIVE_INFINITY,
                maxYear: Number.NEGATIVE_INFINITY,
            });
        }
        const stat = journalStats.get(journal);
        stat.total += 1;
        if (!Number.isNaN(year)) {
            stat.minYear = Math.min(stat.minYear, year);
            stat.maxYear = Math.max(stat.maxYear, year);
        }
    }

    app.meta = {
        total: app.fallbackData.length,
        journals: journalStats.size,
        minYear: Number.isFinite(minYear) ? minYear : 0,
        maxYear: Number.isFinite(maxYear) ? maxYear : 0,
        withAbstract,
        missingAbstract: app.fallbackData.length - withAbstract,
    };
    app.facets = [...journalStats.values()]
        .map((stat) => ({
            ...stat,
            minYear: Number.isFinite(stat.minYear) ? stat.minYear : "",
            maxYear: Number.isFinite(stat.maxYear) ? stat.maxYear : "",
        }))
        .sort((a, b) => a.journal.localeCompare(b.journal));
    app.engineMessage = "当前使用备用 JSON 数据。浏览与基础搜索可用，但不支持完整 FTS5 语法与毫秒级响应。";
}

async function initDataSources() {
    try {
        await initSqliteEngine();
    } catch (error) {
        console.warn(error);
        app.engine = "fallback";
        app.sqliteInitError = String(error?.message || "");
        app.engineMessage = buildSqliteFailureMessage(error);
    }
    try {
        await loadStaticIndexes();
    } catch (error) {
        console.warn(error);
    }
}

async function findArticleByDoi(doi) {
    const cleanDoi = String(doi || "").trim();
    if (!cleanDoi) {
        return null;
    }
    const key = `doi:${cleanDoi.toLowerCase()}`;
    if (app.articleCache.has(key)) {
        return app.articleCache.get(key);
    }

    if (app.engine === "sqlite" && app.db) {
        const row = queryDb(`
            SELECT
                title,
                authors,
                journal,
                year,
                doi,
                abstract
            FROM articles
            WHERE lower(doi) = lower($doi)
            LIMIT 1
        `, { $doi: cleanDoi })[0];
        if (row) {
            rememberArticle(row);
            return app.articleCache.get(key);
        }
        return null;
    }

    await ensureFallbackData();
    const row = app.fallbackData.find((item) =>
        String(item["DOI"] || "").trim().toLowerCase() === cleanDoi.toLowerCase()
    );
    if (!row) {
        return null;
    }
    rememberArticle({
        title: row["Article Title"],
        authors: row["Author Full Names"],
        journal: row["Source Title"],
        year: row["Publication Year"],
        doi: row["DOI"],
        abstract: row["Abstract"],
    });
    return app.articleCache.get(key);
}

function closeArticleModalState() {
    app.state.activeArticleKey = "";
    app.state.activeArticleDoi = "";
}

function openArticleModalState(record) {
    const key = rememberArticle(record);
    const article = app.articleCache.get(key);
    app.state.activeArticleKey = key;
    app.state.activeArticleDoi = article?.doi || "";
}

function closeFavoritesModalState() {
    app.state.favoritesOpen = false;
}

function openFavoritesModalState() {
    closeArticleModalState();
    app.state.favoritesOpen = true;
}

function syncOverlayLock() {
    const articleOpen = !dom.modal.classList.contains("hidden");
    const favoritesOpen = !dom.favoritesModal.classList.contains("hidden");
    document.body.classList.toggle("modal-open", articleOpen || favoritesOpen);
}

function setModalOpen(isOpen) {
    dom.modal.classList.toggle("hidden", !isOpen);
    dom.modal.setAttribute("aria-hidden", isOpen ? "false" : "true");
    syncOverlayLock();
}

function setFavoritesModalOpen(isOpen) {
    dom.favoritesModal.classList.toggle("hidden", !isOpen);
    dom.favoritesModal.setAttribute("aria-hidden", isOpen ? "false" : "true");
    syncOverlayLock();
}

async function renderArticleModal() {
    if (!app.state.activeArticleKey && !app.state.activeArticleDoi) {
        dom.aiLinks.innerHTML = "";
        dom.aiPrompt.textContent = "";
        clearArticleSchema();
        setModalOpen(false);
        return;
    }

    let article = app.state.activeArticleKey
        ? app.articleCache.get(app.state.activeArticleKey)
        : null;

    if (!article && app.state.activeArticleDoi) {
        article = await findArticleByDoi(app.state.activeArticleDoi);
        if (article) {
            app.state.activeArticleKey = buildArticleKey(article);
        }
    }

    if (!article) {
        closeArticleModalState();
        dom.aiLinks.innerHTML = "";
        dom.aiPrompt.textContent = "";
        clearArticleSchema();
        setModalOpen(false);
        return;
    }

    const articleKey = buildArticleKey(article);
    const doiUrl = buildDoiUrl(article.doi);
    const shareUrl = buildShareUrl(article);
    const apiUrl = buildArticleApiUrl(article.doi);
    const aiResources = buildAiResourceLinks(article);
    const aiPrompt = buildAiPrompt(article, aiResources);
    const copyLinkLabel = article.doi ? "复制可分享链接" : "复制当前页面链接";
    dom.modalKicker.textContent = `${article.journal || "未知期刊"} · ${article.year || "年份未知"}`;
    dom.modalTitle.textContent = article.title || "无标题";
    dom.modalMeta.innerHTML = `
        <strong>期刊：</strong>${escapeHtml(article.journal || "未知")}　
        <strong>年份：</strong>${escapeHtml(article.year || "未知")}　
        <strong>DOI：</strong>${article.doi ? escapeHtml(article.doi) : "无"}
    `;
    dom.modalAuthors.textContent = article.authors || "未知作者";
    dom.modalActions.innerHTML = `
        ${renderFavoriteButton(articleKey, isFavorite(articleKey) ? "已收藏" : "加入收藏")}
        ${doiUrl ? `<a class="result-link" href="${doiUrl}" target="_blank" rel="noreferrer">打开 DOI</a>` : ""}
        <a class="result-link" href="${buildScholarUrl(article.title)}" target="_blank" rel="noreferrer">Google Scholar</a>
        <button type="button" class="result-link button-link" data-copy-link="true">${copyLinkLabel}</button>
    `;
    dom.modalAbstract.textContent = article.abstract || "暂无摘要。";
    dom.citationBibtex.textContent = formatBibtex(article);
    dom.citationApa.textContent = formatApa(article);
    dom.citationMla.textContent = formatMla(article);
    dom.aiLinks.innerHTML = `
        ${aiResources.articleJson ? `<a class="result-link" href="${aiResources.articleJson}" target="_blank" rel="noreferrer">文章 JSON</a>` : '<span class="result-link">无 DOI，暂无单篇 JSON</span>'}
        <a class="result-link" href="${aiResources.journalTitles}" target="_blank" rel="noreferrer">本刊标题索引</a>
        ${aiResources.journalAbstracts ? `<a class="result-link" href="${aiResources.journalAbstracts}" target="_blank" rel="noreferrer">同年份段摘要</a>` : ""}
        <a class="result-link" href="${aiResources.overview}" target="_blank" rel="noreferrer">数据库总览</a>
    `;
    dom.aiPrompt.textContent = aiPrompt;
    dom.modal.dataset.shareUrl = shareUrl;
    dom.modal.dataset.aiPrompt = aiPrompt;
    dom.modal.querySelectorAll("[data-copy-link]").forEach((button) => {
        button.textContent = copyLinkLabel;
    });
    renderArticleSchema(article, shareUrl, apiUrl);
    setModalOpen(true);
}

function renderFavoritesLauncher() {
    if (!dom.favoritesToggle) {
        return;
    }
    dom.favoritesToggle.textContent = `我的收藏（${formatNumber(app.favorites.size)}）`;
    dom.favoritesToggle.classList.toggle("has-items", app.favorites.size > 0);
    dom.favoritesToggle.setAttribute("aria-expanded", app.state.favoritesOpen ? "true" : "false");
}

function renderDashboardVisibility() {
    if (!dom.dashboardPanel || !dom.dashboardToggle) {
        return;
    }
    dom.dashboardPanel.hidden = !app.state.dashboardOpen;
    dom.dashboardToggle.textContent = app.state.dashboardOpen ? "收起概况" : "数据库概况";
    dom.dashboardToggle.setAttribute("aria-expanded", app.state.dashboardOpen ? "true" : "false");
    dom.dashboardToggle.classList.toggle("is-active", app.state.dashboardOpen);
}

function renderFavoritesModal() {
    renderFavoritesLauncher();
    if (!app.state.favoritesOpen) {
        setFavoritesModalOpen(false);
        return;
    }

    const favorites = getFavoriteArticles();
    dom.favoritesSummary.textContent = favorites.length
        ? `已收藏 ${formatNumber(favorites.length)} 篇文章。你可以继续筛选、打开详情，或直接导出 BibTeX / CSV。`
        : "收藏夹还是空的。你可以先在搜索结果、浏览页或详情弹窗里把候选文章加入收藏。";
    dom.copyFavoritesBibtex.disabled = favorites.length === 0;
    dom.exportFavoritesBibtex.disabled = favorites.length === 0;
    dom.exportFavoritesCsv.disabled = favorites.length === 0;
    dom.clearFavorites.disabled = favorites.length === 0;

    if (!favorites.length) {
        clearActiveNavigationSelection();
        dom.favoritesList.innerHTML = '<div class="empty-state">还没有收藏文章。</div>';
        setFavoritesModalOpen(true);
        return;
    }

    dom.favoritesList.innerHTML = favorites.map((article) => {
        const articleKey = rememberArticle(article);
        const doiUrl = buildDoiUrl(article.doi);
        return `
            <article class="favorite-card">
                <div class="favorite-card-head">
                    <div>
                        <h3 class="favorite-card-title">
                            <button type="button" class="article-trigger" data-open-article="${escapeHtml(articleKey)}" data-nav-article="${escapeHtml(articleKey)}">${escapeHtml(article.title || "无标题")}</button>
                        </h3>
                        <div class="favorite-card-meta">
                            ${escapeHtml(article.journal || "未知期刊")} · ${escapeHtml(article.year || "年份未知")} · ${article.doi ? `DOI: ${escapeHtml(article.doi)}` : "无 DOI"}
                        </div>
                    </div>
                    ${renderFavoriteButton(articleKey, "移出收藏")}
                </div>
                <div class="favorite-card-authors">${escapeHtml(article.authors || "未知作者")}</div>
                <div class="favorite-card-links">
                    <button type="button" class="result-link button-link" data-open-article="${escapeHtml(articleKey)}">查看详情</button>
                    ${doiUrl ? `<a class="result-link" href="${doiUrl}" target="_blank" rel="noreferrer">打开 DOI</a>` : ""}
                    <a class="result-link" href="${buildScholarUrl(article.title)}" target="_blank" rel="noreferrer">Google Scholar</a>
                </div>
            </article>
        `;
    }).join("");
    syncActiveNavigationButtons();
    setFavoritesModalOpen(true);
}

function renderDatasetMeta() {
    if (!app.meta) {
        dom.datasetMeta.textContent = "正在准备数据概况…";
        return;
    }
    dom.datasetMeta.textContent =
        `当前数据：${formatNumber(app.meta.total)} 篇文献 · ` +
        `${formatNumber(app.meta.journals)} 本期刊 · ` +
        `年份范围 ${app.meta.minYear}-${app.meta.maxYear} · ` +
        `已有摘要 ${formatNumber(app.meta.withAbstract)} 篇 · ` +
        `缺摘要 ${formatNumber(app.meta.missingAbstract)} 篇`;
}

function buildTrendChart(yearCounts) {
    if (!Array.isArray(yearCounts) || !yearCounts.length) {
        return '<div class="empty-state">暂无年度趋势数据。</div>';
    }
    const width = 760;
    const height = 240;
    const padding = { top: 18, right: 20, bottom: 34, left: 16 };
    const baselineY = height - padding.bottom;
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = baselineY - padding.top;
    const maxCount = Math.max(...yearCounts.map((item) => Number(item.count || 0)), 1);
    const points = yearCounts.map((item, index) => {
        const x = yearCounts.length === 1
            ? padding.left + plotWidth / 2
            : padding.left + (plotWidth * index) / (yearCounts.length - 1);
        const y = baselineY - (plotHeight * Number(item.count || 0)) / maxCount;
        return {
            x,
            y,
            year: item.year,
            count: Number(item.count || 0),
        };
    });
    const linePoints = points.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(" ");
    const areaPoints = [
        `${points[0].x.toFixed(1)},${baselineY.toFixed(1)}`,
        linePoints,
        `${points[points.length - 1].x.toFixed(1)},${baselineY.toFixed(1)}`,
    ].join(" ");
    const labelIndexes = [...new Set([0, Math.floor((points.length - 1) / 2), points.length - 1])];
    const gridValues = [0.25, 0.5, 0.75].map((ratio) => ({
        y: baselineY - plotHeight * ratio,
        label: Math.round(maxCount * ratio),
    }));
    const lastPoint = points[points.length - 1];
    return `
        <svg class="trend-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="年度发文趋势图">
            ${gridValues.map((grid) => `
                <g>
                    <line class="trend-grid" x1="${padding.left}" y1="${grid.y.toFixed(1)}" x2="${width - padding.right}" y2="${grid.y.toFixed(1)}"></line>
                    <text class="trend-axis" x="${width - padding.right}" y="${(grid.y - 6).toFixed(1)}" text-anchor="end">${formatNumber(grid.label)}</text>
                </g>
            `).join("")}
            <polygon class="trend-area" points="${areaPoints}"></polygon>
            <polyline class="trend-line" points="${linePoints}"></polyline>
            <circle class="trend-point" cx="${lastPoint.x.toFixed(1)}" cy="${lastPoint.y.toFixed(1)}" r="5"></circle>
            ${labelIndexes.map((index) => {
                const point = points[index];
                return `
                    <text class="trend-label" x="${point.x.toFixed(1)}" y="${height - 10}" text-anchor="middle">${escapeHtml(point.year)}</text>
                `;
            }).join("")}
        </svg>
    `;
}

function renderDashboardList(items, nameKey, unit = "篇") {
    if (!Array.isArray(items) || !items.length) {
        return '<div class="empty-state">暂无数据。</div>';
    }
    return items.map((item) => `
        <div class="dashboard-list-item">
            <strong>${escapeHtml(item[nameKey])}</strong>
            <span>${formatNumber(item.count)} ${unit}</span>
        </div>
    `).join("");
}

function renderDashboard() {
    if (!dom.dashboardSummary || !dom.dashboardTrend) {
        return;
    }
    if (!app.dashboard?.summary) {
        dom.dashboardGeneratedAt.textContent = "概况数据尚未就绪";
        dom.dashboardSummary.innerHTML = '<div class="empty-state">首页概况会在静态索引或检索库准备好后显示。</div>';
        dom.dashboardTrendMeta.textContent = "";
        dom.dashboardTrend.innerHTML = '<div class="empty-state">暂无年度趋势数据。</div>';
        dom.dashboardKeywords.innerHTML = '<div class="empty-state">暂无关键词。</div>';
        dom.dashboardAuthors.innerHTML = '<div class="empty-state">暂无作者榜。</div>';
        dom.dashboardJournals.innerHTML = '<div class="empty-state">暂无期刊分布。</div>';
        return;
    }

    const summary = app.dashboard.summary;
    const yearCounts = app.dashboard.year_counts || [];
    const latestYear = yearCounts[yearCounts.length - 1];
    dom.dashboardGeneratedAt.textContent = `更新于 ${formatTimestamp(app.dashboard.generated_at)}`;
    dom.dashboardSummary.innerHTML = `
        <article class="stat-card">
            <div class="stat-kicker">总篇数</div>
            <div class="stat-value">${formatNumber(summary.total_articles)}</div>
            <div class="stat-meta">${formatNumber(summary.total_journals)} 本期刊 · ${summary.year_min}-${summary.year_max}</div>
        </article>
        <article class="stat-card">
            <div class="stat-kicker">摘要覆盖率</div>
            <div class="stat-value">${formatPercent(summary.abstract_coverage_rate)}</div>
            <div class="stat-meta">已补摘要 ${formatNumber(summary.articles_with_abstract)} 篇</div>
        </article>
        <article class="stat-card">
            <div class="stat-kicker">DOI 覆盖率</div>
            <div class="stat-value">${formatPercent(summary.doi_coverage_rate)}</div>
            <div class="stat-meta">可直接分享 ${formatNumber(summary.records_with_doi)} 篇</div>
        </article>
        <article class="stat-card">
            <div class="stat-kicker">最新年份</div>
            <div class="stat-value">${summary.year_max || "—"}</div>
            <div class="stat-meta">${latestYear ? `该年份当前收录 ${formatNumber(latestYear.count)} 篇` : "年度计数待补充"}</div>
        </article>
    `;
    dom.dashboardTrendMeta.textContent = latestYear
        ? `${summary.year_min}-${summary.year_max} · ${latestYear.year} 年收录 ${formatNumber(latestYear.count)} 篇`
        : `${summary.year_min}-${summary.year_max}`;
    dom.dashboardTrend.innerHTML = buildTrendChart(yearCounts);
    dom.dashboardKeywords.innerHTML = (app.dashboard.top_keywords || []).length
        ? app.dashboard.top_keywords.slice(0, 12).map((item, index, list) => {
            const maxCount = list[0]?.count || 1;
            const weight = 0.92 + (Number(item.count || 0) / maxCount) * 0.34;
            return `
                <span class="dashboard-tag" style="font-size: ${weight.toFixed(2)}rem;">
                    <strong>${escapeHtml(item.term)}</strong>
                    <span>${formatNumber(item.count)}</span>
                </span>
            `;
        }).join("")
        : '<div class="empty-state">暂无关键词。</div>';
    dom.dashboardAuthors.innerHTML = renderDashboardList(app.dashboard.top_authors, "author", "次");
    dom.dashboardJournals.innerHTML = renderDashboardList(app.dashboard.top_journals, "journal", "篇");
}

function renderEngineStatus() {
    dom.engineBadge.className = "engine-badge";
    if (app.engine === "sqlite") {
        dom.engineBadge.classList.add("is-ready");
        dom.engineBadge.textContent = "SQLite FTS5 已连接";
    } else if (app.engine === "fallback") {
        dom.engineBadge.classList.add("is-fallback");
        dom.engineBadge.textContent = "JSON 备用模式";
    } else {
        dom.engineBadge.textContent = "正在初始化";
    }
    dom.engineMessage.textContent = app.engineMessage;
}

function groupFacets() {
    if (!app.facets) {
        return [];
    }
    const seen = new Set();
    const groups = [];

    for (const group of JOURNAL_GROUPS) {
        const items = app.facets.filter((facet) => group.journals.includes(facet.journal));
        if (!items.length) {
            continue;
        }
        items.forEach((item) => seen.add(item.journal));
        groups.push({ label: group.label, items });
    }

    const others = app.facets.filter((facet) => !seen.has(facet.journal));
    if (others.length) {
        groups.push({ label: "其他", items: others });
    }
    return groups;
}

function getSelectedFacetItems() {
    const selected = new Set(app.state.journals);
    return (app.facets || [])
        .filter((item) => selected.has(item.journal))
        .sort((a, b) => a.journal.localeCompare(b.journal));
}

function renderSelectedJournalPills(items, emptyText = "") {
    if (!items.length) {
        return emptyText ? `<div class="helper-text">${escapeHtml(emptyText)}</div>` : "";
    }
    return `
        <div class="selected-journal-list">
            ${items.map((item) => `
                <button type="button" class="selected-journal-chip" data-remove-journal="${escapeHtml(item.journal)}">
                    <strong>${escapeHtml(item.journal)}</strong>
                    <span>${formatNumber(item.total)} 篇</span>
                </button>
            `).join("")}
        </div>
    `;
}

function renderJournalFilters() {
    if (!app.facets) {
        dom.filterContainer.innerHTML = '<div class="empty-state">筛选项会在数据源准备好后显示。</div>';
        if (dom.journalFilterSummary) {
            dom.journalFilterSummary.textContent = "正在准备期刊列表…";
        }
        return;
    }

    const selected = new Set(app.state.journals);
    const query = normalizeText(app.state.journalFacetQuery);
    const groups = groupFacets()
        .map((group) => ({
            ...group,
            items: group.items.filter((item) => !query || normalizeText(item.journal).includes(query)),
        }))
        .filter((group) => group.items.length);
    const visibleCount = groups.reduce((sum, group) => sum + group.items.length, 0);
    if (dom.journalFilterSummary) {
        const selectedCount = app.state.journals.length;
        dom.journalFilterSummary.textContent = query
            ? `当前显示 ${formatNumber(visibleCount)} 本期刊${selectedCount ? ` · 已选 ${formatNumber(selectedCount)} 本` : ""}`
            : `共 ${formatNumber(app.facets.length)} 本期刊${selectedCount ? ` · 已选 ${formatNumber(selectedCount)} 本` : ""}`;
    }
    if (!groups.length) {
        dom.filterContainer.innerHTML = '<div class="sidebar-empty">没有匹配的期刊名。可以缩短关键词，或直接清空上面的过滤输入。</div>';
        return;
    }
    const selectedItems = getSelectedFacetItems();
    const selectedBlock = selectedItems.length ? `
        <section class="facet-group facet-group-selected">
            <div class="browse-header">
                <div>
                    <h3 class="facet-title">已选期刊</h3>
                    <div class="helper-text">点一下即可移除，不必再回到对应学科里找。</div>
                </div>
                <button type="button" class="tiny-btn" data-clear-filter="journals">清空已选</button>
            </div>
            ${renderSelectedJournalPills(selectedItems)}
        </section>
    ` : "";
    dom.filterContainer.innerHTML = selectedBlock + groups.map((group) => `
        <section class="facet-group">
            <div class="facet-title-row">
                <h3 class="facet-title">${escapeHtml(group.label)}</h3>
                <span class="facet-count">${formatNumber(group.items.length)} 本</span>
            </div>
            <div class="facet-list">
                ${group.items.map((item) => `
                    <label class="facet-item">
                        <span class="facet-name">
                            <input type="checkbox" data-journal-filter="${escapeHtml(item.journal)}" ${selected.has(item.journal) ? "checked" : ""}>
                            ${escapeHtml(item.journal)}
                        </span>
                        <span class="facet-count">${formatNumber(item.total)}</span>
                    </label>
                `).join("")}
            </div>
        </section>
    `).join("");
}

function renderTabs() {
    dom.searchView.classList.toggle("active", app.state.mode === "search");
    dom.browseView.classList.toggle("active", app.state.mode === "browse");
    [...dom.tabbar.querySelectorAll(".tab-btn")].forEach((button) => {
        button.classList.toggle("active", button.dataset.mode === app.state.mode);
    });
}

function buildWhereClause(params, query, includeMatch = true) {
    const clauses = [];
    if (includeMatch && query.trim()) {
        clauses.push("articles MATCH $query");
        params.$query = query.trim();
    }
    if (app.state.journals.length) {
        const placeholders = app.state.journals.map((_, index) => `$journal_${index}`);
        clauses.push(`m.journal IN (${placeholders.join(", ")})`);
        app.state.journals.forEach((journal, index) => {
            params[`$journal_${index}`] = journal;
        });
    }
    if (app.state.yearFrom) {
        clauses.push("m.year >= $year_from");
        params.$year_from = Number(app.state.yearFrom);
    }
    if (app.state.yearTo) {
        clauses.push("m.year <= $year_to");
        params.$year_to = Number(app.state.yearTo);
    }
    if (app.state.hasAbstractOnly) {
        clauses.push("TRIM(COALESCE(articles.abstract, '')) <> ''");
    }
    return clauses.length ? `WHERE ${clauses.join(" AND ")}` : "";
}

function searchWithDb() {
    const query = app.state.q.trim();
    const params = {
        $limit: PAGE_SIZE,
        $offset: (app.state.page - 1) * PAGE_SIZE,
    };
    const whereClause = buildWhereClause(params, query, true);
    const countParams = {};
    const countWhereClause = buildWhereClause(countParams, query, true);

    let orderBy = "ORDER BY m.year DESC, articles.title COLLATE NOCASE ASC";
    if (app.state.sort === "journal") {
        orderBy = "ORDER BY m.journal COLLATE NOCASE ASC, m.year DESC, articles.title COLLATE NOCASE ASC";
    } else if (app.state.sort === "relevance" && query) {
        orderBy = "ORDER BY bm25(articles, 8.0, 4.0, 2.0) ASC, m.year DESC";
    }

    const previewExpr = query
        ? `
            COALESCE(
                NULLIF(snippet(articles, 1, '<mark>', '</mark>', '...', 22), ''),
                NULLIF(snippet(articles, 0, '<mark>', '</mark>', '...', 12), ''),
                NULLIF(snippet(articles, 2, '<mark>', '</mark>', '...', 12), ''),
                ''
            ) AS preview
        `
        : `
            CASE
                WHEN TRIM(COALESCE(articles.abstract, '')) <> '' THEN
                    substr(articles.abstract, 1, 280) ||
                    CASE WHEN length(articles.abstract) > 280 THEN '…' ELSE '' END
                ELSE ''
            END AS preview
        `;

    const total = Number(queryDb(`
        SELECT COUNT(*) AS total
        FROM articles
        JOIN articles_meta m ON m.rowid = articles.rowid
        ${countWhereClause}
    `, countParams)[0]?.total || 0);

    const rows = queryDb(`
        SELECT
            articles.rowid AS rowid,
            articles.title AS title,
            articles.authors AS authors,
            articles.journal AS journal,
            m.year AS year,
            articles.doi AS doi,
            ${previewExpr},
            articles.abstract AS abstract
        FROM articles
        JOIN articles_meta m ON m.rowid = articles.rowid
        ${whereClause}
        ${orderBy}
        LIMIT $limit OFFSET $offset
    `, params);

    return {
        total,
        rows,
        usedFallback: false,
    };
}

function scoreFallbackRow(row, tokens) {
    const haystack = normalizeText(
        `${row["Article Title"] || ""} ${row["Abstract"] || ""} ${row["Author Full Names"] || ""}`
    );
    return tokens.reduce((score, token) => score + (haystack.includes(token) ? 1 : 0), 0);
}

function filterFallbackRows() {
    const query = normalizeText(app.state.q);
    const tokens = query.split(/\s+/).filter(Boolean);

    let rows = app.fallbackData.filter((item) => {
        const journal = String(item["Source Title"] || "").trim();
        const year = Number.parseInt(item["Publication Year"], 10);

        if (app.state.journals.length && !app.state.journals.includes(journal)) {
            return false;
        }
        if (app.state.yearFrom && !Number.isNaN(year) && year < Number(app.state.yearFrom)) {
            return false;
        }
        if (app.state.yearTo && !Number.isNaN(year) && year > Number(app.state.yearTo)) {
            return false;
        }
        if (app.state.hasAbstractOnly && !String(item["Abstract"] || "").trim()) {
            return false;
        }
        if (!tokens.length) {
            return true;
        }
        const haystack = normalizeText(
            `${item["Article Title"] || ""} ${item["Abstract"] || ""} ${item["Author Full Names"] || ""}`
        );
        return tokens.every((token) => haystack.includes(token));
    });

    if (app.state.sort === "journal") {
        rows.sort((a, b) => {
            const journalCompare = String(a["Source Title"] || "").localeCompare(String(b["Source Title"] || ""));
            if (journalCompare !== 0) {
                return journalCompare;
            }
            return Number(b["Publication Year"] || 0) - Number(a["Publication Year"] || 0);
        });
    } else if (app.state.sort === "relevance" && tokens.length) {
        rows.sort((a, b) => scoreFallbackRow(b, tokens) - scoreFallbackRow(a, tokens));
    } else {
        rows.sort((a, b) => Number(b["Publication Year"] || 0) - Number(a["Publication Year"] || 0));
    }

    const total = rows.length;
    const offset = (app.state.page - 1) * PAGE_SIZE;
    const pageRows = rows.slice(offset, offset + PAGE_SIZE).map((item) => ({
        title: item["Article Title"] || "无标题",
        authors: item["Author Full Names"] || "未知作者",
        journal: item["Source Title"] || "",
        year: Number.parseInt(item["Publication Year"], 10) || "",
        doi: item["DOI"] || "",
        preview: truncateText(item["Abstract"] || "", 280),
        abstract: item["Abstract"] || "",
    }));

    return {
        total,
        rows: pageRows,
        usedFallback: true,
    };
}

function renderResults(result) {
    const totalPages = Math.max(1, Math.ceil(result.total / PAGE_SIZE));
    const queryActive = Boolean(app.state.q.trim());
    let summary = `共 ${formatNumber(result.total)} 条结果`;
    if (!queryActive) {
        summary = `显示 ${formatNumber(result.total)} 条符合筛选条件的文章，默认按年份从新到旧。`;
    }
    if (result.usedFallback) {
        summary += " 当前为备用 JSON 搜索，语法仅支持基础关键词包含。";
    }
    if (app.state.hasAbstractOnly) {
        summary += " 已过滤掉无摘要记录。";
    }
    dom.resultSummary.textContent = summary;

    if (!result.rows.length) {
        clearActiveNavigationSelection();
        dom.resultList.innerHTML = `
            <div class="empty-state">
                ${queryActive
                    ? "没有找到匹配结果。可以尝试放宽年份范围、减少期刊筛选，或改用更短的关键词。"
                    : "还没有输入搜索词。你也可以直接按筛选条件浏览最近文章。"}
            </div>
        `;
        dom.pagination.innerHTML = "";
        return;
    }

    dom.resultList.innerHTML = result.rows.map((row) => {
        const articleKey = rememberArticle(row);
        const doiUrl = buildDoiUrl(row.doi);
        const preview = row.preview
            ? `<p class="result-snippet">${queryActive ? renderHighlightedSnippet(row.preview) : escapeHtml(row.preview)}</p>`
            : '<p class="result-snippet muted">暂无摘要。</p>';
        const abstractBlock = row.abstract && row.abstract !== row.preview
            ? `
                <details class="abstract-toggle">
                    <summary>展开完整摘要</summary>
                    <div class="full-abstract">${escapeHtml(row.abstract)}</div>
                </details>
            `
            : "";

        return `
            <article class="result-card">
                <div class="result-topline">
                    <span class="journal-tag">${escapeHtml(row.journal)}</span>
                    <span>${escapeHtml(row.year || "年份未知")}</span>
                    <span>${row.doi ? `DOI: ${escapeHtml(row.doi)}` : "无 DOI"}</span>
                </div>
                <h3 class="result-title">
                    <button type="button" class="article-trigger" data-open-article="${escapeHtml(articleKey)}" data-nav-article="${escapeHtml(articleKey)}">${escapeHtml(row.title)}</button>
                </h3>
                <p class="result-authors">${escapeHtml(row.authors || "未知作者")}</p>
                ${preview}
                ${abstractBlock}
                <div class="result-actions">
                    <button type="button" class="result-link button-link" data-open-article="${escapeHtml(articleKey)}">查看详情</button>
                    ${renderFavoriteButton(articleKey)}
                    ${doiUrl ? `<a class="result-link" href="${doiUrl}" target="_blank" rel="noreferrer">打开 DOI</a>` : ""}
                    <a class="result-link" href="${buildScholarUrl(row.title)}" target="_blank" rel="noreferrer">Google Scholar</a>
                </div>
            </article>
        `;
    }).join("");
    syncActiveNavigationButtons();

    dom.pagination.innerHTML = `
        <div class="pagination-meta">第 ${app.state.page} / ${totalPages} 页 · 每页 ${PAGE_SIZE} 条</div>
        <div class="pagination-controls">
            <button class="ghost-btn" data-page-action="prev" ${app.state.page <= 1 ? "disabled" : ""}>上一页</button>
            <button class="ghost-btn" data-page-action="next" ${app.state.page >= totalPages ? "disabled" : ""}>下一页</button>
        </div>
    `;
}

function renderActiveFilters() {
    if (!dom.activeFilters) {
        return;
    }
    const chips = [];
    if (app.state.q.trim()) {
        chips.push(`
            <span class="filter-chip">
                <strong>关键词</strong>
                <span>${escapeHtml(app.state.q.trim())}</span>
                <button type="button" data-clear-filter="query">清除</button>
            </span>
        `);
    }
    if (app.state.yearFrom || app.state.yearTo) {
        chips.push(`
            <span class="filter-chip">
                <strong>年份</strong>
                <span>${escapeHtml(app.state.yearFrom || "不限")} - ${escapeHtml(app.state.yearTo || "不限")}</span>
                <button type="button" data-clear-filter="year">清除</button>
            </span>
        `);
    }
    if (app.state.journals.length) {
        chips.push(`
            <span class="filter-chip">
                <strong>期刊</strong>
                <span>${formatNumber(app.state.journals.length)} 本</span>
                <button type="button" data-clear-filter="journals">清除</button>
            </span>
        `);
    }
    if (app.state.hasAbstractOnly) {
        chips.push(`
            <span class="filter-chip">
                <strong>摘要</strong>
                <span>只看有摘要</span>
                <button type="button" data-clear-filter="abstract">清除</button>
            </span>
        `);
    }
    if (chips.length > 1) {
        chips.push(`
            <span class="filter-chip">
                <strong>全部筛选</strong>
                <button type="button" data-clear-filter="all">一键清空</button>
            </span>
        `);
    }
    dom.activeFilters.innerHTML = chips.join("");
}

async function renderSearchView() {
    dom.searchInput.value = app.state.q;
    dom.yearFrom.value = app.state.yearFrom;
    dom.yearTo.value = app.state.yearTo;
    dom.hasAbstractOnly.checked = app.state.hasAbstractOnly;
    dom.journalFilterQuery.value = app.state.journalFacetQuery;
    dom.sortSelect.value = app.state.sort;
    renderJournalFilters();
    renderActiveFilters();

    if (app.engine === "fallback" && (app.state.q.trim() || app.state.journals.length || app.state.yearFrom || app.state.yearTo)) {
        await ensureFallbackData();
        renderEngineStatus();
        renderDatasetMeta();
        renderJournalFilters();
    }

    if (app.engine === "fallback" && !app.fallbackData && !app.state.q.trim() && !app.state.journals.length && !app.state.yearFrom && !app.state.yearTo) {
        clearActiveNavigationSelection();
        dom.searchNotice.innerHTML = `
            <div class="notice-box warning">
                ${escapeHtml(app.engineMessage)}
                你现在可以直接进入“浏览”标签，或开始搜索时由页面按需加载备用 JSON 数据。
            </div>
        `;
        dom.resultList.innerHTML = `
            <div class="empty-state">
                输入主题、作者或关键词开始搜索，例如 <code>"social mobility"</code>、<code>fertility NOT mortality</code>、<code>Wenbo Hu</code>。
            </div>
        `;
        dom.pagination.innerHTML = "";
        dom.resultSummary.textContent = "等待检索输入。";
        return;
    }

    dom.searchNotice.innerHTML = app.engine === "sqlite"
        ? `
            <div class="notice-box">
                搜索覆盖标题、摘要和作者。支持 SQLite FTS5 语法，例如 <code>"social mobility"</code>、<code>marriage OR cohabitation</code>、<code>educat*</code>。
            </div>
        `
        : `
            <div class="notice-box warning">
                当前为备用 JSON 模式。${escapeHtml(app.engineMessage)} 基础搜索可用，但不支持完整 FTS5 语法和高亮排序。
            </div>
        `;

    try {
        const result = app.engine === "sqlite" ? searchWithDb() : filterFallbackRows();
        renderResults(result);
    } catch (error) {
        console.error(error);
        clearActiveNavigationSelection();
        dom.resultSummary.textContent = "查询失败";
        dom.resultList.innerHTML = `
            <div class="empty-state">
                查询语法可能有误。若你在用 FTS5 高级语法，先试试删掉多余括号或引号。
            </div>
        `;
        dom.pagination.innerHTML = "";
    }
}

function getBrowseJournals() {
    return app.facets ?? [];
}

function getBrowseYearsFromDb(journal) {
    return queryDb(`
        SELECT year, COUNT(*) AS total
        FROM articles_meta
        WHERE journal = $journal
        GROUP BY year
        ORDER BY year DESC
    `, { $journal: journal }).map((row) => ({
        year: Number(row.year || 0),
        total: Number(row.total || 0),
    }));
}

function getBrowseArticlesFromDb(journal, year) {
    return queryDb(`
        SELECT
            articles.title AS title,
            articles.authors AS authors,
            articles.doi AS doi,
            articles.abstract AS abstract,
            m.year AS year,
            articles.journal AS journal
        FROM articles
        JOIN articles_meta m ON m.rowid = articles.rowid
        WHERE m.journal = $journal
          AND m.year = $year
        ORDER BY articles.title COLLATE NOCASE ASC
    `, {
        $journal: journal,
        $year: Number(year),
    });
}

function getBrowseYearsFromFallback(journal) {
    const counter = new Map();
    for (const item of app.fallbackData) {
        if ((item["Source Title"] || "") !== journal) {
            continue;
        }
        const year = Number.parseInt(item["Publication Year"], 10);
        if (Number.isNaN(year)) {
            continue;
        }
        counter.set(year, (counter.get(year) || 0) + 1);
    }
    return [...counter.entries()]
        .map(([year, total]) => ({ year, total }))
        .sort((a, b) => b.year - a.year);
}

function getBrowseArticlesFromFallback(journal, year) {
    return app.fallbackData
        .filter((item) =>
            item["Source Title"] === journal &&
            Number.parseInt(item["Publication Year"], 10) === Number(year)
        )
        .map((item) => ({
            title: item["Article Title"] || "无标题",
            authors: item["Author Full Names"] || "未知作者",
            doi: item["DOI"] || "",
            abstract: item["Abstract"] || "",
            year: Number(year),
            journal,
        }))
        .sort((a, b) => a.title.localeCompare(b.title));
}

function renderBrowseJournals(journals) {
    const query = normalizeText(app.state.browseJournalQuery);
    const filtered = journals.filter((item) => !query || normalizeText(item.journal).includes(query));
    if (dom.browseJournalSummary) {
        const selectedLabel = app.state.browseJournal ? ` · 当前：${app.state.browseJournal}` : "";
        dom.browseJournalSummary.textContent = query
            ? `当前显示 ${formatNumber(filtered.length)} / ${formatNumber(journals.length)} 本期刊${selectedLabel}`
            : `共 ${formatNumber(journals.length)} 本期刊，可按刊名快速过滤${selectedLabel}`;
    }
    if (!filtered.length) {
        dom.journalRail.innerHTML = '<div class="sidebar-empty">没有匹配的期刊名。试试删掉一部分关键词。</div>';
        return;
    }
    const activeJournal = filtered.find((item) => item.journal === app.state.browseJournal) || null;
    const remaining = activeJournal
        ? filtered.filter((item) => item.journal !== activeJournal.journal)
        : filtered;
    const renderedGroups = groupFacets()
        .map((group) => ({
            label: group.label,
            items: remaining.filter((item) => group.items.some((facet) => facet.journal === item.journal)),
        }))
        .filter((group) => group.items.length);
    const seen = new Set(renderedGroups.flatMap((group) => group.items.map((item) => item.journal)));
    const others = remaining.filter((item) => !seen.has(item.journal));
    if (others.length) {
        renderedGroups.push({ label: "其他", items: others });
    }
    const renderJournalButton = (item) => `
        <button class="journal-rail-btn ${app.state.browseJournal === item.journal ? "active" : ""}" data-browse-journal="${escapeHtml(item.journal)}">
            <strong>${escapeHtml(item.journal)}</strong>
            <span class="journal-rail-meta">
                ${formatNumber(item.total)} 篇 · ${escapeHtml(item.minYear || "?")}-${escapeHtml(item.maxYear || "?")}
            </span>
        </button>
    `;
    const activeBlock = activeJournal ? `
        <section class="journal-rail-group">
            <div class="journal-rail-group-title">当前期刊</div>
            ${renderJournalButton(activeJournal)}
        </section>
    ` : "";
    dom.journalRail.innerHTML = activeBlock + renderedGroups.map((group) => `
        <section class="journal-rail-group">
            <div class="journal-rail-group-title">
                <span>${escapeHtml(group.label)}</span>
                <span class="facet-count">${formatNumber(group.items.length)} 本</span>
            </div>
            <div class="journal-rail-group-list">
                ${group.items.map(renderJournalButton).join("")}
            </div>
        </section>
    `).join("");
}

function renderBrowseYears(years) {
    if (!app.state.browseJournal) {
        dom.yearGrid.innerHTML = '<div class="empty-state">左侧先选一本期刊，再看年份分布。</div>';
        return;
    }
    if (!years.length) {
        dom.yearGrid.innerHTML = '<div class="empty-state">这本期刊暂时没有可用年份。</div>';
        return;
    }
    dom.yearGrid.innerHTML = years.map((item) => `
        <button class="year-card ${String(app.state.browseYear) === String(item.year) ? "active" : ""}" data-browse-year="${item.year}">
            <strong>${item.year} 年</strong>
            <span class="muted">${formatNumber(item.total)} 篇文章</span>
        </button>
    `).join("");
}

function renderBrowseArticles(articles) {
    if (!app.state.browseYear) {
        clearActiveNavigationSelection();
        dom.articleList.innerHTML = '<div class="empty-state">选定年份后，这里会列出文章标题、作者、摘要和 DOI。</div>';
        return;
    }
    if (!articles.length) {
        clearActiveNavigationSelection();
        dom.articleList.innerHTML = '<div class="empty-state">这一年暂时没有文章。</div>';
        return;
    }
    dom.articleList.innerHTML = articles.map((row) => {
        const articleKey = rememberArticle(row);
        const doiUrl = buildDoiUrl(row.doi);
        const preview = truncateText(row.abstract || "", 320);
        return `
            <article class="result-card">
                <div class="result-topline">
                    <span class="journal-tag">${escapeHtml(row.journal)}</span>
                    <span>${escapeHtml(row.year)}</span>
                    <span>${row.doi ? `DOI: ${escapeHtml(row.doi)}` : "无 DOI"}</span>
                </div>
                <h3 class="result-title">
                    <button type="button" class="article-trigger" data-open-article="${escapeHtml(articleKey)}" data-nav-article="${escapeHtml(articleKey)}">${escapeHtml(row.title)}</button>
                </h3>
                <p class="result-authors">${escapeHtml(row.authors || "未知作者")}</p>
                <p class="result-snippet">${escapeHtml(preview || "暂无摘要。")}</p>
                <div class="result-actions">
                    <button type="button" class="result-link button-link" data-open-article="${escapeHtml(articleKey)}">查看详情</button>
                    ${renderFavoriteButton(articleKey)}
                    ${doiUrl ? `<a class="result-link" href="${doiUrl}" target="_blank" rel="noreferrer">打开 DOI</a>` : ""}
                    <a class="result-link" href="${buildScholarUrl(row.title)}" target="_blank" rel="noreferrer">Google Scholar</a>
                </div>
            </article>
        `;
    }).join("");
    syncActiveNavigationButtons();
}

function renderBrowseBreadcrumbs() {
    const parts = [
        `<button class="crumb ${!app.state.browseJournal ? "current" : ""}" data-browse-reset="all">全部期刊</button>`,
    ];
    if (app.state.browseJournal) {
        parts.push("<span>/</span>");
        parts.push(`<button class="crumb ${!app.state.browseYear ? "current" : ""}" data-browse-reset="journal">${escapeHtml(app.state.browseJournal)}</button>`);
    }
    if (app.state.browseYear) {
        parts.push("<span>/</span>");
        parts.push(`<button class="crumb current">${escapeHtml(app.state.browseYear)} 年</button>`);
    }
    dom.browseBreadcrumbs.innerHTML = parts.join("");
}

async function renderBrowseView() {
    if (app.engine === "fallback" && !app.fallbackData) {
        await ensureFallbackData();
        renderEngineStatus();
        renderDatasetMeta();
        renderJournalFilters();
    }
    dom.browseJournalQuery.value = app.state.browseJournalQuery;
    const journals = getBrowseJournals();
    const years = app.state.browseJournal
        ? (app.engine === "sqlite"
            ? getBrowseYearsFromDb(app.state.browseJournal)
            : getBrowseYearsFromFallback(app.state.browseJournal))
        : [];
    const articles = app.state.browseJournal && app.state.browseYear
        ? (app.engine === "sqlite"
            ? getBrowseArticlesFromDb(app.state.browseJournal, app.state.browseYear)
            : getBrowseArticlesFromFallback(app.state.browseJournal, app.state.browseYear))
        : [];

    dom.browseStatus.innerHTML = app.engine === "sqlite"
        ? '<div class="notice-box">浏览模式同样直接读取 SQLite 库，不再依赖同步加载的 <code>data.js</code>。</div>'
        : `<div class="notice-box warning">当前浏览模式使用备用 JSON 数据。${escapeHtml(app.engineMessage)}</div>`;
    renderBrowseBreadcrumbs();
    renderBrowseJournals(journals);
    renderBrowseYears(years);
    renderBrowseArticles(articles);
}

async function renderAll() {
    renderTabs();
    renderEngineStatus();
    renderDatasetMeta();
    renderDisciplinePresets();
    renderQuickSearches();
    renderDashboardVisibility();
    renderDashboard();
    if (app.state.mode === "search") {
        await renderSearchView();
    } else {
        await renderBrowseView();
    }
    await renderArticleModal();
    renderFavoritesModal();
    renderEngineStatus();
    renderDatasetMeta();
    renderDisciplinePresets();
    renderQuickSearches();
    renderDashboardVisibility();
    renderDashboard();
    syncUrl();
}

function resetSearchFilters() {
    app.state.journals = [];
    app.state.journalFacetQuery = "";
    app.state.yearFrom = "";
    app.state.yearTo = "";
    app.state.hasAbstractOnly = false;
    app.state.sort = "relevance";
    app.state.page = 1;
    clearActiveNavigationSelection();
}

async function toggleFavoriteByKey(articleKey) {
    if (!articleKey) {
        return;
    }
    toggleFavorite(articleKey);
    await renderAll();
}

function bindEvents() {
    dom.themeToggle.addEventListener("click", () => {
        const nextTheme = app.theme === "dark" ? "light" : "dark";
        writeStorage(THEME_STORAGE_KEY, nextTheme);
        applyTheme(nextTheme);
    });

    dom.dashboardToggle.addEventListener("click", async () => {
        app.state.dashboardOpen = !app.state.dashboardOpen;
        await renderAll();
        if (app.state.dashboardOpen) {
            dom.dashboardPanel.scrollIntoView({ block: "start", behavior: "smooth" });
        }
    });

    dom.dashboardClose.addEventListener("click", async () => {
        app.state.dashboardOpen = false;
        await renderAll();
    });

    dom.favoritesToggle.addEventListener("click", async () => {
        if (app.state.favoritesOpen) {
            closeFavoritesModalState();
        } else {
            openFavoritesModalState();
        }
        await renderAll();
    });

    dom.disciplineGrid.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-discipline-filter]");
        if (!button) {
            return;
        }
        const group = JOURNAL_GROUPS.find((item) => item.label === button.dataset.disciplineFilter);
        if (!group) {
            return;
        }
        closeArticleModalState();
        closeFavoritesModalState();
        app.state.mode = "search";
        app.state.journals = getAvailableJournalsForGroup(group);
        app.state.page = 1;
        clearActiveNavigationSelection();
        await renderAll();
        dom.searchInput.focus();
        dom.searchInput.scrollIntoView({ block: "center", behavior: "smooth" });
    });

    dom.tabbar.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-mode]");
        if (!button) {
            return;
        }
        app.state.mode = button.dataset.mode;
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.searchForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        app.state.q = dom.searchInput.value;
        app.state.page = 1;
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.searchInput.addEventListener("input", () => {
        clearTimeout(searchDebounceId);
        searchDebounceId = setTimeout(async () => {
            app.state.q = dom.searchInput.value;
            app.state.page = 1;
            clearActiveNavigationSelection();
            await renderAll();
        }, 240);
    });

    dom.journalFilterQuery.addEventListener("input", async () => {
        app.state.journalFacetQuery = dom.journalFilterQuery.value;
        await renderAll();
    });

    dom.quickSearches.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-quick-query]");
        if (!button) {
            return;
        }
        app.state.mode = "search";
        app.state.q = button.dataset.quickQuery || "";
        dom.searchInput.value = app.state.q;
        app.state.page = 1;
        clearActiveNavigationSelection();
        await renderAll();
        dom.searchInput.focus();
        dom.searchInput.setSelectionRange(dom.searchInput.value.length, dom.searchInput.value.length);
    });

    dom.sortSelect.addEventListener("change", async () => {
        app.state.sort = dom.sortSelect.value;
        app.state.page = 1;
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.yearFrom.addEventListener("change", async () => {
        app.state.yearFrom = dom.yearFrom.value;
        app.state.page = 1;
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.yearTo.addEventListener("change", async () => {
        app.state.yearTo = dom.yearTo.value;
        app.state.page = 1;
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.hasAbstractOnly.addEventListener("change", async () => {
        app.state.hasAbstractOnly = dom.hasAbstractOnly.checked;
        app.state.page = 1;
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.filterContainer.addEventListener("change", async (event) => {
        const checkbox = event.target.closest("[data-journal-filter]");
        if (!checkbox) {
            return;
        }
        const journal = checkbox.dataset.journalFilter;
        const next = new Set(app.state.journals);
        if (checkbox.checked) {
            next.add(journal);
        } else {
            next.delete(journal);
        }
        app.state.journals = [...next];
        app.state.page = 1;
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.filterContainer.addEventListener("click", async (event) => {
        const removeButton = event.target.closest("[data-remove-journal]");
        if (removeButton) {
            app.state.journals = app.state.journals.filter((journal) => journal !== removeButton.dataset.removeJournal);
            app.state.page = 1;
            clearActiveNavigationSelection();
            await renderAll();
            return;
        }
        const clearButton = event.target.closest("[data-clear-filter]");
        if (clearButton?.dataset.clearFilter === "journals") {
            app.state.journals = [];
            app.state.page = 1;
            clearActiveNavigationSelection();
            await renderAll();
        }
    });

    dom.clearFilters.addEventListener("click", async () => {
        resetSearchFilters();
        await renderAll();
    });

    dom.clearQuery.addEventListener("click", async () => {
        app.state.q = "";
        app.state.page = 1;
        dom.searchInput.value = "";
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.activeFilters.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-clear-filter]");
        if (!button) {
            return;
        }
        const kind = button.dataset.clearFilter;
        if (kind === "query") {
            app.state.q = "";
            dom.searchInput.value = "";
        } else if (kind === "year") {
            app.state.yearFrom = "";
            app.state.yearTo = "";
        } else if (kind === "journals") {
            app.state.journals = [];
        } else if (kind === "abstract") {
            app.state.hasAbstractOnly = false;
        } else if (kind === "all") {
            app.state.q = "";
            dom.searchInput.value = "";
            resetSearchFilters();
        }
        app.state.page = 1;
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.pagination.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-page-action]");
        if (!button || button.disabled) {
            return;
        }
        app.state.page += button.dataset.pageAction === "next" ? 1 : -1;
        app.state.page = Math.max(1, app.state.page);
        clearActiveNavigationSelection();
        await renderAll();
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    const openArticleFromTrigger = async (event) => {
        const trigger = event.target.closest("[data-open-article]");
        if (!trigger) {
            return;
        }
        const article = app.articleCache.get(trigger.dataset.openArticle);
        if (!article) {
            return;
        }
        setActiveNavigationKey(trigger.dataset.openArticle);
        openArticleModalState(article);
        await renderAll();
    };

    const favoriteFromTrigger = async (event) => {
        const trigger = event.target.closest("[data-favorite-article]");
        if (!trigger) {
            return;
        }
        setActiveNavigationKey(trigger.dataset.favoriteArticle);
        await toggleFavoriteByKey(trigger.dataset.favoriteArticle);
    };

    dom.resultList.addEventListener("click", openArticleFromTrigger);
    dom.articleList.addEventListener("click", openArticleFromTrigger);
    dom.resultList.addEventListener("click", favoriteFromTrigger);
    dom.articleList.addEventListener("click", favoriteFromTrigger);

    dom.journalRail.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-browse-journal]");
        if (!button) {
            return;
        }
        app.state.browseJournal = button.dataset.browseJournal;
        app.state.browseYear = "";
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.browseJournalQuery.addEventListener("input", async () => {
        app.state.browseJournalQuery = dom.browseJournalQuery.value;
        await renderAll();
    });

    dom.yearGrid.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-browse-year]");
        if (!button) {
            return;
        }
        app.state.browseYear = button.dataset.browseYear;
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.browseBreadcrumbs.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-browse-reset]");
        if (!button) {
            return;
        }
        if (button.dataset.browseReset === "all") {
            app.state.browseJournal = "";
            app.state.browseYear = "";
        } else {
            app.state.browseYear = "";
        }
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.browseReset.addEventListener("click", async () => {
        app.state.browseJournal = "";
        app.state.browseYear = "";
        clearActiveNavigationSelection();
        await renderAll();
    });

    dom.modal.addEventListener("click", async (event) => {
        if (event.target.closest("[data-close-modal]") || event.target.closest("#modal-close")) {
            closeArticleModalState();
            await renderAll();
            return;
        }

        const favoriteButton = event.target.closest("[data-favorite-article]");
        if (favoriteButton) {
            await toggleFavoriteByKey(favoriteButton.dataset.favoriteArticle);
            return;
        }

        const copyCitationButton = event.target.closest("[data-copy-citation]");
        if (copyCitationButton) {
            const citationKind = copyCitationButton.dataset.copyCitation;
            const citationMap = {
                bibtex: dom.citationBibtex.textContent,
                apa: dom.citationApa.textContent,
                mla: dom.citationMla.textContent,
            };
            const citation = citationMap[citationKind];
            if (citation) {
                await copyText(citation);
            }
            return;
        }

        const copyLinkButton = event.target.closest("[data-copy-link]");
        if (copyLinkButton) {
            await copyText(dom.modal.dataset.shareUrl || window.location.href);
            return;
        }

        const copyAiPromptButton = event.target.closest("[data-copy-ai-prompt]");
        if (copyAiPromptButton) {
            await copyText(dom.modal.dataset.aiPrompt || "");
        }
    });

    dom.favoritesModal.addEventListener("click", async (event) => {
        if (event.target.closest("[data-close-favorites]") || event.target.closest("#favorites-close")) {
            closeFavoritesModalState();
            await renderAll();
            return;
        }

        const openTrigger = event.target.closest("[data-open-article]");
        if (openTrigger) {
            const article = app.articleCache.get(openTrigger.dataset.openArticle);
            if (!article) {
                return;
            }
            closeFavoritesModalState();
            setActiveNavigationKey(openTrigger.dataset.openArticle);
            openArticleModalState(article);
            await renderAll();
            return;
        }

        const favoriteButton = event.target.closest("[data-favorite-article]");
        if (favoriteButton) {
            await toggleFavoriteByKey(favoriteButton.dataset.favoriteArticle);
        }
    });

    dom.copyFavoritesBibtex.addEventListener("click", async () => {
        const bibtex = buildFavoritesBibtex();
        if (bibtex) {
            await copyText(bibtex);
        }
    });

    dom.exportFavoritesBibtex.addEventListener("click", () => {
        const bibtex = buildFavoritesBibtex();
        if (bibtex) {
            downloadTextFile(buildExportFilename("bib"), bibtex, "application/x-bibtex;charset=utf-8");
        }
    });

    dom.exportFavoritesCsv.addEventListener("click", () => {
        const csv = buildFavoritesCsv();
        if (csv) {
            downloadTextFile(buildExportFilename("csv"), csv, "text/csv;charset=utf-8");
        }
    });

    dom.clearFavorites.addEventListener("click", async () => {
        app.favorites.clear();
        saveFavoritesToStorage();
        await renderAll();
    });

    document.addEventListener("keydown", async (event) => {
        const activeTag = document.activeElement?.tagName || "";
        const editingElsewhere =
            document.activeElement &&
            document.activeElement !== dom.searchInput &&
            (activeTag === "INPUT" || activeTag === "TEXTAREA" || activeTag === "SELECT" || document.activeElement.isContentEditable);
        if (event.key === "Escape" && !dom.favoritesModal.classList.contains("hidden")) {
            closeFavoritesModalState();
            await renderAll();
            return;
        }
        if (event.key === "Escape" && !dom.modal.classList.contains("hidden")) {
            closeArticleModalState();
            await renderAll();
            return;
        }
        if (event.key === "/" && document.activeElement !== dom.searchInput && dom.modal.classList.contains("hidden") && dom.favoritesModal.classList.contains("hidden")) {
            event.preventDefault();
            app.state.mode = "search";
            await renderAll();
            dom.searchInput.focus();
        }
        if ((event.key === "ArrowDown" || event.key === "ArrowUp") && !editingElsewhere && dom.modal.classList.contains("hidden")) {
            const moved = moveActiveNavigation(event.key === "ArrowDown" ? 1 : -1);
            if (moved) {
                event.preventDefault();
            }
        }
        if (event.key === "Enter" && document.activeElement === dom.searchInput && app.state.activeResultKey && dom.modal.classList.contains("hidden")) {
            const article = app.articleCache.get(app.state.activeResultKey);
            if (article) {
                event.preventDefault();
                openArticleModalState(article);
                await renderAll();
                return;
            }
        }
        if (event.key === "Escape" && document.activeElement === dom.searchInput) {
            dom.searchInput.blur();
        } else if (event.key === "Escape" && app.state.activeResultKey) {
            clearActiveNavigationSelection();
            syncActiveNavigationButtons();
        }
    });

    window.addEventListener("hashchange", async () => {
        const activeDoi = parseArticleHash();
        closeFavoritesModalState();
        if (!activeDoi) {
            closeArticleModalState();
        } else {
            app.state.activeArticleDoi = activeDoi;
            app.state.activeArticleKey = `doi:${activeDoi.toLowerCase()}`;
        }
        await renderAll();
    });

    window.addEventListener("popstate", async () => {
        hydrateStateFromUrl();
        await renderAll();
    });
}

async function init() {
    cacheDom();
    loadClientPreferences();
    hydrateStateFromUrl();
    bindEvents();
    renderTabs();
    renderEngineStatus();
    renderDatasetMeta();
    await initDataSources();
    await renderAll();
}

window.addEventListener("DOMContentLoaded", init);
