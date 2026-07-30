import os
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
DOCS_DIR = ROOT / "docs"
GUIDES_DIR = DOCS_DIR / "guides"
HANDOFF_DIR = DOCS_DIR / "handoff"
PLANS_DIR = DOCS_DIR / "plans"
REPORTS_DIR = DOCS_DIR / "reports"
CACHE_DIR = ROOT / ".cache"

PROJECT_URL = "https://github.com/huwenbo-lab/publication"
CONTACT_EMAIL = os.environ.get("LITDB_CONTACT_EMAIL", "").strip()
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()
API_USER_AGENT = (
    f"SociologyLitDB/1.0 (mailto:{CONTACT_EMAIL})"
    if CONTACT_EMAIL
    else f"SociologyLitDB/1.0 (+{PROJECT_URL})"
)


def with_contact(url):
    """Append an optional API contact email without hard-coding personal data."""
    if not CONTACT_EMAIL:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}mailto={quote_plus(CONTACT_EMAIL)}"


def with_openalex_auth(url):
    """Add the API key now required for non-demo OpenAlex requests."""
    if not OPENALEX_API_KEY:
        raise RuntimeError("请先设置环境变量 OPENALEX_API_KEY")
    url = with_contact(url)
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}api_key={quote_plus(OPENALEX_API_KEY)}"


REPORTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
