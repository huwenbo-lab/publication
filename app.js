const SQL_JS_BASE = "vendor/sqljs";
const PAGE_SIZE = 50;
const FAVORITES_STORAGE_KEY_V1 = "publication:favorites:v1";
const FAVORITES_STORAGE_KEY_V2 = "publication:favorites:v2";
const FAVORITES_ALL_FOLDER = "__all__";
const FAVORITES_UNCATEGORIZED_FOLDER = "__uncategorized__";
const THEME_STORAGE_KEY = "publication:theme:v1";
const RAW_BASE = "https://raw.githubusercontent.com/huwenbo-lab/publication/main";

const SORT_LABELS = {
    year_desc: "Newest",
    year_asc: "Oldest",
    title: "Title",
    author: "Author",
    journal: "Journal",
};

const JOURNAL_LABELS = {
    "American Journal of Sociology": "AJS",
    "American Sociological Review": "ASR",
    "Annual Review of Sociology": "ARS",
    "Asian Population Studies": "APS",
    "British Journal of Sociology": "BJS",
    "British Journal of Sociology of Education": "BJSE",
    "Chinese Journal of Sociology": "CJS",
    "Chinese Sociological Review": "CSR",
    "Demographic Research": "DR",
    "Demography": "Demography",
    "European Journal of Population": "EJP",
    "European Sociological Review": "ESR",
    "Gender & Society": "G&S",
    "Journal of Family Issues": "JFI",
    "Journal of Family Theory & Review": "JFT&R",
    "Journal of Marriage and Family": "JMF",
    "Population and Development Review": "PDR",
    "Research in Social Stratification and Mobility": "RSSM",
    "Social Forces": "SF",
    "Social Science Research": "SSR",
    "Sociological Science": "SocSci",
    "Sociology": "Sociology",
    "Sociology of Education": "SOE",
    "Socius": "Socius",
    "Work, Employment and Society": "WES",
};

const dom = {};
let searchDebounceId = null;
let renderSequence = 0;

function createFavoriteLibrary() {
    return {
        version: 2,
        folders: [],
        items: {},
    };
}

const app = {
    db: null,
    dbColumns: new Set(),
    meta: null,
    facets: null,
    fallbackData: null,
    authorIndex: null,
    articleCache: new Map(),
    favoriteLibrary: createFavoriteLibrary(),
    engine: "loading",
    loading: true,
    loadingText: "Loading",
    sqliteInitError: "",
    theme: "light",
    state: {
        view: "main",
        q: "",
        searchMode: "all",
        journals: [],
        yearFrom: "",
        yearTo: "",
        hasAbstractOnly: false,
        filtersOpen: false,
        sort: "year_desc",
        sortOpen: false,
        visibleCount: PAGE_SIZE,
        expandedKey: "",
        activeFavoriteFolderId: FAVORITES_ALL_FOLDER,
        expandedFavoriteFolders: new Set(),
        draggingFavoriteKey: "",
        exportOpen: false,
        authorMin: 10,
    },
};

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
    return new Intl.NumberFormat("zh-CN").format(Number(value || 0));
}

function normalizeText(value) {
    return String(value ?? "")
        .toLowerCase()
        .replace(/\s+/g, " ")
        .trim();
}

function normalizeSearchTokenText(value) {
    return String(value ?? "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, " ")
        .replace(/\s+/g, " ")
        .trim();
}

function tokenizeBasicQuery(query) {
    return normalizeSearchTokenText(query).split(/\s+/).filter(Boolean);
}

function escapeFtsTerm(term) {
    return String(term || "").replace(/"/g, '""');
}

function buildSimpleFtsQuery(query, columns = []) {
    const tokens = tokenizeBasicQuery(query);
    if (!tokens.length) {
        return "";
    }
    const tokenQuery = tokens.map((token) => `"${escapeFtsTerm(token)}"`).join(" ");
    if (!columns.length) {
        return tokenQuery;
    }
    return columns.map((column) => `${column}:(${tokenQuery})`).join(" OR ");
}

function truncateText(value, maxChars = 280) {
    const text = String(value ?? "").trim();
    if (!text) {
        return "";
    }
    return text.length > maxChars ? `${text.slice(0, maxChars).trim()}…` : text;
}

function buildDoiUrl(doi) {
    const clean = String(doi ?? "").trim();
    return clean ? `https://doi.org/${clean}` : "";
}

function buildScholarUrl(title) {
    return `https://scholar.google.com/scholar?q=${encodeURIComponent(title ?? "")}`;
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
    if (numericYear >= 2020 && numericYear <= 2026) return "2020_2026";
    if (numericYear >= 2010 && numericYear <= 2019) return "2010_2019";
    if (numericYear >= 2000 && numericYear <= 2009) return "2000_2009";
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
    const segments = clean.split("/").filter(Boolean).map((segment) => encodeURIComponent(segment));
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

function buildAiResourceLinks(article) {
    const journalSlug = safeJournalFilename(article.journal);
    const period = getPeriodKey(article.year);
    return {
        overview: buildRepoRawUrl("lit_db/overview.md"),
        journalTitles: journalSlug ? buildRepoRawUrl(`lit_db/titles/by_journal/${journalSlug}.md`) : "",
        journalAbstracts: journalSlug && period ? buildRepoRawUrl(`lit_db/abstracts/${period}/${journalSlug}.md`) : "",
        articleJson: buildArticleApiUrl(article.doi),
    };
}

function buildAiPrompt(article, resources = buildAiResourceLinks(article)) {
    const lines = [];
    lines.push("请基于以下资料分析这篇文章，并优先引用文章 JSON 中的结构化字段：");
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
        title: String(record?.title ?? "").trim(),
        abstract: String(record?.abstract ?? "").trim(),
        authors: String(record?.authors ?? "").trim(),
        journal: String(record?.journal ?? "").trim(),
        year: record?.year ? Number(record.year) : "",
        doi: String(record?.doi ?? "").trim(),
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

function getArticleByKey(key) {
    return app.articleCache.get(key) || app.favoriteLibrary.items[key]?.article || null;
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

function createFolderId() {
    return `folder-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function normalizeFavoriteFolder(folder) {
    const name = String(folder?.name || "").trim();
    if (!name) {
        return null;
    }
    return {
        id: String(folder.id || createFolderId()),
        name,
        parentId: folder.parentId ? String(folder.parentId) : "",
        createdAt: folder.createdAt || new Date().toISOString(),
        updatedAt: folder.updatedAt || folder.createdAt || new Date().toISOString(),
    };
}

function normalizeFavoriteLibrary(payload) {
    const library = createFavoriteLibrary();
    if (!payload || typeof payload !== "object") {
        return library;
    }

    const folderIds = new Set();
    if (Array.isArray(payload.folders)) {
        for (const rawFolder of payload.folders) {
            const folder = normalizeFavoriteFolder(rawFolder);
            if (!folder || folderIds.has(folder.id)) {
                continue;
            }
            folderIds.add(folder.id);
            library.folders.push(folder);
        }
    }

    const rawItems = payload.items && typeof payload.items === "object" ? payload.items : {};
    for (const [rawKey, entry] of Object.entries(rawItems)) {
        const article = normalizeArticleRecord(entry?.article || entry);
        if (!article.title && !article.doi) {
            continue;
        }
        const key = buildArticleKey(article);
        const folderId = entry?.folderId && folderIds.has(entry.folderId) ? entry.folderId : null;
        library.items[key] = {
            article,
            folderId,
            addedAt: entry?.addedAt || new Date().toISOString(),
            updatedAt: entry?.updatedAt || new Date().toISOString(),
        };
        app.articleCache.set(key, article);
        app.articleCache.delete(rawKey);
    }

    return library;
}

function favoriteLibraryFromV1(items) {
    const library = createFavoriteLibrary();
    if (!Array.isArray(items)) {
        return library;
    }
    for (const item of items) {
        const article = normalizeArticleRecord(item);
        if (!article.title && !article.doi) {
            continue;
        }
        const key = buildArticleKey(article);
        library.items[key] = {
            article,
            folderId: null,
            addedAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
        };
        app.articleCache.set(key, article);
    }
    return library;
}

function loadFavoritesFromStorage() {
    const rawV2 = readStorage(FAVORITES_STORAGE_KEY_V2);
    if (rawV2) {
        try {
            app.favoriteLibrary = normalizeFavoriteLibrary(JSON.parse(rawV2));
            return;
        } catch {
            app.favoriteLibrary = createFavoriteLibrary();
        }
    }

    const rawV1 = readStorage(FAVORITES_STORAGE_KEY_V1);
    if (rawV1) {
        try {
            app.favoriteLibrary = favoriteLibraryFromV1(JSON.parse(rawV1));
            saveFavoritesToStorage();
            return;
        } catch {
            app.favoriteLibrary = createFavoriteLibrary();
        }
    }
}

function saveFavoritesToStorage() {
    app.favoriteLibrary.version = 2;
    writeStorage(FAVORITES_STORAGE_KEY_V2, JSON.stringify(app.favoriteLibrary, null, 2));
}

function favoriteCount() {
    return Object.keys(app.favoriteLibrary.items).length;
}

function getFolderById(folderId) {
    return app.favoriteLibrary.folders.find((folder) => folder.id === folderId) || null;
}

function getFolderChildren(parentId = "") {
    return app.favoriteLibrary.folders
        .filter((folder) => (folder.parentId || "") === (parentId || ""))
        .sort((a, b) => a.name.localeCompare(b.name));
}

function getFolderPath(folderId) {
    const folder = getFolderById(folderId);
    if (!folder) {
        return "";
    }
    const names = [folder.name];
    let current = folder;
    while (current.parentId) {
        current = getFolderById(current.parentId);
        if (!current) {
            break;
        }
        names.unshift(current.name);
    }
    return names.join("/");
}

function countItemsInFolder(folderId) {
    return Object.values(app.favoriteLibrary.items)
        .filter((entry) => (entry.folderId || null) === folderId).length;
}

function getFavoriteArticles(folderId = FAVORITES_ALL_FOLDER) {
    return Object.entries(app.favoriteLibrary.items)
        .filter(([, entry]) => {
            if (folderId === FAVORITES_ALL_FOLDER) return true;
            if (folderId === FAVORITES_UNCATEGORIZED_FOLDER) return !entry.folderId;
            return entry.folderId === folderId;
        })
        .map(([key, entry]) => ({
            ...normalizeArticleRecord(entry.article),
            _favoriteKey: key,
            _folderId: entry.folderId || null,
        }))
        .sort(compareArticles);
}

function isFavorite(articleKey) {
    return Boolean(app.favoriteLibrary.items[articleKey]);
}

function addFavorite(article, folderId = null) {
    const normalized = normalizeArticleRecord(article);
    const key = buildArticleKey(normalized);
    const nextFolder = folderId && folderId !== FAVORITES_UNCATEGORIZED_FOLDER ? folderId : null;
    if (nextFolder && !getFolderById(nextFolder)) {
        return false;
    }
    app.articleCache.set(key, normalized);
    app.favoriteLibrary.items[key] = {
        article: normalized,
        folderId: nextFolder,
        addedAt: app.favoriteLibrary.items[key]?.addedAt || new Date().toISOString(),
        updatedAt: new Date().toISOString(),
    };
    saveFavoritesToStorage();
    return true;
}

function toggleFavoriteByKey(articleKey) {
    if (isFavorite(articleKey)) {
        delete app.favoriteLibrary.items[articleKey];
        saveFavoritesToStorage();
        return false;
    }
    const article = getArticleByKey(articleKey);
    if (!article) {
        return false;
    }
    addFavorite(article, null);
    return true;
}

function moveFavoriteToFolder(articleKey, folderId) {
    const article = getArticleByKey(articleKey);
    if (!article) {
        return false;
    }
    return addFavorite(article, folderId);
}

function ensureFavoriteFolderPath(pathText) {
    const segments = String(pathText || "")
        .split("/")
        .map((segment) => segment.trim())
        .filter(Boolean);
    if (!segments.length) {
        return null;
    }
    let parentId = "";
    let current = null;
    for (const segment of segments) {
        current = app.favoriteLibrary.folders.find((folder) =>
            (folder.parentId || "") === parentId &&
            folder.name.toLowerCase() === segment.toLowerCase()
        );
        if (!current) {
            current = normalizeFavoriteFolder({
                id: createFolderId(),
                name: segment,
                parentId,
            });
            app.favoriteLibrary.folders.push(current);
        }
        parentId = current.id;
        app.state.expandedFavoriteFolders.add(current.parentId || "");
    }
    saveFavoritesToStorage();
    return current;
}

function renameFavoriteFolder(folderId, nextName) {
    const folder = getFolderById(folderId);
    const cleanName = String(nextName || "").trim();
    if (!folder || !cleanName) {
        return false;
    }
    const siblingExists = app.favoriteLibrary.folders.some((item) =>
        item.id !== folder.id &&
        (item.parentId || "") === (folder.parentId || "") &&
        item.name.toLowerCase() === cleanName.toLowerCase()
    );
    if (siblingExists) {
        return false;
    }
    folder.name = cleanName;
    folder.updatedAt = new Date().toISOString();
    saveFavoritesToStorage();
    return true;
}

function deleteFavoriteFolder(folderId) {
    const folder = getFolderById(folderId);
    if (!folder || getFolderChildren(folderId).length || countItemsInFolder(folderId) > 0) {
        return false;
    }
    app.favoriteLibrary.folders = app.favoriteLibrary.folders.filter((item) => item.id !== folderId);
    app.state.activeFavoriteFolderId = FAVORITES_ALL_FOLDER;
    app.state.expandedFavoriteFolders.delete(folderId);
    saveFavoritesToStorage();
    return true;
}

function escapeCsvCell(value) {
    const text = String(value ?? "");
    return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
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
    if (!names.length) return "Unknown";
    if (names.length === 1) return names[0];
    if (names.length === 2) return `${names[0]} & ${names[1]}`;
    return `${names.slice(0, -1).join(", ")}, & ${names[names.length - 1]}`;
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
    if (article.year) lines.push(`  year = {${article.year}},`);
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
        ` ${article.title || "Untitled"}.`,
        article.journal ? ` ${article.journal}.` : "",
        article.doi ? ` ${buildDoiUrl(article.doi)}` : "",
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

function buildFavoritesBibtex(folderId = app.state.activeFavoriteFolderId) {
    return getFavoriteArticles(folderId).map(formatBibtex).join("\n\n");
}

function buildFavoritesJson(folderId = app.state.activeFavoriteFolderId) {
    const articles = getFavoriteArticles(folderId);
    return JSON.stringify({
        version: 2,
        exported_at: new Date().toISOString(),
        folder: getFavoriteFolderLabel(folderId),
        articles,
    }, null, 2);
}

function buildFavoritesCsv(folderId = app.state.activeFavoriteFolderId) {
    const rows = [
        ["folder_path", "title", "authors", "journal", "year", "doi", "abstract"],
        ...getFavoriteArticles(folderId).map((article) => ([
            article._folderId ? getFolderPath(article._folderId) : "未分类",
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

function applyTheme(theme) {
    app.theme = theme === "dark" ? "dark" : "light";
    document.body.dataset.theme = app.theme;
    if (dom.themeToggle) {
        dom.themeToggle.setAttribute("aria-pressed", app.theme === "dark" ? "true" : "false");
    }
}

function loadClientPreferences() {
    loadFavoritesFromStorage();
    const storedTheme = readStorage(THEME_STORAGE_KEY);
    applyTheme(storedTheme === "dark" || storedTheme === "light" ? storedTheme : detectPreferredTheme());
}

async function fetchJsonResource(relativePath) {
    const response = await fetch(relativePath, { cache: "no-cache" });
    if (!response.ok) {
        throw new Error(`${relativePath} unavailable (${response.status})`);
    }
    return response.json();
}

async function initSqliteEngine() {
    if (typeof initSqlJs !== "function") {
        throw new Error("SQL.js runtime unavailable");
    }
    const SQL = await initSqlJs({
        locateFile: (file) => `${SQL_JS_BASE}/${file}`,
    });
    const response = await fetch("literature.db");
    if (!response.ok) {
        throw new Error(`literature.db unavailable (${response.status})`);
    }
    const bytes = new Uint8Array(await response.arrayBuffer());
    app.db = new SQL.Database(bytes);
    app.dbColumns = new Set(queryDb("PRAGMA table_info(articles)").map((row) => row.name));
    app.meta = loadMetaFromDb();
    app.facets = loadFacetsFromDb();
    app.engine = "sqlite";
    app.sqliteInitError = "";
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
    `)[0] || {};
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
    return queryDb(`
        SELECT
            journal,
            COUNT(*) AS total,
            MIN(year) AS min_year,
            MAX(year) AS max_year
        FROM articles_meta
        GROUP BY journal
        ORDER BY journal COLLATE NOCASE ASC
    `).map((row) => ({
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
    const [overviewResult, journalsResult] = await Promise.allSettled([
        fetchJsonResource("api/overview.json"),
        fetchJsonResource("api/journals.json"),
    ]);
    if (!app.meta && overviewResult.status === "fulfilled") {
        app.meta = buildMetaFromSummary(overviewResult.value?.summary);
    }
    if (!app.facets && journalsResult.status === "fulfilled") {
        app.facets = buildFacetsFromStaticIndex(journalsResult.value);
    }
}

async function ensureFallbackData() {
    if (app.fallbackData) {
        return;
    }
    const response = await fetch("data.json", { cache: "no-cache" });
    if (!response.ok) {
        throw new Error(`data.json unavailable (${response.status})`);
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
        if (hasAbstract) withAbstract += 1;
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
}

async function initDataSources() {
    app.loading = true;
    app.loadingText = "Loading";
    renderAll();
    try {
        await initSqliteEngine();
    } catch (error) {
        console.warn(error);
        app.engine = "fallback";
        app.sqliteInitError = String(error?.message || "");
        await loadStaticIndexes();
        await ensureFallbackData();
    }
    await loadStaticIndexes();
    app.loading = false;
}

function buildDbMatchQuery(query) {
    const raw = query.trim();
    if (!raw) {
        return "";
    }
    if (app.state.searchMode === "title_abstract") {
        return buildSimpleFtsQuery(raw, ["title", "abstract"]);
    }
    if (app.state.searchMode === "author") {
        const columns = app.dbColumns.has("author_search") ? ["author_search", "authors"] : ["authors"];
        return buildSimpleFtsQuery(raw, columns);
    }
    if (app.state.searchMode === "journal") {
        return app.dbColumns.has("journal_search")
            ? buildSimpleFtsQuery(raw, ["journal_search"])
            : buildSimpleFtsQuery(raw, ["journal"]);
    }
    return buildSimpleFtsQuery(raw);
}

function buildWhereClause(params, query, includeMatch = true) {
    const clauses = [];
    const matchQuery = buildDbMatchQuery(query);
    if (includeMatch && matchQuery) {
        clauses.push("articles MATCH $query");
        params.$query = matchQuery;
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

function getOrderByClause() {
    if (app.state.sort === "journal") {
        return "ORDER BY m.journal COLLATE NOCASE ASC, m.year DESC, articles.title COLLATE NOCASE ASC";
    }
    if (app.state.sort === "year_asc") {
        return "ORDER BY m.year ASC, articles.title COLLATE NOCASE ASC";
    }
    if (app.state.sort === "author") {
        return "ORDER BY articles.authors COLLATE NOCASE ASC, m.year DESC, articles.title COLLATE NOCASE ASC";
    }
    if (app.state.sort === "title") {
        return "ORDER BY articles.title COLLATE NOCASE ASC, m.year DESC";
    }
    return "ORDER BY m.year DESC, articles.title COLLATE NOCASE ASC";
}

function searchWithDb() {
    const query = app.state.q.trim();
    const params = {
        $limit: app.state.visibleCount,
        $offset: 0,
    };
    const whereClause = buildWhereClause(params, query, true);
    const countParams = {};
    const countWhereClause = buildWhereClause(countParams, query, true);
    const previewExpr = query
        ? `
            COALESCE(
                NULLIF(snippet(articles, 1, '<mark>', '</mark>', '...', 24), ''),
                NULLIF(snippet(articles, 0, '<mark>', '</mark>', '...', 16), ''),
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
        ${getOrderByClause()}
        LIMIT $limit OFFSET $offset
    `, params);

    return { total, rows, usedFallback: false };
}

function getSearchHaystackForMode(articleLike) {
    const title = articleLike.title ?? articleLike["Article Title"] ?? "";
    const abstract = articleLike.abstract ?? articleLike["Abstract"] ?? "";
    const authors = articleLike.authors ?? articleLike["Author Full Names"] ?? "";
    const journal = articleLike.journal ?? articleLike["Source Title"] ?? "";
    const year = articleLike.year ?? articleLike["Publication Year"] ?? "";
    if (app.state.searchMode === "title_abstract") return `${title} ${abstract}`;
    if (app.state.searchMode === "author") return authors;
    if (app.state.searchMode === "journal") return journal;
    return `${title} ${abstract} ${authors} ${journal} ${year}`;
}

function rowMatchesSearchMode(articleLike, tokens) {
    if (!tokens.length) {
        return true;
    }
    const haystack = normalizeSearchTokenText(getSearchHaystackForMode(articleLike));
    return tokens.every((token) => haystack.includes(token));
}

function rowMatchesCommonFilters(articleLike) {
    const journal = String(articleLike.journal ?? articleLike["Source Title"] ?? "").trim();
    const year = Number.parseInt(articleLike.year ?? articleLike["Publication Year"], 10);
    const abstract = String(articleLike.abstract ?? articleLike["Abstract"] ?? "").trim();
    if (app.state.journals.length && !app.state.journals.includes(journal)) {
        return false;
    }
    if (app.state.yearFrom && !Number.isNaN(year) && year < Number(app.state.yearFrom)) {
        return false;
    }
    if (app.state.yearTo && !Number.isNaN(year) && year > Number(app.state.yearTo)) {
        return false;
    }
    if (app.state.hasAbstractOnly && !abstract) {
        return false;
    }
    return true;
}

function sortSearchRows(rows) {
    if (app.state.sort === "journal") {
        rows.sort((a, b) =>
            String(a.journal || "").localeCompare(String(b.journal || "")) ||
            Number(b.year || 0) - Number(a.year || 0)
        );
    } else if (app.state.sort === "year_asc") {
        rows.sort((a, b) => Number(a.year || 0) - Number(b.year || 0));
    } else if (app.state.sort === "author") {
        rows.sort((a, b) =>
            String(a.authors || "").localeCompare(String(b.authors || "")) ||
            Number(b.year || 0) - Number(a.year || 0)
        );
    } else if (app.state.sort === "title") {
        rows.sort((a, b) => String(a.title || "").localeCompare(String(b.title || "")));
    } else {
        rows.sort((a, b) =>
            Number(b.year || 0) - Number(a.year || 0) ||
            String(a.title || "").localeCompare(String(b.title || ""))
        );
    }
}

function filterFallbackRows() {
    const tokens = tokenizeBasicQuery(app.state.q);
    let rows = app.fallbackData.filter((item) =>
        rowMatchesCommonFilters(item) && rowMatchesSearchMode(item, tokens)
    );
    rows = rows.map((item) => ({
        title: item["Article Title"] || "Untitled",
        authors: item["Author Full Names"] || "Unknown",
        journal: item["Source Title"] || "",
        year: Number.parseInt(item["Publication Year"], 10) || "",
        doi: item["DOI"] || "",
        preview: truncateText(item["Abstract"] || "", 280),
        abstract: item["Abstract"] || "",
    }));
    sortSearchRows(rows);
    return {
        total: rows.length,
        rows: rows.slice(0, app.state.visibleCount),
        usedFallback: true,
    };
}

async function loadSearchResults() {
    if (app.loading) {
        return { total: 0, rows: [], loading: true };
    }
    if (app.engine === "fallback") {
        await ensureFallbackData();
        return filterFallbackRows();
    }
    try {
        return searchWithDb();
    } catch (error) {
        console.error(error);
        return { total: 0, rows: [], error };
    }
}

async function ensureAuthorIndex() {
    if (app.authorIndex) {
        return app.authorIndex;
    }
    app.authorIndex = await fetchJsonResource("api/authors.json");
    return app.authorIndex;
}

function cacheDom() {
    dom.topbarMeta = $("topbar-meta");
    dom.favoritesToggle = $("favorites-toggle");
    dom.favoriteCount = $("favorite-count");
    dom.themeToggle = $("theme-toggle");
    dom.authorsLink = $("authors-link");
    dom.journalStrip = $("journal-strip");
    dom.journalPills = $("journal-pills");
    dom.mainView = $("main-view");
    dom.favoritesView = $("favorites-view");
    dom.authorsView = $("authors-view");
    dom.globalLoading = $("global-loading");
    dom.loadingText = $("loading-text");
    dom.searchForm = $("search-form");
    dom.searchInput = $("search-input");
    dom.searchModeSelect = $("search-mode-select");
    dom.resultSummary = $("result-summary");
    dom.filtersToggle = $("filters-toggle");
    dom.filtersBadge = $("filters-badge");
    dom.filtersPanel = $("filters-panel");
    dom.yearFrom = $("year-from");
    dom.yearTo = $("year-to");
    dom.hasAbstractOnly = $("has-abstract-only");
    dom.selectedJournalList = $("selected-journal-list");
    dom.sortToggle = $("sort-toggle");
    dom.sortMenu = $("sort-menu");
    dom.resultList = $("result-list");
    dom.loadMoreRow = $("load-more-row");
    dom.loadMore = $("load-more");
    dom.favoritesBack = $("favorites-back");
    dom.favoritesSummary = $("favorites-summary");
    dom.exportToggle = $("export-toggle");
    dom.exportMenu = $("export-menu");
    dom.exportFavoritesBibtex = $("export-favorites-bibtex");
    dom.exportFavoritesCsv = $("export-favorites-csv");
    dom.exportFavoritesJson = $("export-favorites-json");
    dom.favoriteFolderPath = $("favorite-folder-path");
    dom.createFavoriteFolder = $("create-favorite-folder");
    dom.renameFavoriteFolder = $("rename-favorite-folder");
    dom.deleteFavoriteFolder = $("delete-favorite-folder");
    dom.favoriteFolderTree = $("favorite-folder-tree");
    dom.favoritesList = $("favorites-list");
    dom.authorsBack = $("authors-back");
    dom.authorsSummary = $("authors-summary");
    dom.authorMinInput = $("author-min-input");
    dom.authorList = $("author-list");
    dom.articleSchema = $("article-schema");
}

function journalLabel(journal) {
    return JOURNAL_LABELS[journal] || journal;
}

function renderTopbar() {
    if (app.meta) {
        dom.topbarMeta.textContent = `${formatNumber(app.meta.total)} · ${formatNumber(app.meta.journals)} journals`;
    } else {
        dom.topbarMeta.textContent = app.loading ? "Loading" : "0 · 0 journals";
    }
    const count = favoriteCount();
    dom.favoriteCount.textContent = formatNumber(count);
    dom.favoritesToggle.classList.toggle("is-active", app.state.view === "favorites" || count > 0);
    dom.favoritesToggle.setAttribute("aria-pressed", app.state.view === "favorites" ? "true" : "false");
    dom.authorsLink.classList.toggle("is-active", app.state.view === "authors");
}

function renderLoading() {
    dom.globalLoading.hidden = !app.loading;
    dom.loadingText.textContent = app.loadingText;
}

function renderViews() {
    dom.mainView.classList.toggle("active", app.state.view === "main");
    dom.favoritesView.classList.toggle("active", app.state.view === "favorites");
    dom.authorsView.classList.toggle("active", app.state.view === "authors");
    dom.journalStrip.hidden = app.state.view !== "main";
}

function renderJournalPills() {
    if (!app.facets?.length) {
        dom.journalPills.innerHTML = "";
        return;
    }
    const selected = new Set(app.state.journals);
    const allActive = selected.size === 0;
    const pills = [
        `<button class="journal-pill ${allActive ? "active" : ""}" type="button" data-journal-pill="__all__">All</button>`,
        ...app.facets.map((facet) => `
            <button
                class="journal-pill ${selected.has(facet.journal) ? "active" : ""}"
                type="button"
                title="${escapeHtml(facet.journal)}"
                data-journal-pill="${escapeHtml(facet.journal)}"
            >${escapeHtml(journalLabel(facet.journal))}</button>
        `),
    ];
    dom.journalPills.innerHTML = pills.join("");
}

function activeFilterCount() {
    let count = 0;
    if (app.state.yearFrom || app.state.yearTo) count += 1;
    if (app.state.hasAbstractOnly) count += 1;
    if (app.state.journals.length) count += app.state.journals.length;
    return count;
}

function renderFilters() {
    dom.filtersPanel.hidden = !app.state.filtersOpen;
    dom.filtersToggle.setAttribute("aria-expanded", app.state.filtersOpen ? "true" : "false");
    const count = activeFilterCount();
    dom.filtersBadge.hidden = count === 0;
    dom.filtersBadge.textContent = formatNumber(count);
    dom.yearFrom.value = app.state.yearFrom;
    dom.yearTo.value = app.state.yearTo;
    dom.hasAbstractOnly.checked = app.state.hasAbstractOnly;
    dom.selectedJournalList.innerHTML = app.state.journals.map((journal) => `
        <button type="button" class="selected-journal-chip" data-remove-journal="${escapeHtml(journal)}">
            <span>${escapeHtml(journalLabel(journal))}</span>
            <span aria-hidden="true">×</span>
        </button>
    `).join("");
}

function renderSortMenu() {
    dom.sortToggle.textContent = `Sort: ${SORT_LABELS[app.state.sort] || "Newest"} ▾`;
    dom.sortToggle.setAttribute("aria-expanded", app.state.sortOpen ? "true" : "false");
    dom.sortMenu.hidden = !app.state.sortOpen;
    dom.sortMenu.querySelectorAll("[data-sort-value]").forEach((button) => {
        button.classList.toggle("active", button.dataset.sortValue === app.state.sort);
    });
}

function renderArticleSchema(article) {
    if (!dom.articleSchema) {
        return;
    }
    if (!article) {
        dom.articleSchema.textContent = "";
        return;
    }
    const doiUrl = buildDoiUrl(article.doi);
    const schema = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        headline: article.title || "Untitled",
        name: article.title || "Untitled",
        abstract: article.abstract || "",
        author: parseAuthorList(article.authors).map((author) => ({
            "@type": "Person",
            name: author,
        })),
        isPartOf: {
            "@type": "Periodical",
            name: article.journal || "",
        },
        datePublished: article.year ? String(article.year) : "",
        identifier: article.doi ? [{
            "@type": "PropertyValue",
            propertyID: "DOI",
            value: article.doi,
        }] : [],
        url: doiUrl || buildArticleApiUrl(article.doi) || "",
    };
    dom.articleSchema.textContent = JSON.stringify(schema, null, 2);
}

function buildFavoriteFolderOptions(articleKey) {
    const entry = app.favoriteLibrary.items[articleKey];
    const selectedFolderId = entry?.folderId || FAVORITES_UNCATEGORIZED_FOLDER;
    const options = [
        `<option value="" ${entry ? "" : "selected"}>添加到文件夹</option>`,
        `<option value="${FAVORITES_UNCATEGORIZED_FOLDER}" ${selectedFolderId === FAVORITES_UNCATEGORIZED_FOLDER && entry ? "selected" : ""}>未分类</option>`,
    ];
    const append = (parentId = "", depth = 0) => {
        for (const folder of getFolderChildren(parentId)) {
            const prefix = depth ? `${"　".repeat(depth)}└ ` : "";
            options.push(`<option value="${escapeHtml(folder.id)}" ${selectedFolderId === folder.id ? "selected" : ""}>${prefix}${escapeHtml(folder.name)}</option>`);
            append(folder.id, depth + 1);
        }
    };
    append();
    return options.join("");
}

function renderArticleDetail(article, articleKey, queryActive) {
    const doiUrl = buildDoiUrl(article.doi);
    const abstract = article.abstract
        ? `<p class="article-abstract">${escapeHtml(article.abstract)}</p>`
        : '<p class="article-abstract muted">No abstract</p>';
    return `
        <div class="article-detail">
            <div class="article-detail-inner">
                ${abstract}
                <div class="detail-actions">
                    ${doiUrl ? `<a class="detail-link" href="${doiUrl}" target="_blank" rel="noreferrer">DOI</a>` : ""}
                    <a class="detail-link" href="${buildScholarUrl(article.title)}" target="_blank" rel="noreferrer">Scholar</a>
                    <select class="folder-select" data-folder-select="${escapeHtml(articleKey)}" aria-label="Add to folder">
                        ${buildFavoriteFolderOptions(articleKey)}
                    </select>
                </div>
                <div class="copy-actions">
                    <button class="copy-button" type="button" data-copy-bibtex="${escapeHtml(articleKey)}">BibTeX</button>
                    <button class="copy-button" type="button" data-copy-apa="${escapeHtml(articleKey)}">APA</button>
                    <button class="copy-button" type="button" data-copy-ai="${escapeHtml(articleKey)}">AI prompt</button>
                </div>
            </div>
        </div>
    `;
}

function renderArticleRow(row, queryActive = false) {
    const articleKey = rememberArticle(row);
    const article = app.articleCache.get(articleKey);
    const expanded = app.state.expandedKey === articleKey;
    const favorite = isFavorite(articleKey);
    return `
        <article class="article-row" data-article-row="${escapeHtml(articleKey)}">
            <div class="article-summary">
                <button class="article-open" type="button" data-toggle-article="${escapeHtml(articleKey)}">
                    <span class="article-title">${escapeHtml(article.title || "Untitled")}</span>
                    <span class="article-authors">${escapeHtml(article.authors || "Unknown")}</span>
                    <span class="article-meta">${escapeHtml(article.year || "Unknown")} · ${escapeHtml(journalLabel(article.journal || ""))}</span>
                </button>
                <button
                    class="star-button ${favorite ? "is-active" : ""}"
                    type="button"
                    data-favorite-article="${escapeHtml(articleKey)}"
                    aria-label="${favorite ? "Remove favorite" : "Add favorite"}"
                    aria-pressed="${favorite ? "true" : "false"}"
                >${favorite ? "★" : "☆"}</button>
            </div>
            ${expanded ? renderArticleDetail(article, articleKey, queryActive) : ""}
        </article>
    `;
}

function renderArticleList(result) {
    if (result.loading) {
        dom.resultSummary.textContent = "Showing 0 articles";
        dom.resultList.innerHTML = "";
        dom.loadMoreRow.hidden = true;
        return;
    }
    const shown = Math.min(result.rows.length, result.total);
    dom.resultSummary.textContent = `Showing ${formatNumber(shown)} of ${formatNumber(result.total)} articles`;
    if (!result.rows.length) {
        dom.resultList.innerHTML = '<div class="empty-state">No articles found</div>';
        dom.loadMoreRow.hidden = true;
        renderArticleSchema(null);
        return;
    }
    const queryActive = Boolean(app.state.q.trim());
    dom.resultList.innerHTML = result.rows.map((row) => renderArticleRow(row, queryActive)).join("");
    dom.loadMoreRow.hidden = result.total <= app.state.visibleCount;
    const activeArticle = app.state.expandedKey ? getArticleByKey(app.state.expandedKey) : null;
    renderArticleSchema(activeArticle);
}

async function renderMainView() {
    dom.searchInput.value = app.state.q;
    dom.searchModeSelect.value = app.state.searchMode;
    renderLoading();
    renderFilters();
    renderSortMenu();
    const sequence = ++renderSequence;
    const result = await loadSearchResults();
    if (sequence !== renderSequence || app.state.view !== "main") {
        return;
    }
    renderArticleList(result);
}

function getFavoriteFolderLabel(folderId) {
    if (folderId === FAVORITES_ALL_FOLDER) return "All";
    if (folderId === FAVORITES_UNCATEGORIZED_FOLDER) return "未分类";
    return getFolderPath(folderId) || "Folder";
}

function renderFavoriteFolderButton(id, label, count, depth = 0, hasChildren = false) {
    const active = app.state.activeFavoriteFolderId === id;
    const expanded = id === "" || app.state.expandedFavoriteFolders.has(id);
    const expander = hasChildren
        ? `<button class="folder-expander" type="button" data-toggle-folder="${escapeHtml(id)}" aria-label="Toggle folder">${expanded ? "▾" : "▸"}</button>`
        : '<span class="folder-expander" aria-hidden="true"></span>';
    return `
        <div class="folder-row" style="--folder-depth: ${depth};" data-drop-folder="${escapeHtml(id)}">
            ${expander}
            <button class="folder-button ${active ? "active" : ""}" type="button" data-favorite-folder="${escapeHtml(id)}">
                <span>${escapeHtml(label)}</span>
                <span class="folder-count">${formatNumber(count)}</span>
            </button>
        </div>
    `;
}

function renderFavoriteFolderNodes(parentId = "", depth = 0) {
    return getFolderChildren(parentId).map((folder) => {
        const children = getFolderChildren(folder.id);
        const expanded = app.state.expandedFavoriteFolders.has(folder.id);
        const childHtml = expanded ? renderFavoriteFolderNodes(folder.id, depth + 1) : "";
        return `
            ${renderFavoriteFolderButton(folder.id, folder.name, countItemsInFolder(folder.id), depth, children.length > 0)}
            ${childHtml}
        `;
    }).join("");
}

function renderFavoriteFolderTree() {
    const allCount = getFavoriteArticles(FAVORITES_ALL_FOLDER).length;
    const uncategorizedCount = getFavoriteArticles(FAVORITES_UNCATEGORIZED_FOLDER).length;
    dom.favoriteFolderTree.innerHTML = `
        ${renderFavoriteFolderButton(FAVORITES_ALL_FOLDER, "All", allCount, 0, false)}
        ${renderFavoriteFolderButton(FAVORITES_UNCATEGORIZED_FOLDER, "未分类", uncategorizedCount, 0, false)}
        ${renderFavoriteFolderNodes()}
    `;
}

function renderFavoriteArticleRow(article) {
    const articleKey = article._favoriteKey || rememberArticle(article);
    const folderPath = article._folderId ? getFolderPath(article._folderId) : "未分类";
    const doiUrl = buildDoiUrl(article.doi);
    return `
        <article class="favorite-row" draggable="true" data-drag-favorite="${escapeHtml(articleKey)}">
            <div>
                <p class="favorite-title">${escapeHtml(article.title || "Untitled")}</p>
                <p class="favorite-meta">${escapeHtml(article.authors || "Unknown")}</p>
                <p class="favorite-meta">${escapeHtml(article.year || "Unknown")} · ${escapeHtml(journalLabel(article.journal || ""))} · ${escapeHtml(folderPath)}</p>
                <div class="copy-actions">
                    ${doiUrl ? `<a class="detail-link" href="${doiUrl}" target="_blank" rel="noreferrer">DOI</a>` : ""}
                    <button class="copy-button" type="button" data-copy-bibtex="${escapeHtml(articleKey)}">BibTeX</button>
                    <button class="copy-button" type="button" data-copy-apa="${escapeHtml(articleKey)}">APA</button>
                    <button class="copy-button" type="button" data-copy-ai="${escapeHtml(articleKey)}">AI prompt</button>
                    <select class="folder-select" data-folder-select="${escapeHtml(articleKey)}" aria-label="Move favorite">
                        ${buildFavoriteFolderOptions(articleKey)}
                    </select>
                </div>
            </div>
            <div class="favorite-actions">
                <button class="star-button is-active" type="button" data-favorite-article="${escapeHtml(articleKey)}" aria-label="Remove favorite">★</button>
            </div>
        </article>
    `;
}

function renderFavoritesView() {
    renderFavoriteFolderTree();
    const folderId = app.state.activeFavoriteFolderId || FAVORITES_ALL_FOLDER;
    const articles = getFavoriteArticles(folderId);
    dom.favoritesSummary.textContent = `${formatNumber(articles.length)} articles · ${getFavoriteFolderLabel(folderId)}`;
    dom.renameFavoriteFolder.disabled = folderId === FAVORITES_ALL_FOLDER || folderId === FAVORITES_UNCATEGORIZED_FOLDER;
    dom.deleteFavoriteFolder.disabled = dom.renameFavoriteFolder.disabled;
    dom.exportFavoritesBibtex.disabled = articles.length === 0;
    dom.exportFavoritesCsv.disabled = articles.length === 0;
    dom.exportFavoritesJson.disabled = articles.length === 0;
    dom.exportMenu.hidden = !app.state.exportOpen;
    dom.exportToggle.setAttribute("aria-expanded", app.state.exportOpen ? "true" : "false");
    dom.favoritesList.innerHTML = articles.length
        ? articles.map(renderFavoriteArticleRow).join("")
        : '<div class="empty-state">No articles found</div>';
}

async function renderAuthorsView() {
    dom.authorMinInput.value = app.state.authorMin;
    try {
        await ensureAuthorIndex();
    } catch (error) {
        console.error(error);
        dom.authorsSummary.textContent = "0 authors";
        dom.authorList.innerHTML = '<div class="empty-state">No articles found</div>';
        return;
    }
    const authors = (app.authorIndex?.authors || [])
        .filter((author) => Number(author.count || 0) >= app.state.authorMin)
        .sort((a, b) =>
            Number(b.count || 0) - Number(a.count || 0) ||
            String(a.name || "").localeCompare(String(b.name || ""))
        );
    dom.authorsSummary.textContent = `${formatNumber(authors.length)} authors`;
    dom.authorList.innerHTML = authors.map((author) => {
        const mainJournal = author.journals?.[0]?.journal || "";
        return `
            <button class="author-row" type="button" data-author-name="${escapeHtml(author.name || "")}">
                <span>
                    <span class="author-name">${escapeHtml(author.name || "Unknown")}</span>
                    <span class="author-meta">${formatNumber(author.count)} · ${escapeHtml(journalLabel(mainJournal))}</span>
                </span>
                <span class="author-count">${formatNumber(author.count)}</span>
            </button>
        `;
    }).join("") || '<div class="empty-state">No articles found</div>';
}

async function renderAll() {
    renderViews();
    renderTopbar();
    renderJournalPills();
    if (app.state.view === "main") {
        await renderMainView();
    } else if (app.state.view === "favorites") {
        renderLoading();
        renderFavoritesView();
    } else if (app.state.view === "authors") {
        renderLoading();
        await renderAuthorsView();
    }
}

function resetResultWindow() {
    app.state.visibleCount = PAGE_SIZE;
    app.state.expandedKey = "";
}

async function setView(view) {
    app.state.view = view;
    app.state.sortOpen = false;
    app.state.exportOpen = false;
    await renderAll();
}

async function updateSearchFromInput() {
    app.state.q = dom.searchInput.value;
    resetResultWindow();
    await renderAll();
}

function queueSearchRender() {
    window.clearTimeout(searchDebounceId);
    searchDebounceId = window.setTimeout(updateSearchFromInput, 300);
}

async function copyArticleByKey(articleKey, kind) {
    const article = getArticleByKey(articleKey);
    if (!article) {
        return;
    }
    if (kind === "bibtex") {
        await copyText(formatBibtex(article));
    } else if (kind === "apa") {
        await copyText(formatApa(article));
    } else if (kind === "ai") {
        await copyText(buildAiPrompt(article));
    }
}

function exportCurrentFavorites(kind) {
    const folderId = app.state.activeFavoriteFolderId;
    if (kind === "bibtex") {
        const text = buildFavoritesBibtex(folderId);
        if (text) downloadTextFile(buildExportFilename("bib"), text, "application/x-bibtex;charset=utf-8");
    } else if (kind === "csv") {
        const text = buildFavoritesCsv(folderId);
        if (text) downloadTextFile(buildExportFilename("csv"), text, "text/csv;charset=utf-8");
    } else if (kind === "json") {
        const text = buildFavoritesJson(folderId);
        if (text) downloadTextFile(buildExportFilename("json"), text, "application/json;charset=utf-8");
    }
}

function bindEvents() {
    dom.searchForm.addEventListener("submit", (event) => {
        event.preventDefault();
    });

    dom.searchInput.addEventListener("input", queueSearchRender);

    dom.searchModeSelect.addEventListener("change", async () => {
        app.state.searchMode = dom.searchModeSelect.value;
        resetResultWindow();
        await renderAll();
    });

    dom.themeToggle.addEventListener("click", async () => {
        applyTheme(app.theme === "dark" ? "light" : "dark");
        writeStorage(THEME_STORAGE_KEY, app.theme);
        await renderAll();
    });

    dom.favoritesToggle.addEventListener("click", async () => {
        await setView(app.state.view === "favorites" ? "main" : "favorites");
    });

    dom.authorsLink.addEventListener("click", async () => {
        await setView("authors");
    });

    dom.favoritesBack.addEventListener("click", async () => {
        await setView("main");
    });

    dom.authorsBack.addEventListener("click", async () => {
        await setView("main");
    });

    dom.journalPills.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-journal-pill]");
        if (!button) {
            return;
        }
        const journal = button.dataset.journalPill;
        if (journal === "__all__") {
            app.state.journals = [];
        } else {
            const next = new Set(app.state.journals);
            if (next.has(journal)) {
                next.delete(journal);
            } else {
                next.add(journal);
            }
            app.state.journals = [...next];
        }
        resetResultWindow();
        await renderAll();
    });

    dom.filtersToggle.addEventListener("click", async () => {
        app.state.filtersOpen = !app.state.filtersOpen;
        await renderAll();
    });

    dom.selectedJournalList.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-remove-journal]");
        if (!button) {
            return;
        }
        app.state.journals = app.state.journals.filter((journal) => journal !== button.dataset.removeJournal);
        resetResultWindow();
        await renderAll();
    });

    dom.yearFrom.addEventListener("change", async () => {
        app.state.yearFrom = dom.yearFrom.value;
        resetResultWindow();
        await renderAll();
    });

    dom.yearTo.addEventListener("change", async () => {
        app.state.yearTo = dom.yearTo.value;
        resetResultWindow();
        await renderAll();
    });

    dom.hasAbstractOnly.addEventListener("change", async () => {
        app.state.hasAbstractOnly = dom.hasAbstractOnly.checked;
        resetResultWindow();
        await renderAll();
    });

    dom.sortToggle.addEventListener("click", async () => {
        app.state.sortOpen = !app.state.sortOpen;
        await renderAll();
    });

    dom.sortMenu.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-sort-value]");
        if (!button) {
            return;
        }
        app.state.sort = button.dataset.sortValue;
        app.state.sortOpen = false;
        resetResultWindow();
        await renderAll();
    });

    dom.resultList.addEventListener("click", async (event) => {
        const favoriteButton = event.target.closest("[data-favorite-article]");
        if (favoriteButton) {
            event.stopPropagation();
            toggleFavoriteByKey(favoriteButton.dataset.favoriteArticle);
            await renderAll();
            return;
        }

        const toggleButton = event.target.closest("[data-toggle-article]");
        if (toggleButton) {
            const key = toggleButton.dataset.toggleArticle;
            app.state.expandedKey = app.state.expandedKey === key ? "" : key;
            await renderAll();
            return;
        }

        const copyBibtex = event.target.closest("[data-copy-bibtex]");
        const copyApa = event.target.closest("[data-copy-apa]");
        const copyAi = event.target.closest("[data-copy-ai]");
        if (copyBibtex) await copyArticleByKey(copyBibtex.dataset.copyBibtex, "bibtex");
        if (copyApa) await copyArticleByKey(copyApa.dataset.copyApa, "apa");
        if (copyAi) await copyArticleByKey(copyAi.dataset.copyAi, "ai");
    });

    dom.resultList.addEventListener("change", async (event) => {
        const select = event.target.closest("[data-folder-select]");
        if (!select || !select.value) {
            return;
        }
        moveFavoriteToFolder(select.dataset.folderSelect, select.value);
        await renderAll();
    });

    dom.loadMore.addEventListener("click", async () => {
        app.state.visibleCount += PAGE_SIZE;
        await renderAll();
    });

    dom.exportToggle.addEventListener("click", async () => {
        app.state.exportOpen = !app.state.exportOpen;
        await renderAll();
    });

    dom.exportFavoritesBibtex.addEventListener("click", () => exportCurrentFavorites("bibtex"));
    dom.exportFavoritesCsv.addEventListener("click", () => exportCurrentFavorites("csv"));
    dom.exportFavoritesJson.addEventListener("click", () => exportCurrentFavorites("json"));

    dom.createFavoriteFolder.addEventListener("click", async () => {
        const folder = ensureFavoriteFolderPath(dom.favoriteFolderPath.value);
        if (folder) {
            app.state.activeFavoriteFolderId = folder.id;
            app.state.expandedFavoriteFolders.add(folder.parentId || "");
            dom.favoriteFolderPath.value = "";
        }
        await renderAll();
    });

    dom.renameFavoriteFolder.addEventListener("click", async () => {
        const folder = getFolderById(app.state.activeFavoriteFolderId);
        if (!folder) {
            return;
        }
        const nextName = window.prompt("Rename", folder.name);
        if (nextName !== null) {
            renameFavoriteFolder(folder.id, nextName);
            await renderAll();
        }
    });

    dom.deleteFavoriteFolder.addEventListener("click", async () => {
        if (deleteFavoriteFolder(app.state.activeFavoriteFolderId)) {
            await renderAll();
        }
    });

    dom.favoriteFolderTree.addEventListener("click", async (event) => {
        const toggle = event.target.closest("[data-toggle-folder]");
        if (toggle) {
            const id = toggle.dataset.toggleFolder;
            if (app.state.expandedFavoriteFolders.has(id)) {
                app.state.expandedFavoriteFolders.delete(id);
            } else {
                app.state.expandedFavoriteFolders.add(id);
            }
            await renderAll();
            return;
        }
        const folderButton = event.target.closest("[data-favorite-folder]");
        if (!folderButton) {
            return;
        }
        app.state.activeFavoriteFolderId = folderButton.dataset.favoriteFolder;
        await renderAll();
    });

    dom.favoriteFolderTree.addEventListener("dragover", (event) => {
        if (event.target.closest("[data-drop-folder]")) {
            event.preventDefault();
        }
    });

    dom.favoriteFolderTree.addEventListener("drop", async (event) => {
        const target = event.target.closest("[data-drop-folder]");
        if (!target || !app.state.draggingFavoriteKey) {
            return;
        }
        event.preventDefault();
        const folderId = target.dataset.dropFolder;
        moveFavoriteToFolder(app.state.draggingFavoriteKey, folderId);
        app.state.draggingFavoriteKey = "";
        await renderAll();
    });

    dom.favoritesList.addEventListener("dragstart", (event) => {
        const row = event.target.closest("[data-drag-favorite]");
        if (!row) {
            return;
        }
        app.state.draggingFavoriteKey = row.dataset.dragFavorite;
        event.dataTransfer.effectAllowed = "move";
    });

    dom.favoritesList.addEventListener("click", async (event) => {
        const favoriteButton = event.target.closest("[data-favorite-article]");
        if (favoriteButton) {
            toggleFavoriteByKey(favoriteButton.dataset.favoriteArticle);
            await renderAll();
            return;
        }

        const copyBibtex = event.target.closest("[data-copy-bibtex]");
        const copyApa = event.target.closest("[data-copy-apa]");
        const copyAi = event.target.closest("[data-copy-ai]");
        if (copyBibtex) await copyArticleByKey(copyBibtex.dataset.copyBibtex, "bibtex");
        if (copyApa) await copyArticleByKey(copyApa.dataset.copyApa, "apa");
        if (copyAi) await copyArticleByKey(copyAi.dataset.copyAi, "ai");
    });

    dom.favoritesList.addEventListener("change", async (event) => {
        const select = event.target.closest("[data-folder-select]");
        if (!select || !select.value) {
            return;
        }
        moveFavoriteToFolder(select.dataset.folderSelect, select.value);
        await renderAll();
    });

    dom.authorMinInput.addEventListener("change", async () => {
        app.state.authorMin = Math.max(1, Number(dom.authorMinInput.value || 10));
        await renderAll();
    });

    dom.authorList.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-author-name]");
        if (!button) {
            return;
        }
        app.state.q = button.dataset.authorName;
        app.state.searchMode = "author";
        resetResultWindow();
        await setView("main");
        dom.searchInput.focus();
        dom.searchInput.setSelectionRange(dom.searchInput.value.length, dom.searchInput.value.length);
    });

    document.addEventListener("click", async (event) => {
        const insideSort = event.target.closest("#sort-toggle") || event.target.closest("#sort-menu");
        const insideExport = event.target.closest("#export-toggle") || event.target.closest("#export-menu");
        let needsRender = false;
        if (!insideSort && app.state.sortOpen) {
            app.state.sortOpen = false;
            needsRender = true;
        }
        if (!insideExport && app.state.exportOpen) {
            app.state.exportOpen = false;
            needsRender = true;
        }
        if (needsRender) {
            await renderAll();
        }
    });

    document.addEventListener("keydown", async (event) => {
        const activeTag = document.activeElement?.tagName || "";
        const editingElsewhere =
            document.activeElement &&
            document.activeElement !== dom.searchInput &&
            (activeTag === "INPUT" || activeTag === "TEXTAREA" || activeTag === "SELECT" || document.activeElement.isContentEditable);

        if (event.key === "/" && !editingElsewhere) {
            event.preventDefault();
            app.state.view = "main";
            await renderAll();
            dom.searchInput.focus();
            return;
        }

        if (event.key === "Escape") {
            if (app.state.sortOpen || app.state.exportOpen || app.state.filtersOpen || app.state.expandedKey) {
                app.state.sortOpen = false;
                app.state.exportOpen = false;
                app.state.filtersOpen = false;
                app.state.expandedKey = "";
                await renderAll();
            } else if (document.activeElement === dom.searchInput) {
                dom.searchInput.blur();
            }
        }
    });
}

async function init() {
    cacheDom();
    loadClientPreferences();
    bindEvents();
    app.state.expandedFavoriteFolders.add("");
    await renderAll();
    window.setTimeout(() => dom.searchInput.focus({ preventScroll: true }), 0);
    try {
        await initDataSources();
    } finally {
        await renderAll();
        window.setTimeout(() => dom.searchInput.focus({ preventScroll: true }), 0);
    }
}

window.addEventListener("DOMContentLoaded", init);
