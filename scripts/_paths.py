from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
DOCS_DIR = ROOT / "docs"
GUIDES_DIR = DOCS_DIR / "guides"
HANDOFF_DIR = DOCS_DIR / "handoff"
PLANS_DIR = DOCS_DIR / "plans"
REPORTS_DIR = DOCS_DIR / "reports"
CACHE_DIR = ROOT / ".cache"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
