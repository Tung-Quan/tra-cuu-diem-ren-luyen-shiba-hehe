"""
Script to automatically refactor backend.py by replacing sections with imports.
Run this to update the main backend.py file.
"""
import re

# Read the original backend.py
with open("backend.py", "r", encoding="utf-8") as f:
    content = f.read()

print("Original file: {len(content)} chars, {content.count(chr(10))} lines")

# Backup
with open("backend.py.backup", "w", encoding="utf-8") as f:
    f.write(content)

# =======================
# REPLACEMENTS
# =======================

# 1. Replace duplicate imports (lines 84-85)
content = re.sub(
    r'LINK_POOL_MAP: Dict\[str, List\[Dict\[str, Any\]\]\] = \{\}\nimport re\nfrom urllib\.parse import urlparse, parse_qs',
    'LINK_POOL_MAP: Dict[str, List[Dict[str, Any]]] = {}',
    content
)

# 2. Replace entire config section with import from config
config_section_pattern = r'# =========================\n# Config\n# =========================.*?USE_DEEP = .*?\n'
config_replacement = '''# =========================
# Configuration (imported from config module)
# =========================
from backend.config import (
    DEFAULT_SPREADSHEET_ID,
    GOOGLE_CREDS,
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
    DRIVE_META_CACHE,
    DEBUG_LOG,
    STATS,
    debug_log as _dlog,
    db_mysql
)

'''

content = re.sub(config_section_pattern, config_replacement, content, flags=re.DOTALL)

# 3. Remove duplicate global declarations (lines 76-83)
globals_pattern = r'# =========================\n# Globals \(in-memory DB\)\n# =========================\nDATABASE_ROWS.*?LINK_POOL_MAP: Dict\[str, List\[Dict\[str, Any\]\]\] = \{\}\n'
content = re.sub(globals_pattern, '', content, flags=re.DOTALL)

# 4. Add utility imports at top after FastAPI imports
utils_imports = '''
# =========================
# Local Utility Imports  
# =========================
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
    URL_RE
)

from backend.utils.csv_helpers import (
    read_csv_text,
    read_csv_bytes,
    csv_to_text,
    safe_fetch_csv_text,
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

'''

# Insert after "from urllib.parse import urlparse, parse_qs"
content = re.sub(
    r'(from urllib\.parse import urlparse, parse_qs\n)',
    r'\1' + utils_imports,
    content
)

# 5. Remove duplicate URL pattern definitions (lines 87-99)
content = re.sub(
    r'_GSHEETS_ID_PATTERNS = \[.*?\ndef extract_gsheets_file_id\(u: str\).*?return None\n',
    '',
    content,
    flags=re.DOTALL
)

# 6. Remove duplicate extract_gid function (lines 101-111)
content = re.sub(
    r'\ndef extract_gid\(u: str\).*?return None\n',
    '',
    content,
    flags=re.DOTALL
)

# 7. Replace vn_strict_fix, repair_text, fold_vi, etc. with imports
# Remove vn_strict_fix
content = re.sub(
    r'def vn_strict_fix\(s: str\).*?return s4\.strip\(\)\n',
    '',
    content,
    flags=re.DOTALL
)

# Remove v n_fix_if_needed
content = re.sub(
    r'def vn_fix_if_needed\(s: str\).*?return s\.strip\(\)\n',
    '',
    content,
    flags=re.DOTALL
)

# Remove fold_vi
content = re.sub(
    r'def fold_vi\(s: str\).*?return s\.lower\(\)\n',
    '',
    content,
    flags=re.DOTALL
)

# Remove normalize_query
content = re.sub(
    r'def normalize_query\(q: str\).*?return q_fixed, q_fold\n',
    '',
    content,
    flags=re.DOTALL
)

# Remove repair_text (it's just an alias)
content = re.sub(
    r'def repair_text\(s: str\).*?return vn_strict_fix\(s\)\n',
    '',
    content,
    flags=re.DOTALL
)

# Remove http_decode_bytes
content = re.sub(
    r'def http_decode_bytes\(resp\).*?return resp\.content\.decode\("utf-8", errors="replace"\)\n',
    '',
    content,
    flags=re.DOTALL
)

# 8. Replace function calls to use new names
content = content.replace('vn_strict_fix(', 'fix_vietnamese_text(')
content = content.replace('repair_text(', 'fix_vietnamese_text(')
content = content.replace('fold_vi(', 'fold_vietnamese(')
content = content.replace('http_decode_bytes(', 'decode_http_response(')

# 9. Replace _gspread_client() calls
content = content.replace('_gspread_client()', 'get_gspread_client()')
content = content.replace('_sheets_service()', 'get_sheets_service()')
content = content.replace('_drive_service()', 'get_drive_service()')
content = content.replace('_drive_get_meta(', 'get_drive_file_meta(')
content = content.replace('_drive_download_bytes(', 'download_drive_file(')

# Write refactored version
with open("backend.py", "w", encoding="utf-8") as f:
    f.write(content)

print(f"Refactored file: {len(content)} chars, {content.count(chr(10))} lines")
print("Backup saved to backend.py.backup")
print("✓ Removed duplicate imports")
print("✓ Added utility module imports")
print("✓ Removed duplicate function definitions")
print("✓ Updated function calls to use new names")
