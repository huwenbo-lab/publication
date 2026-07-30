#!/usr/bin/env python3
"""Static and runtime checks for the publication frontend shell."""

import json
from pathlib import Path
import subprocess
from urllib.parse import urlparse

from build_article_api import build_site_url, doi_to_relative_path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "style.css").read_text(encoding="utf-8")
JS = (ROOT / "app.js").read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def check_article_api_urls():
    """Compare the browser URL builder with the Python API generator."""
    dois = [
        "10.1016/s1040-2608(00)80013-1",
        "10.1000/example:section|part*one",
        "10.1000/example%value",
        "10.1177/0003122412442882",
    ]
    node_script = f"""
const fs = require("fs");
const vm = require("vm");
const source = fs.readFileSync("app.js", "utf8");
const sandbox = {{
    URL,
    window: {{
        location: {{ href: "https://huwenbo-lab.github.io/publication/" }},
        addEventListener: () => {{}},
        setTimeout: () => {{}},
    }},
}};
vm.createContext(sandbox);
vm.runInContext(source, sandbox, {{ filename: "app.js" }});
const dois = {json.dumps(dois)};
const output = dois.map((doi) => ({{
    path: sandbox.buildArticleApiPath(doi),
    url: sandbox.buildArticleApiUrl(doi),
}}));
process.stdout.write(JSON.stringify(output));
"""
    result = subprocess.run(
        ["node", "-e", node_script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    require(
        result.returncode == 0,
        f"app.js API URL runtime check failed: {result.stderr.strip()}",
    )
    actual = json.loads(result.stdout)
    for doi, browser_result in zip(dois, actual):
        physical_path = Path("api") / doi_to_relative_path(doi)
        expected_url = build_site_url(physical_path)
        expected_path = urlparse(expected_url).path.removeprefix("/publication/")
        require(
            browser_result["path"] == expected_path,
            f"app.js API path differs from Python generator for DOI {doi}",
        )
        require(
            browser_result["url"] == expected_url,
            f"app.js API URL differs from Python generator for DOI {doi}",
        )


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
        "function encodeArticleApiPathSegment",
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

    check_article_api_urls()


if __name__ == "__main__":
    main()
