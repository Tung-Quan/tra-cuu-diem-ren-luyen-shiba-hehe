"""
Google API client management and utilities.
Handles gspread, Google Sheets API, and Google Drive API clients.
"""
import os
import io
import re
from typing import Any, Dict, List, Optional

from backend.config import (
    GOOGLE_CREDS,
    HAS_GSPREAD,
    HAS_GOOGLE_API,
    DRIVE_META_CACHE,
    debug_log,
)

if HAS_GSPREAD:
    import gspread
    from google.oauth2.service_account import Credentials
else:
    Credentials = None

if HAS_GOOGLE_API:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseDownload


# =========================
# Singleton Services
# =========================
_SHEETS_SERVICE = None
_DRIVE_SERVICE = None
_DOCS_SERVICE = None

# =========================
# Helper Functions
# =========================
def _resolve_creds_path(path: str) -> str:
    """Resolve credentials file path relative to backend directory."""
    if not os.path.isabs(path) and not os.path.exists(path):
        cand = os.path.join(os.path.dirname(__file__), "..", path)
        if os.path.exists(cand):
            return cand
    return path


# =========================
# gspread Client
# =========================
def get_gspread_client() -> Optional["gspread.Client"]:
    """Get or create gspread client singleton."""
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
        debug_log(f"[gspread] cannot authorize: {e}")
        return None


# =========================
# Google Sheets API Service
# =========================
def get_sheets_service():
    """Get or create Sheets API service singleton."""
    global _SHEETS_SERVICE
    if _SHEETS_SERVICE:
        return _SHEETS_SERVICE
    
    if not HAS_GOOGLE_API or Credentials is None:
        debug_log("[sheets] googleapiclient not available")
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
        debug_log(f"[sheets] cannot build service: {e}")
        return None


# =========================
# Google Drive API Service
# =========================
def get_drive_service():
    """Get or create Drive API service singleton."""
    global _DRIVE_SERVICE
    if _DRIVE_SERVICE:
        return _DRIVE_SERVICE
    
    if not HAS_GOOGLE_API or Credentials is None:
        debug_log("[drive] googleapiclient not available")
        return None
    
    try:
        creds = Credentials.from_service_account_file(
            _resolve_creds_path(GOOGLE_CREDS),
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        _DRIVE_SERVICE = build("drive", "v3", credentials=creds, cache_discovery=False)
        return _DRIVE_SERVICE
    except Exception as e:
        debug_log(f"[drive] cannot build service: {e}")
        return None


# =========================
# Google Docs API Service
# =========================
def get_docs_service():
    """Get or create Docs API service singleton."""
    global _DOCS_SERVICE
    if _DOCS_SERVICE:
        return _DOCS_SERVICE
    
    if not HAS_GOOGLE_API or Credentials is None:
        debug_log("[docs] googleapiclient not available")
        return None
    
    try:
        creds = Credentials.from_service_account_file(
            _resolve_creds_path(GOOGLE_CREDS),
            scopes=["https://www.googleapis.com/auth/documents.readonly"],
        )
        _DOCS_SERVICE = build("docs", "v1", credentials=creds, cache_discovery=False)
        return _DOCS_SERVICE
    except Exception as e:
        debug_log(f"[docs] cannot build service: {e}")
        return None


# =========================
# Drive Operations
# =========================
def get_drive_file_meta(file_id: str) -> Optional[dict]:
    """
    Get Drive file metadata (cached).
    Resolves shortcuts to target files.
    """
    if not file_id:
        return None
    
    if file_id in DRIVE_META_CACHE:
        return DRIVE_META_CACHE[file_id]
    
    svc = get_drive_service()
    if not svc:
        return None
    
    try:
        meta = svc.files().get(
            fileId=file_id,
            fields="id,name,mimeType,shortcutDetails"
        ).execute()
        
        # Resolve shortcut to target
        if (meta.get("mimeType") == "application/vnd.google-apps.shortcut" and
            (meta.get("shortcutDetails") or {}).get("targetId")):
            target_id = meta["shortcutDetails"]["targetId"]
            meta2 = svc.files().get(
                fileId=target_id,
                fields="id,name,mimeType"
            ).execute()
            meta = {
                "id": meta2.get("id"),
                "name": meta2.get("name"),
                "mimeType": meta2.get("mimeType")
            }
        
        DRIVE_META_CACHE[file_id] = meta
        return meta
    
    except Exception as e:
        debug_log(f"[drive] get meta failed {file_id}: {e}")
        return None


def download_drive_file(file_id: str) -> Optional[bytes]:
    """Download file content from Drive."""
    svc = get_drive_service()
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
        debug_log(f"[drive] download failed {file_id}: {e}")
        return None


# =========================
# Sheets Operations
# =========================
def get_sheet_values_by_gid(file_id: str, gid: Optional[str], max_rows: int = 5) -> Optional[Dict[str, List[List[str]]]]:
    """
    Get sheet values by GID using Sheets API.
    
    Returns:
        {sheet_title: [[cell_values...]]}
    """
    svc = get_sheets_service()
    if not svc:
        return None
    
    try:
        meta = svc.spreadsheets().get(
            spreadsheetId=file_id,
            fields="sheets(properties(sheetId,title))"
        ).execute()
        
        sheets = (meta or {}).get("sheets", [])
        title = None
        
        # Find sheet by GID
        if gid:
            for s in sheets:
                props = (s.get("properties") or {})
                if str(props.get("sheetId")) == str(gid):
                    title = props.get("title")
                    break
        
        # Fallback to first sheet
        if not title and sheets:
            title = (sheets[0].get("properties") or {}).get("title")
        
        if not title:
            return None
        
        # Get values
        vals = svc.spreadsheets().values().get(
            spreadsheetId=file_id,
            range=title,
            majorDimension="ROWS"
        ).execute().get("values", [])
        
        return {title: (vals[:max_rows] if isinstance(vals, list) else [])}
    
    except Exception as e:
        debug_log(f"[sheets] rows_by_gid error {file_id}: {e}")
        return None


def get_sheet_values_as_csv(file_id: str, gid: Optional[str]) -> Optional[str]:
    """Get sheet values as CSV text using Sheets API."""
    import csv
    import io
    
    rows_map = get_sheet_values_by_gid(file_id, gid, max_rows=10000)
    if not rows_map:
        return None
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    for sheet_title, rows in rows_map.items():
        for row in rows:
            writer.writerow(row)
    
    return output.getvalue()

# =========================
# Google Docs API Service 
# =========================
def get_docs_service():
    """Get or create Docs API service singleton."""
    global _DOCS_SERVICE
    if _DOCS_SERVICE:
        return _DOCS_SERVICE
    
    if not HAS_GOOGLE_API or Credentials is None:
        debug_log("[docs] googleapiclient not available")
        return None
    
    try:
        creds = Credentials.from_service_account_file(
            _resolve_creds_path(GOOGLE_CREDS),
            scopes=[
                "https://www.googleapis.com/auth/documents.readonly", # Scope quan trọng để đọc Docs
                "https://www.googleapis.com/auth/drive.readonly",
            ],
        )
        _DOCS_SERVICE = build("docs", "v1", credentials=creds, cache_discovery=False)
        return _DOCS_SERVICE
    except Exception as e:
        debug_log(f"[docs] cannot build service: {e}")
        return None

def get_doc_content(file_id: str) -> Optional[str]:
    """
    Download and extract text content from a Google Doc.
    Checks MIME type first to ensure it's a native Google Doc.
    """
    # 1. Kiểm tra Metadata để biết loại file
    meta = get_drive_file_meta(file_id)
    if not meta:
        debug_log(f"[docs] could not fetch meta for {file_id}")
        return None
    
    mime_type = meta.get("mimeType", "")
    print(f"[docs] File Name: {meta.get('name')}")
    print(f"[docs] Mime Type: {mime_type}")

    # 2. Nếu là file Word (.docx), báo lỗi hướng dẫn convert
    if mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return (
            "ERROR: Đây là file Microsoft Word (.docx), không phải Google Doc.\n"
            "Google Docs API không thể đọc trực tiếp file Word.\n"
            "Giải pháp: Mở file trên Drive -> File -> Save as Google Docs -> Dùng ID mới."
        )

    # 3. Nếu không phải Google Doc (ví dụ PDF, Image...)
    if mime_type != "application/vnd.google-apps.document":
        return f"ERROR: Định dạng file không hỗ trợ ({mime_type}). Chỉ hỗ trợ Google Docs."

    # 4. Nếu đúng là Google Doc, tiến hành đọc
    svc = get_docs_service()
    if not svc:
        return None

    try:
        document = svc.documents().get(documentId=file_id).execute()
        content = document.get('body').get('content')
        return _read_structural_elements(content)
    except Exception as e:
        debug_log(f"[docs] get content failed {file_id}: {e}")
        return None

def _read_structural_elements(elements: List[Dict[str, Any]]) -> str:
    """Recursively extracts text from document elements."""
    text = ''
    for value in elements:
        if 'paragraph' in value:
            elements = value.get('paragraph').get('elements')
            for elem in elements:
                text += elem.get('textRun', {}).get('content', '')
        elif 'table' in value:
            # Xử lý bảng: lặp qua các dòng và ô
            table = value.get('table')
            for row in table.get('tableRows'):
                cells = row.get('tableCells')
                for cell in cells:
                    text += _read_structural_elements(cell.get('content'))
                text += '\n' # Xuống dòng sau mỗi row của bảng
        elif 'tableOfContents' in value:
            # Xử lý mục lục
            toc = value.get('tableOfContents')
            text += _read_structural_elements(toc.get('content'))
    return text

# =========================
# Deep Scan (Rich Text Links)
# =========================
def extract_links_from_text_runs(text_format_runs: Optional[List[Dict[str, Any]]]) -> List[str]:
    """Extract URLs from Sheets rich text formatting."""
    urls: List[str] = []
    for run in (text_format_runs or []):
        fmt = (run or {}).get("format") or {}
        link = fmt.get("link") or {}
        uri = link.get("uri")
        if uri:
            urls.append(uri)
    return urls


def deep_scan_all_sheets(spreadsheet_id: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Deep scan all sheets for links using Sheets API.
    
    Extracts links from:
    - cell.hyperlink
    - userEnteredValue.formulaValue (HYPERLINK & naked URLs)
    - userEnteredValue.stringValue (typed URLs)
    - textFormatRuns.format.link.uri (rich text links)
    - formattedValue (rendered)
    - note (cell comments)
    
    Returns:
        {sheet_title: [{url, row, col, address}]}
    """
    from backend.utils.url_helpers import URL_RE
    
    svc = get_sheets_service()
    if not svc:
        return {}
    
    try:
        resp = svc.spreadsheets().get(
            spreadsheetId=spreadsheet_id,
            includeGridData=True,
            fields=(
                "sheets("
                "properties(title),"
                "data(rowData(values(hyperlink,userEnteredValue,formattedValue,textFormatRuns,note)))"
                ")"
            ),
        ).execute()
    except Exception as e:
        debug_log(f"[deep] error on spreadsheet {spreadsheet_id}: {e}")
        return {}
    
    # Helper to convert (row, col) to A1 notation
    def a1_addr(row: int, col: int) -> str:
        col_letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        c = col
        label = ""
        while c:
            c, rem = divmod(c - 1, 26)
            label = col_letters[rem] + label
        return f"{label}{row}"
    
    # Clean URLs
    def clean_urls(urls: List[Any]) -> List[str]:
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
    
    results: Dict[str, List[Dict[str, Any]]] = {}
    
    for sheet in resp.get("sheets", []):
        title = (sheet.get("properties") or {}).get("title", "")
        data_blocks = sheet.get("data", []) or []
        found: List[Dict[str, Any]] = []
        
        for block in data_blocks:
            row_data = block.get("rowData", []) or []
            for r_idx, row in enumerate(row_data):
                values = (row or {}).get("values", []) or []
                for c_idx, cell in enumerate(values):
                    urls: List[str] = []
                    
                    # Extract from various sources
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
                    
                    urls.extend(extract_links_from_text_runs(cell.get("textFormatRuns")))
                    
                    fmt = cell.get("formattedValue")
                    if fmt:
                        urls.extend(URL_RE.findall(fmt))
                    
                    note = cell.get("note")
                    if note:
                        urls.extend(URL_RE.findall(note))
                    
                    urls = clean_urls(urls)
                    if not urls:
                        continue
                    
                    r1 = r_idx + 1
                    c1 = c_idx + 1
                    a1 = a1_addr(r1, c1)
                    
                    for u in urls:
                        found.append({"url": u, "row": r1, "col": c1, "address": a1})
        
        results[title] = found
    
    return results

