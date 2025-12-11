"""
Configuration and global state management for the backend.
Centralizes all environment variables, global data structures, and feature flags.
"""
import os
import time
from typing import Any, Dict, List

# =========================
# Environment Configuration
# =========================
DEFAULT_SPREADSHEET_ID = os.environ.get(
    "SPREADSHEET_ID",
    "1-ypUyKglUjblgy1Gy0gITcdHF4YLdJnaCNKM_6_fCrI"
)
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
USE_DEEP = os.environ.get("DEEP_INDEX", "1").lower() in ("1", "true", "yes")

# =========================
# Feature Flags
# =========================
try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except Exception:
    HAS_GSPREAD = False
    Credentials = None

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload
    HAS_GOOGLE_API = True
except Exception:
    HAS_GOOGLE_API = False

try:
    from backend import db_mysql
    HAS_MYSQL = True
except Exception:
    try:
        import db_mysql
        HAS_MYSQL = True
    except Exception as e:
        HAS_MYSQL = False
        db_mysql = None
        print(f"[WARNING] MySQL module not available: {e}")

# =========================
# Global Data Structures
# =========================
DATABASE_ROWS: List[Dict[str, Any]] = []
SHEETS: List[str] = []
LINK_POOL: Dict[str, List[Dict[str, Any]]] = {}  # url -> list of locations
LINK_POOL_LIST: List[Dict[str, Any]] = []  # flat list of all links
LINK_POOL_MAP: Dict[str, List[Dict[str, Any]]] = {}

# Caches
GSPREAD_SKIP_IDS: set[str] = set()
URL_ACCESS_CACHE: dict[str, str] = {}  # url -> "ok"|"private"|"unsupported"
DRIVE_META_CACHE: dict[str, dict] = {}  # fileId -> {id, name, mimeType}

# =========================
# Debug & Statistics
# =========================
DEBUG_LOG: List[str] = []
DEBUG_LOG_MAX = 5000

STATS: Dict[str, Any] = {
    "built_at": None,
    "total_links": 0,
    "per_sheet": []
}

# =========================
# Logging Helper
# =========================
def debug_log(msg: str):
    """Add a timestamped message to DEBUG_LOG."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    DEBUG_LOG.append(line)
    if len(DEBUG_LOG) > DEBUG_LOG_MAX:
        del DEBUG_LOG[: len(DEBUG_LOG) - DEBUG_LOG_MAX]
