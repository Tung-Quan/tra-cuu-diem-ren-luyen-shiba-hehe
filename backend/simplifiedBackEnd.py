# export_links_with_names.py
import re
import asyncio
import httpx
from bs4 import BeautifulSoup
import json
import os
from typing import List, Optional


EFAULT_SPREADSHEET_ID = os.environ.get(
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
