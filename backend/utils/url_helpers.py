"""
URL parsing and validation utilities.
Handles Google Sheets/Docs URLs, file ID extraction, and export URL generation.
"""
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

# =========================
# Regex Patterns
# =========================
URL_RE = re.compile(r"https?://[^\s)>\]\"']+", re.IGNORECASE)
DOCS_ID_RE = re.compile(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)")
SHEETS_ID_RE = re.compile(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)")
GID_RE = re.compile(r"[#?&]gid=(\d+)")

_GSHEETS_ID_PATTERNS = [
    r"/spreadsheets/d/([a-zA-Z0-9-_]+)",
    r"/file/d/([a-zA-Z0-9-_]+)",
    r"[?&]id=([a-zA-Z0-9-_]+)",
    r"/export/.*/\*/([a-zA-Z0-9-_]+)",
]


# =========================
# File ID Extraction
# =========================
def extract_gsheets_file_id(url: str) -> Optional[str]:
    """Extract Google Sheets/Drive file ID from URL."""
    for pat in _GSHEETS_ID_PATTERNS:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def extract_gid_from_url(url: str) -> Optional[str]:
    """
    Extract GID (sheet ID) from Google Sheets URL.
    Checks both query params and fragment.
    """
    try:
        p = urlparse(url)
        # Check query params
        qgid = (parse_qs(p.query or "").get("gid") or [None])[0]
        if qgid:
            return qgid
        # Check fragment
        if p.fragment:
            m = re.search(r"gid=(\d+)", p.fragment)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


# =========================
# URL Type Detection
# =========================
def is_google_sheets_url(url: str) -> bool:
    """Check if URL is a Google Sheets URL."""
    try:
        p = urlparse(url)
        return (
            ("docs.google.com" in p.netloc and "/spreadsheets/" in p.path) or
            ("googleusercontent.com" in p.netloc and "/export/" in p.path)
        )
    except Exception:
        return False


def is_google_docs_url(url: str) -> bool:
    """Check if URL is a Google Docs URL."""
    try:
        p = urlparse(url)
        return "docs.google.com" in p.netloc and "/document/" in p.path
    except Exception:
        return False


def classify_google_url(url: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Classify Google URL and extract metadata.
    
    Returns:
        (kind, file_id, gid) where kind in {'docs', 'sheets', 'unknown'}
    """
    m = DOCS_ID_RE.search(url)
    if m:
        return ("docs", m.group(1), None)
    
    m = SHEETS_ID_RE.search(url)
    if m:
        gid = None
        g = GID_RE.search(url)
        if g:
            gid = g.group(1)
        return ("sheets", m.group(1), gid)
    
    return ("unknown", None, None)


# =========================
# Export URL Generation
# =========================
def build_gsheets_csv_export(url: str) -> Tuple[str, str]:
    """
    Build CSV export URL for Google Sheets.
    
    Returns:
        (export_url, sheet_hint) - export URL and sheet identifier hint
    """
    p = urlparse(url)
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", p.path)
    file_id = m.group(1) if m else None

    q = parse_qs(p.query or "")
    gid_q = (q.get("gid") or [""])[0]

    # Priority: fragment gid over query gid
    gid_frag = ""
    if p.fragment:
        mf = re.search(r"gid=(\d+)", p.fragment)
        gid_frag = mf.group(1) if mf else ""

    gid = gid_frag or gid_q or "0"

    if not file_id:
        raise ValueError("Cannot parse Google Sheets file ID")

    export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&gid={gid}"
    return export_url, f"gid {gid}"


def normalize_to_gsheets_csv_export(url: str, gid_hint: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Normalize any Google Sheets URL variant to standard CSV export URL.
    
    Returns:
        (export_url, gid_used)
    """
    file_id = extract_gsheets_file_id(url)
    if not file_id:
        return url, gid_hint

    gid = gid_hint or extract_gid_from_url(url) or "0"
    export_url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv&gid={gid}"
    return export_url, gid


def export_candidates(url: str) -> List[str]:
    """
    Get possible export endpoints for Google URLs.
    
    - Sheets: CSV export (with gid if present)
    - Docs: TXT export
    - Others: return original URL
    """
    kind, file_id, maybe_gid = classify_google_url(url)
    
    if kind == "docs" and file_id:
        return [f"https://docs.google.com/document/d/{file_id}/export?format=txt"]
    
    if kind == "sheets" and file_id:
        base = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"
        return [f"{base}&gid={maybe_gid}"] if maybe_gid else [base]
    
    return [url]


# =========================
# URL Cleaning
# =========================
def clean_urls(urls: List[any]) -> List[str]:
    """
    Clean and deduplicate URLs.
    
    - Remove non-string items
    - Strip whitespace and trailing punctuation
    - Filter to http/https only
    - Deduplicate by base URL (without query/fragment)
    """
    out, seen = [], set()
    for u in urls:
        if not isinstance(u, str):
            continue
        u = u.strip().strip('")]}').strip()
        if not u.startswith("http"):
            continue
        base = u.split("#")[0].split("?")[0]
        if base in seen:
            continue
        seen.add(base)
        out.append(u)
    return out
