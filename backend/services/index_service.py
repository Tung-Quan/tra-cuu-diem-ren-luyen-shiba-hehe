"""Index service - business logic for building index."""
import time
from typing import Any, Dict, List, Optional, Tuple
import re

from backend.config import (
    DEFAULT_SPREADSHEET_ID,
    DATABASE_ROWS,
    SHEETS,
    LINK_POOL,
    LINK_POOL_LIST,
    LINK_POOL_MAP,
    GSPREAD_SKIP_IDS,
    STATS,
    HAS_GSPREAD,
    debug_log as _dlog
)
from backend.utils.google_api import (
    get_gspread_client,
    get_sheets_service,
    deep_scan_all_sheets
)
from backend.utils.url_helpers import classify_google_url


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
    from backend.utils.url_helpers import URL_RE, clean_urls
    
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


class IndexService:
    """Service for building and managing search index."""
    
    @staticmethod
    def build_index(verbose: bool = False, deep: bool = False) -> Tuple[List[Dict[str, Any]], List[str]]:
        """
        Build index from DEFAULT_SPREADSHEET_ID.
        
        Args:
            verbose: Enable verbose logging
            deep: Enable deep scanning for rich-text links via Sheets API
            
        Returns:
            Tuple of (rows, sheets)
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
                _dlog(f"[index] Sheet '{title}' size = {nrows}x{ncols}")

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
