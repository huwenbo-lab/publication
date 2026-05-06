#!/usr/bin/env python3
"""Static checks for optional cloud favorites sync."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
CSS = (ROOT / "style.css").read_text(encoding="utf-8")
JS = (ROOT / "app.js").read_text(encoding="utf-8")
WORKER = ROOT / "workers" / "favorites-sync" / "src" / "index.js"
WRANGLER = ROOT / "workers" / "favorites-sync" / "wrangler.jsonc"
README = ROOT / "workers" / "favorites-sync" / "README.md"
WORKER_CHECK = ROOT / "scripts" / "check_favorites_sync_worker.mjs"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def require_tokens(text, tokens, filename):
    for token in tokens:
        require(token in text, f"{filename} is missing required token: {token}")


def main():
    require_tokens(
        INDEX,
        [
            'id="sync-endpoint"',
            'id="sync-key"',
            'id="sync-save"',
            'id="sync-pull"',
            'id="sync-push"',
            'id="sync-status"',
        ],
        "index.html",
    )

    require_tokens(
        CSS,
        [
            ".sync-panel",
            ".sync-grid",
            ".sync-actions",
            ".sync-status",
        ],
        "style.css",
    )

    require_tokens(
        JS,
        [
            'const FAVORITES_SYNC_STORAGE_KEY = "publication:favorites-sync:v1"',
            "function loadSyncSettings",
            "function saveSyncSettings",
            "function buildFavoriteLibraryPayload",
            "function mergeFavoriteLibraries",
            "async function pullFavoritesFromCloud",
            "async function pushFavoritesToCloud",
            "function renderSyncPanel",
        ],
        "app.js",
    )

    for path in [WORKER, WRANGLER, README, WORKER_CHECK]:
        require(path.exists(), f"{path.relative_to(ROOT)} is missing")

    worker_source = WORKER.read_text(encoding="utf-8")
    require_tokens(
        worker_source,
        [
            "Authorization",
            "constantTimeEqual",
            "FAVORITES_KV",
            "SYNC_KEY",
            "OPTIONS",
            "GET",
            "PUT",
            "favorites:default",
        ],
        "workers/favorites-sync/src/index.js",
    )

    wrangler_source = WRANGLER.read_text(encoding="utf-8")
    require_tokens(
        wrangler_source,
        [
            '"compatibility_date"',
            '"observability"',
            '"kv_namespaces"',
            '"binding": "FAVORITES_KV"',
            '"vars"',
        ],
        "workers/favorites-sync/wrangler.jsonc",
    )

    readme_source = README.read_text(encoding="utf-8")
    require_tokens(
        readme_source,
        [
            "wrangler kv namespace create",
            "wrangler secret put SYNC_KEY",
            "wrangler deploy",
        ],
        "workers/favorites-sync/README.md",
    )


if __name__ == "__main__":
    main()
