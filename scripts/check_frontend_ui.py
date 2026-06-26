#!/usr/bin/env python3
"""Static checks for the publication frontend shell."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "style.css").read_text(encoding="utf-8")
JS = (ROOT / "app.js").read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    removed_index_tokens = [
        'id="tabbar"',
        'class="hero',
        'class="discipline-strip',
        'id="dashboard-panel"',
        'id="article-modal"',
        'id="favorites-modal"',
        "热门关键词",
        "期刊分布",
        "常用方向",
        "数据库概况",
        "默认每页",
        "按 /",
    ]
    for token in removed_index_tokens:
        require(token not in INDEX, f"index.html still contains removed UI token: {token}")

    required_index_tokens = [
        'id="app-topbar"',
        'id="journal-pills"',
        'id="search-input"',
        'id="search-mode-select"',
        'id="filters-toggle"',
        'id="filters-panel"',
        'id="sort-menu"',
        'id="result-list"',
        'id="favorites-view"',
        'id="authors-view"',
    ]
    for token in required_index_tokens:
        require(token in INDEX, f"index.html is missing required UI token: {token}")

    required_css_tokens = [
        "--content-width: 960px",
        "body[data-theme=\"dark\"]",
        ".topbar",
        "position: sticky",
        ".journal-strip",
        "grid-template-columns: repeat(10",
        ".favorites-workspace",
        "overflow-y: auto",
    ]
    for token in required_css_tokens:
        require(token in CSS, f"style.css is missing required token: {token}")

    removed_css_tokens = [
        "overflow-x: auto",
        ".journal-pills::-webkit-scrollbar",
    ]
    for token in removed_css_tokens:
        require(token not in CSS, f"style.css still contains horizontal journal scroll token: {token}")

    removed_js_tokens = [
        "renderDashboard",
        "renderDisciplinePresets",
        "renderTabs",
        "setModalOpen",
        "setFavoritesModalOpen",
    ]
    for token in removed_js_tokens:
        require(token not in JS, f"app.js still contains removed renderer: {token}")

    required_js_tokens = [
        "const PAGE_SIZE = 50",
        "literature.db",
        "data.json",
        "localStorage",
        "function initSqliteEngine",
        "function searchWithDb",
        "function renderJournalPills",
        "function renderArticleList",
        "function renderFavoritesView",
        "function renderAuthorsView",
        "No articles found",
        'event.key === "/"',
    ]
    for token in required_js_tokens:
        require(token in JS, f"app.js is missing required token: {token}")


if __name__ == "__main__":
    main()
