"""
Refactored backend.py - uses modular utilities
"""
# Standard library
import io
import csv
import json
import time
import re
from typing import Any, Dict, List, Optional, Tuple

# FastAPI
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

# Third-party
from rapidfuzz import fuzz
import httpx
from bs4 import BeautifulSoup

# Local imports - configuration and utilities
from backend.config import (
    DEFAULT_SPREADSHEET_ID,
    USE_DEEP,
    HAS_GSPREAD,
    HAS_GOOGLE_API,
    HAS_MYSQL,
    DATABASE_ROWS,
    SHEETS,
    LINK_POOL,
    LINK_POOL_LIST,
    LINK_POOL_MAP,
    GSPREAD_SKIP_IDS,
    URL_ACCESS_CACHE,
    STATS,
    DEBUG_LOG,
    debug_log as _dlog,
    db_mysql
)

from backend.utils.text_processing import (
    fix_vietnamese_text,
    fold_vietnamese,
    normalize_query,
    decode_http_response
)

from backend.utils.url_helpers import (
    extract_gsheets_file_id,
    extract_gid_from_url,
    is_google_sheets_url,
    is_google_docs_url,
    classify_google_url,
    build_gsheets_csv_export,
    normalize_to_gsheets_csv_export,
    export_candidates,
    clean_urls,
    URL_RE,
    DOCS_ID_RE,
    SHEETS_ID_RE,
    GID_RE
)

from backend.utils.csv_helpers import (
    read_csv_text,
    read_csv_bytes,
    csv_to_text,
    safe_fetch_csv_text,
    parse_plaintext_as_table,
    xlsx_bytes_to_csvtext,
    rows_from_xlsx_bytes
)

from backend.utils.google_api import (
    get_gspread_client,
    get_sheets_service,
    get_drive_service,
    get_drive_file_meta,
    download_drive_file,
    get_sheet_values_by_gid,
    get_sheet_values_as_csv,
    deep_scan_all_sheets
)

# =========================
# FastAPI App
# =========================
app = FastAPI(title="Link-aware Search Backend", version="2.1.0 (refactored)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Utility Functions
# =========================
COL_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

def _a1_addr(row: int, col: int) -> str:
    """Convert row/col to A1 notation (e.g., 1,1 → A1)."""
    c = col
    label = ""
    while c:
        c, rem = divmod(c - 1, 26)
        label = COL_LETTERS[rem] + label
    return f"{label}{row}"


def extract_links_from_cell(val: Any, formula: Any) -> List[str]:
    """Extract URLs from cell value and formula (HYPERLINK)."""
    val_s = val if isinstance(val, str) else ("" if val is None else str(val))
    fm_s = formula if isinstance(formula, str) else ("" if formula is None else str(formula))
    links: List[str] = []
    
    if val_s:
        links += URL_RE.findall(val_s)
    
    if fm_s:
        m = re.search(r'HYPERLINK\s*\(\s*"([^"]+)"', fm_s, re.IGNORECASE)
        if m:
            u = m.group(1)
            if not u.startswith("http") and ("docs.google.com" in u or "drive.google.com" in u):
                u = "https://" + u
            links.append(u)
        links += URL_RE.findall(fm_s)
    
    return clean_urls(links)


def _mark_gspread_skip(file_id: str, reason: str):
    """Mark a spreadsheet ID to skip gspread attempts."""
    if not file_id:
        return
    if file_id not in GSPREAD_SKIP_IDS:
        GSPREAD_SKIP_IDS.add(file_id)
        _dlog(f"[fetch] skip gspread for {file_id} ({reason})")


def _mark_url_private(url: str, reason: str = "private"):
    """Mark a URL as private/inaccessible."""
    if URL_ACCESS_CACHE.get(url) != "private":
        URL_ACCESS_CACHE[url] = "private"
        _dlog(f"[fetch] mark private for {url} ({reason})")


# =========================
# HTTP Fetch Helper
# =========================
async def _http_get_text(url: str, timeout: float = 20.0) -> Optional[str]:
    """
    Fetch content via HTTP.
    - text/plain, text/csv: return text directly
    - HTML: strip tags and return text
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0"}
        ) as client:
            r = await client.get(url)
            if r.status_code != 200:
                try:
                    _dlog(f"[http] {r.status_code} on {url}")
                except Exception:
                    pass
                return None
            
            ct = (r.headers.get("content-type") or "").lower()
            if "text/plain" in ct or url.lower().endswith(".txt"):
                return r.text
            if "text/csv" in ct or url.lower().endswith(".csv"):
                return r.text
            
            # HTML - strip tags
            html = r.text
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.extract()
            return soup.get_text("\n")
    except Exception as e:
        try:
            _dlog(f"[http] error {e} on {url}")
        except Exception:
            pass
        return None


# =========================
# Content Fetching
# =========================
async def fetch_text_from_url(url: str) -> Optional[str]:
    """
    Main content fetching function.
    Handles Google Sheets, Docs, Excel, and general URLs.
    """
    kind, file_id, maybe_gid = classify_google_url(url)

    # Check if already marked private
    if URL_ACCESS_CACHE.get(url) == "private":
        return None

    # Get metadata via Drive API
    meta = get_drive_file_meta(file_id) if file_id else None
    if meta and meta.get("id") and file_id and meta["id"] != file_id:
        file_id = meta["id"]  # Resolved shortcut target
    mime = (meta or {}).get("mimeType", "")

    # === Google Sheets ===
    if mime == "application/vnd.google-apps.spreadsheet":
        # Try gspread first
        if HAS_GSPREAD and (file_id not in GSPREAD_SKIP_IDS):
            client = get_gspread_client()
            if client:
                try:
                    ss = client.open_by_key(file_id)
                    if maybe_gid:
                        ws = ss.get_worksheet_by_id(int(maybe_gid)) or next(
                            (w for w in ss.worksheets()
                             if str(getattr(w, "_properties", {}).get("sheetId")) == str(maybe_gid)),
                            None
                        )
                    else:
                        ws = ss.sheet1
                    if ws:
                        values = ws.get_all_values()
                        return fix_vietnamese_text(csv_to_text(values))
                except Exception as e:
                    if "not supported for this document" in str(e).lower():
                        _mark_gspread_skip(file_id, "unsupported-or-noaccess")
                    else:
                        _dlog(f"[fetch] gspread sheets failed for {file_id}: {str(e)[:160]}")
        
        # Try Sheets API
        csv_text = get_sheet_values_as_csv(file_id, maybe_gid)
        if csv_text:
            return fix_vietnamese_text(csv_text)
        
        _mark_url_private(url, "sheets_api_no_access")
        return None

    # === Google Docs ===
    if mime == "application/vnd.google-apps.document":
        svc = get_drive_service()
        if svc:
            try:
                data = svc.files().export(fileId=file_id, mimeType="text/plain").execute()
                text = data.decode("utf-8", "ignore") if isinstance(data, bytes) else str(data)
                return fix_vietnamese_text(text)
            except Exception as e:
                _dlog(f"[drive] export txt failed {file_id}: {e}")
        _mark_url_private(url, "drive_export_no_access")
        return None

    # === Unsupported Google types ===
    if mime in (
        "application/vnd.google-apps.presentation",
        "application/vnd.google-apps.drawing",
        "application/vnd.google-apps.folder",
        "application/vnd.google-apps.form",
    ):
        _mark_url_private(url, "unsupported_mime")
        return None

    # === Excel .xlsx ===
    if mime in ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",):
        data = download_drive_file(file_id)
        if data:
            text = xlsx_bytes_to_csvtext(data)
            if text:
                return fix_vietnamese_text(text)
        _mark_url_private(url, "excel_download_or_parse_failed")
        return None

    # === Public export candidates ===
    for cand in export_candidates(url):
        text = await _http_get_text(cand)
        if text:
            return fix_vietnamese_text(text)

    # === Plain HTTP ===
    if kind == "unknown":
        text = await _http_get_text(url)
        if text:
            return fix_vietnamese_text(text)

    _mark_url_private(url, "final_no_access_or_unknown_mime")
    return None


async def preview_tables_from_url(url: str, max_rows: int = 5) -> Dict[str, Any]:
    """
    Preview table content from URL.
    Supports: Google Sheets, Excel (.xlsx/.xls), CSV
    """
    try:
        kind, file_id, maybe_gid = classify_google_url(url)
    except Exception:
        kind, file_id, maybe_gid = None, None, None

    meta = get_drive_file_meta(file_id) if file_id else None
    mime = (meta or {}).get("mimeType", "")

    # === Google Sheets via Drive API ===
    if mime == "application/vnd.google-apps.spreadsheet":
        try:
            rows_map = get_sheet_values_by_gid(file_id, maybe_gid, max_rows=max_rows) or {}
            fixed_tables = []
            for sheet_name, rows in rows_map.items():
                fixed_rows = [
                    [fix_vietnamese_text(c) if c is not None else "" for c in (row or [])]
                    for row in (rows or [])[:max_rows]
                ]
                fixed_tables.append({"name": sheet_name, "rows": fixed_rows})
            return {"kind": "sheets", "tables": fixed_tables}
        except Exception as e:
            _dlog(f"[sheets] preview via Drive API failed {file_id}: {e}")

    # === Google Sheets via public CSV ===
    try:
        if is_google_sheets_url(url):
            export_url, sheet_hint = build_gsheets_csv_export(url)
            import requests
            resp = requests.get(export_url, timeout=20)
            resp.raise_for_status()
            csv_text = decode_http_response(resp)
            rows = read_csv_text(csv_text)
            fixed_rows = [
                [fix_vietnamese_text(str(c)) if c is not None else "" for c in (row or [])]
                for row in (rows or [])[:max_rows]
            ]
            return {
                "kind": "sheets",
                "tables": [{"name": f"Google Sheets ({sheet_hint})", "rows": fixed_rows}]
            }
    except Exception as e:
        _dlog(f"[sheets] public CSV export failed: {e}")

    # === Excel .xlsx ===
    if mime in ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",):
        data = download_drive_file(file_id) if file_id else None
        tables = []
        if data:
            try:
                rows_map = rows_from_xlsx_bytes(data, max_rows=max_rows) or {}
                for sheet_name, rows in rows_map.items():
                    fixed_rows = [
                        [fix_vietnamese_text(c) if c is not None else "" for c in (row or [])]
                        for row in (rows or [])[:max_rows]
                    ]
                    tables.append({"name": sheet_name, "rows": fixed_rows})
            except Exception as e:
                _dlog(f"[excel-xlsx] preview failed: {e}")
        return {"kind": "excel", "tables": tables}

    # === CSV fallback ===
    try:
        for cand in export_candidates(url) or []:
            if not (cand.endswith(".csv") or "format=csv" in cand):
                continue
            txt = await _http_get_text(cand)
            if not txt:
                continue
            rows = read_csv_text(txt)
            fixed_rows = [
                [fix_vietnamese_text(str(c)) if c is not None else "" for c in (row or [])]
                for row in (rows or [])[:max_rows]
            ]
            return {"kind": "csv", "tables": [{"name": "Data", "rows": fixed_rows}]}
    except Exception as e:
        _dlog(f"[fallback-csv] preview failed: {e}")

    return {"kind": "unknown", "tables": []}


# =========================
# Peek Rows (Quick Preview)
# =========================
def _peek_url_rows(url: str, nrows: int = 10, gid: Optional[str] = None) -> List[List[str]]:
    """Quick peek at first N rows from a table URL."""
    try:
        if is_google_sheets_url(url):
            base = url.split("#")[0]
            if gid is not None and "gid=" not in base:
                sep = "&" if "?" in base else "?"
                url = f"{base}{sep}gid={gid}"
            export_url, _hint = build_gsheets_csv_export(url)
            import requests
            resp = requests.get(export_url, timeout=25)
            resp.raise_for_status()
            csv_text = decode_http_response(resp)
            rows = read_csv_text(csv_text)
            out = []
            for row in rows[:nrows]:
                out.append([fix_vietnamese_text("" if c is None else str(c)) for c in (row or [])])
            return out

        if url.endswith(".csv") or "format=csv" in url:
            import requests
            resp = requests.get(url, timeout=25)
            resp.raise_for_status()
            csv_text = decode_http_response(resp)
            rows = read_csv_text(csv_text)
            out = []
            for row in rows[:nrows]:
                out.append([fix_vietnamese_text("" if c is None else str(c)) for c in (row or [])])
            return out
    except Exception as e:
        _dlog(f"[peek] failed {url}: {e}")
    return []


# =========================
# Indexer
# =========================
def _iter_all_indexed_links(limit: Optional[int] = None) -> List[dict]:
    """Iterate all indexed links from LINK_POOL_LIST."""
    pool = LINK_POOL_LIST
    if isinstance(pool, list):
        return pool if (limit is None or limit >= len(pool)) else pool[:limit]
    
    # Fallback from LINK_POOL
    out = []
    for u, locs in (LINK_POOL or {}).items():
        for loc in (locs or []):
            out.append({
                "url": u,
                "sheet": loc.get("sheet", ""),
                "row": loc.get("row", ""),
                "col": loc.get("col", ""),
                "address": loc.get("address", ""),
                "gid": loc.get("sheet_gid") or loc.get("gid"),
                "sheet_name": loc.get("sheet_name", "")
            })
            if limit and len(out) >= limit:
                return out
    return out


def index_sources(verbose: bool = False, deep: bool = False) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Build index from DEFAULT_SPREADSHEET_ID.
    Returns (rows, sheets).
    """
    rows: List[Dict[str, Any]] = []
    sheets: List[str] = []

    # Reset link pools
    LINK_POOL.clear()
    LINK_POOL_LIST.clear()

    STATS["per_sheet"] = []
    start_ts = time.time()

    if not DEFAULT_SPREADSHEET_ID:
        _dlog("[index] No SPREADSHEET_ID set → empty index.")
        return rows, sheets
    
    if not HAS_GSPREAD:
        _dlog("[index] gspread not available → cannot open spreadsheet.")
        return rows, sheets

    client = get_gspread_client()
    if not client:
        _dlog("[index] cannot get gspread client")
        return rows, sheets

    try:
        ss = client.open_by_key(DEFAULT_SPREADSHEET_ID)
        worksheets = ss.worksheets()
        _dlog(f"[index] Opened spreadsheet with {len(worksheets)} sheets")
    except Exception as e:
        _dlog(f"[index] open spreadsheet failed: {e}")
        return rows, sheets

    # Build gid -> sheet_name mapping
    gid_to_name: Dict[str, str] = {}
    for ws in worksheets:
        props = getattr(ws, "_properties", {}) or {}
        gid = props.get("sheetId") or props.get("id")
        if gid is not None:
            gid_to_name[str(gid)] = ws.title

    # Deep scan if enabled
    deep_map: Dict[str, List[Dict[str, Any]]] = {}
    if deep:
        svc = get_sheets_service()
        if svc:
            _dlog("[deep] ENABLED: scanning rich-text links via Sheets API…")
            deep_map = deep_scan_all_sheets(DEFAULT_SPREADSHEET_ID) or {}
            total_occ = sum(len(v) for v in deep_map.values())
            _dlog(f"[deep] SUMMARY: got {total_occ} link occurrences from API")
        else:
            _dlog("[deep] DISABLED (service not available)")

    seen_flat_keys: set[str] = set()
    sheet_row_base: Dict[str, int] = {}

    for ws in worksheets:
        title = ws.title
        sheets.append(title)

        try:
            values = ws.get_all_values()
        except Exception as e:
            _dlog(f"[index] cannot read values: {title}: {e}")
            continue

        nrows = len(values)
        ncols = max((len(r) for r in values), default=0)
        
        try:
            if nrows > 0 and ncols > 0:
                rng = f"A1:{_a1_addr(nrows, ncols)}"
                raw_formulas = ws.get(rng, value_render_option="FORMULA")
                formulas = [[cell if isinstance(cell, str) else ("" if cell is None else str(cell))
                            for cell in row] for row in raw_formulas]
            else:
                formulas = []
        except Exception as e:
            _dlog(f"[index] cannot read formulas: {title}: {e}")
            formulas = []

        # Stats
        non_empty_cells = 0
        value_http_cells = 0
        formula_http_cells = 0
        cell_with_links = 0
        list_before = len(LINK_POOL_LIST)
        map_before = len(LINK_POOL)

        if verbose:
            _dlog(f"[index] Sheet '{title}' size ≈ {nrows}x{ncols}")

        # Pack rows for search
        base_row_index = len(rows)
        sheet_row_base[title] = base_row_index
        for r in range(nrows):
            row_vals = values[r]
            if any((cell or "").strip() for cell in row_vals):
                rows.append({
                    "sheet": title,
                    "row": r + 1,
                    "cols": row_vals,
                    "text": " ".join(x for x in row_vals if isinstance(x, str)),
                    "links": []
                })

        # Extract links from cells
        for r in range(nrows):
            for c in range(ncols):
                v = values[r][c] if c < len(values[r]) else ""
                if isinstance(v, str) and v.strip():
                    non_empty_cells += 1
                fm = formulas[r][c] if (r < len(formulas) and c < len(formulas[r])) else ""
                if ("http" in (v or "")) and isinstance(v, str):
                    value_http_cells += 1
                if ("http" in (fm or "")) or ("HYPERLINK" in (fm or "")):
                    formula_http_cells += 1

                link_list = extract_links_from_cell(v, fm)
                if not link_list:
                    continue
                cell_with_links += 1

                a1 = _a1_addr(r + 1, c + 1)

                for u in link_list:
                    _, __, maybe_gid = classify_google_url(u)
                    sheet_name = gid_to_name.get(str(maybe_gid), "") if maybe_gid else ""

                    # Add to map
                    loc = {"sheet": title, "row": r + 1, "col": c + 1, "address": a1}
                    if maybe_gid:
                        loc["sheet_gid"] = maybe_gid
                        if sheet_name:
                            loc["sheet_name"] = sheet_name
                    LINK_POOL.setdefault(u, []).append(loc)

                    # Add to flat list
                    k = f"{u}@@{a1}"
                    if k not in seen_flat_keys:
                        seen_flat_keys.add(k)
                        LINK_POOL_LIST.append({
                            "url": u,
                            "sheet": title,
                            "row": r + 1,
                            "col": c + 1,
                            "address": a1,
                            "gid": maybe_gid,
                            "sheet_name": sheet_name
                        })

                    # Add to row record
                    try:
                        rows[base_row_index + r]["links"].append(u)
                    except Exception:
                        pass

        # Process deep links
        deep_added_list = 0
        deep_added_map = 0
        deep_occurs = 0
        if deep and title in deep_map:
            occs = deep_map.get(title) or []
            deep_occurs = len(occs)
            for item in occs:
                u = item["url"]
                r1 = item["row"]
                c1 = item["col"]
                a1_deep = item["address"]
                _, __, maybe_gid2 = classify_google_url(u)
                sheet_name2 = gid_to_name.get(str(maybe_gid2), "") if maybe_gid2 else ""

                # Map
                exists = any(loc.get("sheet") == title and loc.get("address") == a1_deep
                           for loc in LINK_POOL.get(u, []))
                if not exists:
                    LINK_POOL.setdefault(u, []).append({
                        "sheet": title, "row": r1, "col": c1, "address": a1_deep,
                        **({"sheet_gid": maybe_gid2} if maybe_gid2 else {}),
                        **({"sheet_name": sheet_name2} if sheet_name2 else {})
                    })
                    deep_added_map += 1

                # List
                k2 = f"{u}@@{a1_deep}"
                if k2 not in seen_flat_keys:
                    seen_flat_keys.add(k2)
                    LINK_POOL_LIST.append({
                        "url": u, "sheet": title, "row": r1, "col": c1, "address": a1_deep,
                        "gid": maybe_gid2, "sheet_name": sheet_name2
                    })
                    deep_added_list += 1

                # Add to row
                try:
                    rows[sheet_row_base[title] + (r1 - 1)]["links"].append(u)
                except Exception:
                    pass

        sheet_stat = {
            "sheet": title,
            "size": f"{nrows}x{ncols}",
            "non_empty_cells": non_empty_cells,
            "value_http_cells": value_http_cells,
            "formula_http_cells": formula_http_cells,
            "cells_with_links_extracted": cell_with_links,
            "added_to_list_flat": len(LINK_POOL_LIST) - list_before,
            "added_url_keys_map": len(LINK_POOL) - map_before,
            "deep_occurrences_seen": deep_occurs,
            "deep_added_to_list_flat": deep_added_list,
            "deep_added_url_keys_map": deep_added_map,
            "flat_links_total_now": len(LINK_POOL_LIST),
            "url_keys_total_now": len(LINK_POOL),
        }
        STATS["per_sheet"].append(sheet_stat)

        _dlog(
            f"[index] '{title}': non-empty={non_empty_cells}, "
            f"value_has_http={value_http_cells}, formula_has_http/HYPERLINK={formula_http_cells}, "
            f"cells_extracted_links={cell_with_links}, "
            f"add_flat={sheet_stat['added_to_list_flat']}, add_map_keys={sheet_stat['added_url_keys_map']}, "
            f"deep_occurs={deep_occurs}, deep_add_flat={deep_added_list}, deep_add_map={deep_added_map}, "
            f"total_flat={len(LINK_POOL_LIST)}, total_map_keys={len(LINK_POOL)}"
        )

    STATS["built_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    STATS["total_links_flat"] = len(LINK_POOL_LIST)
    STATS["total_links_map_keys"] = len(LINK_POOL)
    
    _dlog(
        f"[index] Indexed {len(LINK_POOL_LIST)} flat link records and "
        f"{len(LINK_POOL)} unique URL keys from {len(sheets)} sheets "
        f"in {round(time.time()-start_ts,2)}s"
    )
    return rows, sheets


def build_database(verbose: bool = False, deep: bool = False) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Wrapper for index_sources."""
    return index_sources(verbose=verbose, deep=deep)


# =========================
# Search
# =========================
def _tokens(q_fold: str) -> List[str]:
    """Tokenize folded query (min length 2)."""
    return [t for t in re.split(r"\s+", q_fold) if len(t) >= 2]


def _all_tokens_in_text(q_fold: str, text_fold: str) -> bool:
    """Check if all query tokens appear in text (word boundary)."""
    toks = _tokens(q_fold)
    return all(re.search(rf"\b{re.escape(tok)}\b", text_fold) for tok in toks)


def _match_score(q_raw: str, s_raw: str, exact: bool, fuzz_threshold: int) -> int:
    """Calculate match score between query and string."""
    q_fix = fix_vietnamese_text(q_raw)
    s_fix = fix_vietnamese_text(s_raw)
    q_fold = fold_vietnamese(q_fix)
    s_fold = fold_vietnamese(s_fix)
    
    if exact:
        return 100 if _all_tokens_in_text(q_fold, s_fold) else 0
    
    return max(
        fuzz.partial_ratio(q_fix, s_fix),
        fuzz.partial_ratio(q_fold, s_fold)
    )


def _snippet(s: str, q: str, window: int = 60) -> str:
    """Extract snippet around query match."""
    s_fix = fix_vietnamese_text(s)
    q_fix = fix_vietnamese_text(q)
    s_fold = fold_vietnamese(s_fix)
    q_fold = fold_vietnamese(q_fix)
    
    m = re.search(re.escape(q_fold), s_fold, flags=re.IGNORECASE)
    if not m:
        return s_fix[:window * 2]
    
    i = m.start()
    left = max(0, i - window)
    right = min(len(s_fix), i + window)
    return s_fix[left:right]


def search_rows(query: str, top_k: int = 20, fuzz_threshold: int = 85, exact: bool = False) -> List[Dict[str, Any]]:
    """Search in indexed rows."""
    results: List[Tuple[int, Dict[str, Any]]] = []
    if not query or not str(query).strip():
        return []
    
    q_fixed, q_fold = normalize_query(query)
    
    for row in DATABASE_ROWS:
        raw = row.get("text") or ""
        text_fixed = fix_vietnamese_text(raw)
        text_fold = fold_vietnamese(text_fixed)
        
        if exact:
            ok = _all_tokens_in_text(q_fold, text_fold)
            score = 100 if ok else 0
        else:
            if q_fixed.lower() in text_fixed.lower() or q_fold in text_fold:
                score = 100
            else:
                score = max(
                    fuzz.partial_ratio(q_fixed, text_fixed),
                    fuzz.partial_ratio(q_fold, text_fold)
                )
        
        if score >= (100 if exact else fuzz_threshold):
            results.append((score, {
                "sheet": row["sheet"],
                "row": row["row"],
                "snippet": _snippet(text_fixed, q_fixed),
                "snippet_nodau": _snippet(text_fold, q_fold),
                "links": sorted(set(row.get("links", []))),
                "score": score
            }))
    
    results.sort(key=lambda x: x[0], reverse=True)
    return [r for _, r in results[:top_k]]


def _search_in_one_url_core(
    url: str, q: str, *,
    gid: Optional[str] = None,
    exact: bool = False,
    fuzz_threshold: int = 85,
    max_rows: int = 10000
) -> List[dict] | dict:
    """
    Search in a single URL (Google Sheets/CSV).
    Returns list of hits or error dict.
    """
    csv_text, finfo = safe_fetch_csv_text(url, gid=gid)
    if not csv_text:
        return {"error": finfo.get("error") or "fetch_failed", "normalized_url": finfo.get("normalized_url")}

    try:
        rows = read_csv_text(csv_text)
    except Exception as e:
        return {"error": f"csv_parse_failed: {e}", "normalized_url": finfo.get("normalized_url")}

    hits: List[dict] = []
    for idx, row in enumerate(rows[:max_rows], start=1):
        line = " | ".join("" if c is None else str(c) for c in row)
        score = _match_score(q, line, exact, fuzz_threshold)
        if score >= (100 if exact else fuzz_threshold):
            hits.append({
                "row": idx,
                "score": score,
                "snippet": _snippet(line, q),
                "values": [fix_vietnamese_text("" if c is None else str(c)) for c in row],
            })
    return hits
