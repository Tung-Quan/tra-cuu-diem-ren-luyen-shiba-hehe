# backend.py — full version (deep scan + vi-fold search + Sheets/Drive fallbacks + debug)
import os
import re
import io
import csv
import json
import time
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from ftfy import fix_text
from rapidfuzz import fuzz

# HTTP fetch & HTML parse
import httpx
from bs4 import BeautifulSoup

# ---- Google Sheets via gspread (values/formulas) ----
try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except Exception:
    HAS_GSPREAD = False
    Credentials = None  # type: ignore

# ---- Google APIs (Sheets + Drive) for deep scan & export ----
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload
    HAS_GOOGLE_API = True
except Exception:
    HAS_GOOGLE_API = False

# =========================
# FastAPI app & CORS
# =========================
app = FastAPI(title="Link-aware Search Backend", version="2.0.0 (deep+fold+mimes)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# Config
# =========================
DEFAULT_SPREADSHEET_ID = os.environ.get(
    "SPREADSHEET_ID",
    "1-ypUyKglUjblgy1Gy0gITcdHF4YLdJnaCNKM_6_fCrI"  # đổi ID nếu cần
)
GOOGLE_CREDS = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "credentials.json")
USE_DEEP = os.environ.get("DEEP_INDEX", "1").lower() in ("1", "true", "yes")

# =========================
# Globals (in-memory DB)
# =========================
DATABASE_ROWS: List[Dict[str, Any]] = []   # row records for quick search
SHEETS: List[str] = []                     # sheet titles
LINK_POOL: Dict[str, List[Dict[str, Any]]] = {}  # url -> [{sheet,row,col,address,...}]

# Debug ring buffer for logs
DEBUG_LOG: List[str] = []
DEBUG_LOG_MAX = 5000
STATS: Dict[str, Any] = {"built_at": None, "total_links": 0, "per_sheet": []}

# Skip / cache
GSPREAD_SKIP_IDS: set[str] = set()        # spreadsheet IDs not suitable for gspread
URL_ACCESS_CACHE: dict[str, str] = {}     # url -> "ok"|"private"|"unsupported"
DRIVE_META_CACHE: dict[str, dict] = {}    # fileId -> {id,name,mimeType}

# =========================
# Logging helper
# =========================
def _dlog(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    DEBUG_LOG.append(line)
    if len(DEBUG_LOG) > DEBUG_LOG_MAX:
        del DEBUG_LOG[: len(DEBUG_LOG) - DEBUG_LOG_MAX]

# =========================
# Utilities
# =========================
COL_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
def _a1_addr(row: int, col: int) -> str:
    c = col
    label = ""
    while c:
        c, rem = divmod(c - 1, 26)
        label = COL_LETTERS[rem] + label
    return f"{label}{row}"

URL_RE = re.compile(r"https?://[^\s)>\]\"']+", re.IGNORECASE)
DOCS_ID_RE = re.compile(r"docs\.google\.com/document/d/([a-zA-Z0-9_-]+)")
SHEETS_ID_RE = re.compile(r"docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)")
GID_RE = re.compile(r"[#?&]gid=(\d+)")

def classify_google_url(url: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Return (kind, file_id, gid?) where kind in {'docs','sheets','unknown'}.
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

def export_candidates(url: str) -> List[str]:
    """
    Possible export endpoints for public Sheets/Docs.
    Sheets: CSV (with gid if present)
    Docs: TXT
    """
    kind, file_id, maybe_gid = classify_google_url(url)
    if kind == "docs" and file_id:
        return [f"https://docs.google.com/document/d/{file_id}/export?format=txt"]
    if kind == "sheets" and file_id:
        base = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=csv"
        return [f"{base}&gid={maybe_gid}"] if maybe_gid else [base]
    return [url]

def extract_links_from_cell(val: Any, formula: Any) -> List[str]:
    """
    Pull URLs from cell value and formula (HYPERLINK). De-duplicate by base.
    """
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
    out, seen = [], set()
    for u in links:
        if not isinstance(u, str):
            continue
        cleaned = u.strip().strip('")]}').strip()
        if not cleaned.startswith("http"):
            continue
        base = cleaned.split("#")[0].split("?")[0]
        if base not in seen:
            out.append(cleaned)
            seen.add(base)
    return out

def repair_text(s: str) -> str:
    try:
        s = fix_text(s)
    except Exception:
        pass
    s = s.replace("\u00A0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def fold_vi(s: str) -> str:
    """
    Chuẩn hoá để tìm không dấu:
    - Sửa mojibake (repair_text)
    - Đổi đ/Đ -> d/D
    - NFKD rồi bỏ dấu kết hợp
    """
    if not isinstance(s, str):
        s = "" if s is None else str(s)
    s = repair_text(s)
    s = s.replace("đ", "d").replace("Đ", "D")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()

def normalize_query(q: str) -> Tuple[str, str]:
    """Trả về (q_fixed, q_fold) = (đã sửa font, đã bỏ dấu)."""
    q_fixed = repair_text(q or "")
    q_fold = fold_vi(q_fixed)
    return q_fixed, q_fold

def _snippet(text: str, query: str, width: int = 120) -> str:
    text_low = text.lower()
    q = query.lower()
    i = text_low.find(q)
    if i < 0:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, i - width // 2)
    end = min(len(text), i + len(q) + width // 2)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end] + suffix

# =========================
# Clients & helpers (Google)
# =========================
def _resolve_creds_path(p: str) -> str:
    if not os.path.isabs(p) and not os.path.exists(p):
        cand = os.path.join(os.path.dirname(__file__), p)
        if os.path.exists(cand):
            return cand
    return p

def _gspread_client() -> Optional["gspread.Client"]:
    if not HAS_GSPREAD or Credentials is None:
        return None
    creds_path = _resolve_creds_path(GOOGLE_CREDS)
    try:
        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
        )
        return gspread.authorize(creds)
    except Exception as e:
        _dlog(f"[gspread] cannot authorize: {e}")
        return None

_SHEETS_SERVICE = None
def _sheets_service():
    global _SHEETS_SERVICE
    if _SHEETS_SERVICE:
        return _SHEETS_SERVICE
    if not HAS_GOOGLE_API or Credentials is None:
        _dlog("[deep] googleapiclient not available")
        return None
    try:
        creds = Credentials.from_service_account_file(
            _resolve_creds_path(GOOGLE_CREDS),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets.readonly",
                "https://www.googleapis.com/auth/drive.readonly",
            ],
        )
        _SHEETS_SERVICE = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return _SHEETS_SERVICE
    except Exception as e:
        _dlog(f"[deep] cannot build sheets service: {e}")
        return None

_DRIVE_SERVICE = None
def _drive_service():
    global _DRIVE_SERVICE
    if _DRIVE_SERVICE:
        return _DRIVE_SERVICE
    if not HAS_GOOGLE_API or Credentials is None:
        _dlog("[drive] googleapiclient not available")
        return None
    try:
        creds = Credentials.from_service_account_file(
            _resolve_creds_path(GOOGLE_CREDS),
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        _DRIVE_SERVICE = build("drive", "v3", credentials=creds, cache_discovery=False)
        return _DRIVE_SERVICE
    except Exception as e:
        _dlog(f"[drive] cannot build service: {e}")
        return None

def _drive_get_meta(file_id: str) -> Optional[dict]:
    if not file_id:
        return None
    if file_id in DRIVE_META_CACHE:
        return DRIVE_META_CACHE[file_id]
    svc = _drive_service()
    if not svc:
        return None
    try:
        meta = svc.files().get(
            fileId=file_id,
            fields="id,name,mimeType,shortcutDetails"
        ).execute()
        # resolve shortcut -> target
        if (meta.get("mimeType") == "application/vnd.google-apps.shortcut" and
            (meta.get("shortcutDetails") or {}).get("targetId")):
            target_id = meta["shortcutDetails"]["targetId"]
            meta2 = svc.files().get(
                fileId=target_id,
                fields="id,name,mimeType"
            ).execute()
            meta = {"id": meta2.get("id"), "name": meta2.get("name"), "mimeType": meta2.get("mimeType")}
        DRIVE_META_CACHE[file_id] = meta
        return meta
    except Exception as e:
        _dlog(f"[drive] get meta failed {file_id}: {e}")
        return None

def _drive_download_bytes(file_id: str) -> Optional[bytes]:
    svc = _drive_service()
    if not svc:
        return None
    try:
        req = svc.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return buf.getvalue()
    except Exception as e:
        _dlog(f"[drive] download failed {file_id}: {e}")
        return None

def _xlsx_bytes_to_csvtext(data: bytes) -> Optional[str]:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
        out = io.StringIO()
        w = csv.writer(out)
        for ws in wb.worksheets:
            w.writerow([f"-- SHEET: {ws.title} --"])
            for row in ws.iter_rows(values_only=True):
                w.writerow([("" if v is None else str(v)) for v in row])
        return out.getvalue()
    except Exception as e:
        _dlog(f"[excel] parse xlsx failed: {e}")
        return None

def _sheets_values_csv_by_gid(file_id: str, gid: Optional[str]) -> Optional[str]:
    svc = _sheets_service()
    if not svc:
        return None
    try:
        meta = svc.spreadsheets().get(
            spreadsheetId=file_id,
            fields="sheets(properties(sheetId,title))"
        ).execute()
        sheets = (meta or {}).get("sheets", [])
        title = None
        if gid:
            for s in sheets:
                props = (s.get("properties") or {})
                if str(props.get("sheetId")) == str(gid):
                    title = props.get("title"); break
        if not title and sheets:
            title = (sheets[0].get("properties") or {}).get("title")
        if not title:
            return None
        vals = svc.spreadsheets().values().get(
            spreadsheetId=file_id,
            range=title,
            majorDimension="ROWS"
        ).execute().get("values", [])
        return _csv_to_text(vals)
    except HttpError as he:
        _dlog(f"[sheets] values.get failed {file_id}: {he}")
        return None
    except Exception as e:
        _dlog(f"[sheets] values.get error {file_id}: {e}")
        return None

# =========================
# HTTP fetch helper
# =========================
async def _http_get_text(url: str, timeout: float = 20.0) -> Optional[str]:
    """
    Tải nội dung qua HTTP:
      - text/plain, text/csv: trả thẳng text
      - HTML: bóc sạch tag, trả text
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

def _csv_to_text(rows: List[List[str]]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerows(rows)
    return output.getvalue()

# =========================
# Fetch text from URL (Sheets/Docs/Excel/HTML)
# =========================
def _mark_gspread_skip(file_id: str, reason: str):
    if not file_id:
        return
    if file_id not in GSPREAD_SKIP_IDS:
        GSPREAD_SKIP_IDS.add(file_id)
        _dlog(f"[fetch] skip gspread for {file_id} ({reason})")

def _mark_url_private(url: str, reason: str = "private"):
    if URL_ACCESS_CACHE.get(url) != "private":
        URL_ACCESS_CACHE[url] = "private"
        _dlog(f"[fetch] mark private for {url} ({reason})")

async def fetch_text_from_url(url: str) -> Optional[str]:
    kind, file_id, maybe_gid = classify_google_url(url)

    # Nếu đã biết url private → bỏ qua luôn
    if URL_ACCESS_CACHE.get(url) == "private":
        return None

    # Nếu có file_id, sniff mime qua Drive (resolve shortcut)
    meta = _drive_get_meta(file_id) if file_id else None
    if meta and meta.get("id") and file_id and meta["id"] != file_id:
        file_id = meta["id"]  # resolved target
    mime = (meta or {}).get("mimeType", "")

    # ===== Route theo MIME =====
    if mime == "application/vnd.google-apps.spreadsheet":
        # gspread trước (nếu không skip)
        if HAS_GSPREAD and (file_id not in GSPREAD_SKIP_IDS):
            client = _gspread_client()
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
                        return repair_text(_csv_to_text(values))
                except Exception as e:
                    if "not supported for this document" in str(e).lower():
                        _mark_gspread_skip(file_id, "unsupported-or-noaccess")
                    else:
                        _dlog(f"[fetch] gspread sheets failed once for {file_id}: {str(e)[:160]}")
        # Sheets API values
        csv_text = _sheets_values_csv_by_gid(file_id, maybe_gid)
        if csv_text:
            return repair_text(csv_text)
        _mark_url_private(url, "sheets_api_no_access")
        return None

    if mime == "application/vnd.google-apps.document":
        # Google Docs -> export TXT
        svc = _drive_service()
        if svc:
            try:
                data = svc.files().export(fileId=file_id, mimeType="text/plain").execute()  # type: ignore
                text = data.decode("utf-8", "ignore") if isinstance(data, bytes) else str(data)
                return repair_text(text)
            except Exception as e:
                _dlog(f"[drive] export txt failed {file_id}: {e}")
        _mark_url_private(url, "drive_export_no_access")
        return None

    if mime in (
        "application/vnd.google-apps.presentation",  # Slides
        "application/vnd.google-apps.drawing",       # Drawings
        "application/vnd.google-apps.folder",        # Folder
        "application/vnd.google-apps.form",          # Forms
    ):
        _mark_url_private(url, "unsupported_mime")
        return None

    if mime in ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",):
        # Excel .xlsx uploaded to Drive
        data = _drive_download_bytes(file_id)
        if data:
            text = _xlsx_bytes_to_csvtext(data)
            if text:
                return repair_text(text)
        _mark_url_private(url, "excel_download_or_parse_failed")
        return None

    # Nếu không có/không đọc MIME (public?) → thử public export candidates
    for cand in export_candidates(url):
        text = await _http_get_text(cand)
        if text:
            return repair_text(text)

    # Cuối cùng: HTML thường
    if kind == "unknown":
        text = await _http_get_text(url)
        if text:
            return repair_text(text)

    _mark_url_private(url, "final_no_access_or_unknown_mime")
    return None

# =========================
# Deep scan helpers (rich text links in Sheets)
# =========================
def _links_from_text_runs(text_format_runs: Optional[List[Dict[str, Any]]]) -> List[str]:
    urls: List[str] = []
    for run in (text_format_runs or []):
        fmt = (run or {}).get("format") or {}
        link = fmt.get("link") or {}
        uri = link.get("uri")
        if uri:
            urls.append(uri)
    return urls

def _clean_urls(urls: List[Any]) -> List[str]:
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

def deep_scan_all_sheets(service, spreadsheet_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Read ALL sheets with includeGridData=True and extract links from:
    - cell.hyperlink
    - userEnteredValue.formulaValue (HYPERLINK & naked http)
    - userEnteredValue.stringValue (typed http)
    - textFormatRuns.format.link.uri (rich text link)
    - formattedValue (rendered)
    - note (links in cell note)
    Return: {sheet_title: [{url,row,col,address}]}
    """
    try:
        resp = service.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            includeGridData=True,
            fields=(
                "sheets("
                "properties(title),"
                "data(rowData(values(hyperlink,userEnteredValue,formattedValue,textFormatRuns,note)))"
                ")"
            ),
        ).execute()
    except HttpError as he:
        _dlog(f"[deep] HttpError on spreadsheet: {he}")
        return {}
    except Exception as e:
        _dlog(f"[deep] error on spreadsheet: {e}")
        return {}

    results: Dict[str, List[Dict[str, Any]]] = {}
    for s in resp.get("sheets", []):
        title = (s.get("properties") or {}).get("title", "")
        data_blocks = s.get("data", []) or []
        found: List[Dict[str, Any]] = []
        for block in data_blocks:
            rowData = block.get("rowData", []) or []
            for r_idx, row in enumerate(rowData):
                values = (row or {}).get("values", []) or []
                for c_idx, cell in enumerate(values):
                    urls: List[str] = []
                    hl = cell.get("hyperlink")
                    if hl:
                        urls.append(hl)
                    uev = cell.get("userEnteredValue") or {}
                    fv = uev.get("formulaValue")
                    if fv:
                        urls.extend(URL_RE.findall(fv))
                        m = re.search(r'HYPERLINK\s*\(\s*"([^"]+)"', fv, re.IGNORECASE)
                        if m:
                            urls.append(m.group(1))
                    sv = uev.get("stringValue")
                    if sv:
                        urls.extend(URL_RE.findall(sv))
                    urls.extend(_links_from_text_runs(cell.get("textFormatRuns")))
                    fmt = cell.get("formattedValue")
                    if fmt:
                        urls.extend(URL_RE.findall(fmt))
                    note = cell.get("note")
                    if note:
                        urls.extend(URL_RE.findall(note))
                    urls = _clean_urls(urls)
                    if not urls:
                        continue
                    r1 = r_idx + 1
                    c1 = c_idx + 1
                    a1 = _a1_addr(r1, c1)
                    for u in urls:
                        found.append({"url": u, "row": r1, "col": c1, "address": a1})
        results[title] = found
    return results

# =========================
# Indexer
# =========================
def index_sources(verbose: bool = False, deep: bool = False) -> Tuple[List[Dict[str, Any]], List[str]]:
    rows: List[Dict[str, Any]] = []
    sheets: List[str] = []
    LINK_POOL.clear()
    STATS["per_sheet"] = []
    start_ts = time.time()

    if not DEFAULT_SPREADSHEET_ID:
        _dlog("[index] No SPREADSHEET_ID set → empty index.")
        return rows, sheets
    if not HAS_GSPREAD:
        _dlog("[index] gspread not available → cannot open spreadsheet; empty index.")
        return rows, sheets

    client = _gspread_client()
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

    gid_to_name: Dict[str, str] = {}
    for ws in worksheets:
        props = getattr(ws, "_properties", {}) or {}
        gid = props.get("sheetId") or props.get("id")
        if gid is not None:
            gid_to_name[str(gid)] = ws.title

    # prepare deep data once
    deep_map: Dict[str, List[Dict[str, Any]]] = {}
    if deep:
        svc = _sheets_service()
        if svc:
            _dlog("[deep] ENABLED: scanning rich-text links via Sheets API…")
            deep_map = deep_scan_all_sheets(svc, DEFAULT_SPREADSHEET_ID) or {}
            total_occ = sum(len(v) for v in deep_map.values())
            _dlog(f"[deep] SUMMARY: got {total_occ} link occurrences from API")
        else:
            _dlog("[deep] DISABLED (service not available)")

    total_links = 0
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
                formulas = [
                    [cell if isinstance(cell, str) else ("" if cell is None else str(cell)) for cell in row]
                    for row in raw_formulas
                ]
            else:
                formulas = []
        except Exception as e:
            _dlog(f"[index] cannot read formulas: {title}: {e}")
            formulas = []

        # stats counters
        non_empty_cells = 0
        value_http_cells = 0
        formula_http_cells = 0
        cell_with_links = 0
        sheet_links_before = len(LINK_POOL)

        if verbose:
            _dlog(f"[index] Sheet '{title}' size ≈ {nrows}x{ncols}")

        # pack simple rows
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

        # walk cells (value/formula)
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
                    loc = {"sheet": title, "row": r + 1, "col": c + 1, "address": a1}
                    if maybe_gid:
                        loc["sheet_gid"] = maybe_gid
                        if maybe_gid in gid_to_name:
                            loc["sheet_name"] = gid_to_name[maybe_gid]
                    LINK_POOL.setdefault(u, []).append(loc)

                try:
                    rows[base_row_index + r]["links"].extend(link_list)
                except Exception:
                    pass

        added_links = len(LINK_POOL) - sheet_links_before
        total_links = len(LINK_POOL)

        # integrate deep links (rich text)
        deep_added = 0
        deep_occurs = 0
        if deep and title in deep_map:
            occs = deep_map.get(title) or []
            deep_occurs = len(occs)
            for item in occs:
                u = item["url"]; r1 = item["row"]; c1 = item["col"]; a1 = item["address"]
                exists = any(loc.get("sheet")==title and loc.get("address")==a1 for loc in LINK_POOL.get(u, []))
                if not exists:
                    LINK_POOL.setdefault(u, []).append({"sheet": title, "row": r1, "col": c1, "address": a1})
                    deep_added += 1
                # push into row record
                try:
                    rows[sheet_row_base[title] + (r1 - 1)]["links"].append(u)
                except Exception:
                    pass
            total_links = len(LINK_POOL)

        sheet_stat = {
            "sheet": title,
            "size": f"{nrows}x{ncols}",
            "non_empty_cells": non_empty_cells,
            "value_http_cells": value_http_cells,
            "formula_http_cells": formula_http_cells,
            "cells_with_links_extracted": cell_with_links,
            "unique_links_added": added_links,
            "deep_occurrences_seen": deep_occurs,
            "deep_links_added": deep_added,
            "unique_links_total_now": total_links,
        }
        STATS["per_sheet"].append(sheet_stat)

        _dlog(
            f"[index] '{title}': non-empty={non_empty_cells}, value_has_http={value_http_cells}, "
            f"formula_has_http/HYPERLINK={formula_http_cells}, cells_extracted_links={cell_with_links}, "
            f"unique_links_added={added_links}, deep_occurs={deep_occurs}, deep_links_added={deep_added}, "
            f"unique_links_total={total_links}"
        )

    STATS["built_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    STATS["total_links"] = len(LINK_POOL)
    _dlog(f"[index] Indexed {len(LINK_POOL)} unique links from {len(sheets)} sheets in {round(time.time()-start_ts,2)}s")
    return rows, sheets

def build_database(verbose: bool = False, deep: bool = False) -> Tuple[List[Dict[str, Any]], List[str]]:
    return index_sources(verbose=verbose, deep=deep)

# =========================
# Search helpers
# =========================
def search_rows(query: str, top_k: int = 20, fuzz_threshold: int = 85) -> List[Dict[str, Any]]:
    results: List[Tuple[int, Dict[str, Any]]] = []
    if not query or not str(query).strip():
        return []
    q_fixed, q_fold = normalize_query(query)
    for row in DATABASE_ROWS:
        raw = row.get("text") or ""
        text_fixed = repair_text(raw)
        text_fold  = fold_vi(text_fixed)

        if q_fixed.lower() in text_fixed.lower() or q_fold in text_fold:
            score = 100
        else:
            score = max(
                fuzz.partial_ratio(q_fixed, text_fixed),
                fuzz.partial_ratio(q_fold,  text_fold)
            )
        if score >= fuzz_threshold:
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

# =========================
# API endpoints
# =========================
@app.get("/health")
def health():
    return {"ok": True, "rows": len(DATABASE_ROWS), "sheets": len(SHEETS), "links": len(LINK_POOL)}

@app.get("/sheets")
def list_sheets():
    return {"sheets": SHEETS}

@app.get("/links_index")
def links_index(limit: int = 200):
    examples = []
    for i, (u, locs) in enumerate(LINK_POOL.items()):
        if i >= limit:
            break
        examples.append({"url": u, "where": locs[:5]})
    return {"total": len(LINK_POOL), "examples": examples}

@app.get("/rebuild_db")
def rebuild_db(deep: int | None = None):
    global DATABASE_ROWS, SHEETS
    resolved_deep = USE_DEEP if deep is None else bool(deep)
    t0 = time.time()
    rows, sheets = build_database(verbose=False, deep=resolved_deep)
    DATABASE_ROWS = rows
    SHEETS = sheets
    dt = round(time.time() - t0, 2)
    return {
        "status": "ok",
        "rows": len(DATABASE_ROWS),
        "sheets": len(SHEETS),
        "links": len(LINK_POOL),
        "took_s": dt,
        "stats": STATS,
        "deep_used": resolved_deep,
    }

# ---- DEBUG ----
@app.get("/debug/reindex")
def debug_reindex(verbose: int = 1, deep: int | None = None):
    global DATABASE_ROWS, SHEETS
    resolved_deep = USE_DEEP if deep is None else bool(deep)
    t0 = time.time()
    rows, sheets = build_database(verbose=bool(verbose), deep=resolved_deep)
    DATABASE_ROWS = rows
    SHEETS = sheets
    dt = round(time.time() - t0, 2)
    return {
        "status": "ok",
        "rows": len(DATABASE_ROWS),
        "sheets": len(SHEETS),
        "links": len(LINK_POOL),
        "took_s": dt,
        "stats": STATS,
        "deep_used": resolved_deep,
        "log_tail_hint": "GET /debug/scan_log?limit=300",
    }

@app.get("/debug/stats")
def debug_stats():
    return STATS

@app.get("/debug/scan_log")
def debug_scan_log(limit: int = 300):
    limit = max(1, min(limit, 2000))
    return {"lines": DEBUG_LOG[-limit:]}

@app.get("/debug/capabilities")
def debug_capabilities():
    return {
        "HAS_GSPREAD": HAS_GSPREAD,
        "HAS_GOOGLE_API": HAS_GOOGLE_API,
        "SPREADSHEET_ID": DEFAULT_SPREADSHEET_ID,
        "CREDS_PATH": GOOGLE_CREDS,
        "USE_DEEP": USE_DEEP,
    }

@app.get("/debug/gspread_skip")
def debug_gspread_skip():
    return {"count": len(GSPREAD_SKIP_IDS), "ids": list(GSPREAD_SKIP_IDS)[:50]}

@app.post("/debug/gspread_skip/clear")
def debug_gspread_skip_clear():
    GSPREAD_SKIP_IDS.clear()
    return {"status": "ok", "cleared": True}

@app.get("/debug/service_account")
def debug_service_account():
    try:
        with open(_resolve_creds_path(GOOGLE_CREDS), "r", encoding="utf-8") as f:
            return {"client_email": json.load(f).get("client_email")}
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/check_url")
async def debug_check_url(u: str):
    kind, file_id, gid = classify_google_url(u)
    can = export_candidates(u)
    status_before = URL_ACCESS_CACHE.get(u)
    text = await fetch_text_from_url(u)
    status_after = URL_ACCESS_CACHE.get(u)
    return {
        "kind": kind, "file_id": file_id, "gid": gid,
        "export_candidates": can,
        "was_marked": status_before, "now_marked": status_after,
        "fetched": bool(text),
        "snippet": (text[:180] + "…") if text else None
    }

# ---- SEARCH ----
@app.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    top_k: int = 20,
    follow_links: bool = False,
    link_limit: int = 10
):
    q_fixed, q_fold = normalize_query(q)
    base_hits = search_rows(q_fixed, top_k=top_k)
    out = {"query": q_fixed, "hits": base_hits, "link_hits": []}

    if follow_links and base_hits:
        visited = set()
        for h in base_hits:
            for url in h.get("links", [])[:link_limit]:
                if url in visited:
                    continue
                visited.add(url)
                text = await fetch_text_from_url(url)
                if not text:
                    continue
                text_fixed = repair_text(text)
                text_fold  = fold_vi(text_fixed)

                ok = (
                    q_fixed.lower() in text_fixed.lower()
                    or q_fold in text_fold
                    or max(
                        fuzz.partial_ratio(q_fixed, text_fixed),
                        fuzz.partial_ratio(q_fold,  text_fold)
                    ) >= 85
                )
                if ok:
                    out["link_hits"].append({
                        "url": url,
                        "snippet": _snippet(text_fixed, q_fixed, width=180),
                        "snippet_nodau": _snippet(text_fold, q_fold, width=180)
                    })
    return out

@app.get("/search_links")
def search_links(q: str = Query(..., description="substring to match in URL"), limit: int = 50):
    qlow = q.lower()
    matches = []
    for url, locs in LINK_POOL.items():
        if qlow in url.lower():
            matches.append({"url": url, "where": locs[:5], "count": len(locs)})
            if len(matches) >= limit:
                break
    return {"query": q, "matches": matches, "total_urls": len(LINK_POOL)}

# =========================
# Startup
# =========================
@app.on_event("startup")
def _startup_build():
    global DATABASE_ROWS, SHEETS
    _dlog(f"Building database... (deep={'ON' if USE_DEEP else 'OFF'})")
    rows, sheets = build_database(verbose=False, deep=USE_DEEP)
    DATABASE_ROWS = rows
    SHEETS = sheets
    _dlog(f"Database built with {len(DATABASE_ROWS)} rows from {len(SHEETS)} sheets; {len(LINK_POOL)} links")
