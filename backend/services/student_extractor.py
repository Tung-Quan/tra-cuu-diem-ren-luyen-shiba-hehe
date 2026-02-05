"""
Student Extractor Service - Extract student info from sheets and populate MySQL.
Handles various sheet formats with "HỌ VÀ TÊN", "MSSV" columns.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from backend.config import DEFAULT_SPREADSHEET_ID, HAS_GSPREAD, debug_log as _dlog
from backend.utils.google_api import get_gspread_client
from backend.db_mysql import (
    insert_student,
    insert_link, 
    link_student_to_url,
    batch_insert_student_links
)


class StudentExtractor:
    """Extract student data from sheets and populate database."""
    
    # Patterns để nhận diện header columns
    NAME_PATTERNS = [
        r"h[oọ]\s*v[aà]\s*t[eê]n",
        r"h[oọ].*t[eê]n",
        r"full\s*name",
        r"name",
    ]
    
    MSSV_PATTERNS = [
        r"mssv",
        r"m[aã]\s*s[oố].*sinh\s*vi[eê]n",
        r"student.*id",
        r"id",
    ]
    
    CLASS_PATTERNS = [
        r"l[oớ]p",
        r"class",
    ]
    
    @staticmethod
    def _normalize_header(header: str) -> str:
        """Normalize header for pattern matching."""
        return re.sub(r'\s+', ' ', str(header).lower().strip())
    
    @staticmethod
    def _find_header_indices(row: List[str]) -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Find column indices for NAME, MSSV, CLASS in a header row.
        
        Returns:
            (name_col_idx, mssv_col_idx, class_col_idx) or None if not found
        """
        name_idx = None
        mssv_idx = None
        class_idx = None
        
        for i, cell in enumerate(row):
            normalized = StudentExtractor._normalize_header(cell)
            
            # Check name patterns
            if name_idx is None:
                for pattern in StudentExtractor.NAME_PATTERNS:
                    if re.search(pattern, normalized, re.IGNORECASE):
                        name_idx = i
                        break
            
            # Check MSSV patterns
            if mssv_idx is None:
                for pattern in StudentExtractor.MSSV_PATTERNS:
                    if re.search(pattern, normalized, re.IGNORECASE):
                        mssv_idx = i
                        break
            
            # Check class patterns
            if class_idx is None:
                for pattern in StudentExtractor.CLASS_PATTERNS:
                    if re.search(pattern, normalized, re.IGNORECASE):
                        class_idx = i
                        break
        
        return name_idx, mssv_idx, class_idx
    
    @staticmethod
    def _clean_mssv(mssv: str) -> Optional[str]:
        """Clean and validate MSSV."""
        if not mssv:
            return None
        
        # Remove non-alphanumeric except spaces
        cleaned = re.sub(r'[^\w\s]', '', str(mssv).strip())
        cleaned = re.sub(r'\s+', '', cleaned)
        
        # MSSV usually 7-10 digits
        if cleaned and (cleaned.isdigit() or cleaned.isalnum()) and 5 <= len(cleaned) <= 15:
            return cleaned
        
        return None
    
    @staticmethod
    def _clean_name(name: str) -> Optional[str]:
        """Clean and validate student name."""
        if not name:
            return None
        
        # Remove extra spaces
        cleaned = re.sub(r'\s+', ' ', str(name).strip())
        
        # Name should have at least 3 characters and contain letters
        if len(cleaned) >= 3 and re.search(r'[a-zA-ZÀ-ỹ]', cleaned):
            return cleaned
        
        return None
    
    @staticmethod
    def extract_students_from_sheet(
        worksheet,
        sheet_url: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract student records from a worksheet.
        
        Returns:
            List of {full_name, mssv, url, sheet, row, address, snippet}
        """
        records = []
        
        try:
            values = worksheet.get_all_values()
        except Exception as e:
            _dlog(f"[extractor] Cannot read sheet {worksheet.title}: {e}")
            return records
        
        sheet_title = worksheet.title
        _dlog(f"[extractor] Processing sheet: {sheet_title} ({len(values)} rows)")
        
        # Scan for header rows
        for row_idx, row in enumerate(values):
            name_col, mssv_col, class_col = StudentExtractor._find_header_indices(row)
            
            # Found a valid header
            if name_col is not None and mssv_col is not None:
                _dlog(f"[extractor] Found header at row {row_idx + 1}: name_col={name_col}, mssv_col={mssv_col}, class_col={class_col}")
                
                # Extract data rows below header
                data_start = row_idx + 1
                for data_idx in range(data_start, len(values)):
                    data_row = values[data_idx]
                    
                    # Stop if we hit another header or empty section
                    # Removed arbitrary 200 limit to support larger files
                    # if data_idx - data_start > 200:  # Safety limit
                    #     break
                    
                    # Get name and MSSV
                    raw_name = data_row[name_col] if name_col < len(data_row) else ""
                    raw_mssv = data_row[mssv_col] if mssv_col < len(data_row) else ""
                    raw_class = data_row[class_col] if class_col is not None and class_col < len(data_row) else ""
                    
                    full_name = StudentExtractor._clean_name(raw_name)
                    mssv = StudentExtractor._clean_mssv(raw_mssv)
                    
                    # Skip if no valid data
                    if not full_name and not mssv:
                        continue
                    
                    # Skip if looks like header again
                    if full_name and re.search(r'h[oọ].*t[eê]n', full_name.lower()):
                        break
                    
                    # Create record
                    record = {
                        "full_name": full_name or "Unknown",
                        "mssv": mssv,
                        "url": sheet_url or "",
                        "sheet": sheet_title,
                        "row": data_idx + 1,
                        "address": f"A{data_idx + 1}",
                        "snippet": f"{full_name or ''} - {mssv or ''} - {raw_class or ''}".strip(" -"),
                        "class": raw_class or None
                    }
                    
                    records.append(record)
                
                _dlog(f"[extractor] Extracted {len(records)} students from header at row {row_idx + 1}")
        
        return records
    
    @staticmethod
    def scan_and_populate_database(
        spreadsheet_id: Optional[str] = None,
        sheet_names: Optional[List[str]] = None,
        dry_run: bool = False,
        scan_linked_sheets: bool = True
    ) -> Dict[str, Any]:
        """
        Scan spreadsheet, extract students, and populate database.
        
        Args:
            spreadsheet_id: Google Spreadsheet ID (default: from config)
            sheet_names: List of sheet names to process (default: all)
            dry_run: If True, only extract but don't insert to DB
            scan_linked_sheets: If True, also scan linked Google Sheets for student data
            
        Returns:
            {
                "ok": bool,
                "sheets_scanned": int,
                "students_found": int,
                "students_inserted": int,
                "records": List[Dict] (if dry_run),
                "linked_sheets_scanned": int (if scan_linked_sheets)
            }
        """
        if not HAS_GSPREAD:
            return {"ok": False, "error": "gspread not available"}
        
        spreadsheet_id = spreadsheet_id or DEFAULT_SPREADSHEET_ID
        if not spreadsheet_id:
            return {"ok": False, "error": "No spreadsheet ID provided"}
        
        client = get_gspread_client()
        if not client:
            return {"ok": False, "error": "Cannot get gspread client"}
        
        try:
            _dlog(f"[extractor] Attempting to open spreadsheet: {spreadsheet_id}")
            ss = client.open_by_key(spreadsheet_id)
            worksheets = ss.worksheets()
            _dlog(f"[extractor] Opened spreadsheet '{ss.title}' with {len(worksheets)} sheets")
        except Exception as e:
            error_msg = str(e)
            _dlog(f"[extractor] Error opening spreadsheet: {error_msg}")
            
            # Provide helpful error messages
            if "404" in error_msg or "not found" in error_msg.lower():
                return {
                    "ok": False, 
                    "error": f"Spreadsheet not found or not shared with service account. ID: {spreadsheet_id}",
                    "help": "Make sure the spreadsheet exists and is shared with your service account email"
                }
            elif "403" in error_msg or "permission" in error_msg.lower():
                return {
                    "ok": False,
                    "error": f"Permission denied. Spreadsheet not shared with service account. ID: {spreadsheet_id}",
                    "help": "Share the spreadsheet with the email in credentials.json"
                }
            else:
                return {"ok": False, "error": f"Cannot open spreadsheet: {error_msg}"}
        
        # Filter sheets if specified
        if sheet_names:
            worksheets = [ws for ws in worksheets if ws.title in sheet_names]
        
        # Build sheet URL
        base_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
        
        all_records = []
        sheets_scanned = 0
        total_found = 0
        total_inserted = 0
        
        for ws in worksheets:
            sheets_scanned += 1
            
            # Get sheet GID
            props = getattr(ws, "_properties", {}) or {}
            gid = props.get("sheetId") or props.get("id")
            sheet_url = f"{base_url}/edit#gid={gid}" if gid else base_url
            
            # Extract students
            records = StudentExtractor.extract_students_from_sheet(ws, sheet_url)
            
            _dlog(f"[extractor] Sheet '{ws.title}': found {len(records)} students")
            
            if dry_run:
                all_records.extend(records)
                total_found += len(records)
            else:
                # Insert immediately
                if records:
                    inserted = batch_insert_student_links(records)
                    total_inserted += inserted
                    total_found += len(records) # still track found count
        
        _dlog(f"[extractor] Total students found: {total_found} from {sheets_scanned} sheets")
        
        # Dry run - just return records
        if dry_run:
            return {
                "ok": True,
                "sheets_scanned": sheets_scanned,
                "students_found": total_found,
                "students_inserted": 0,
                "records": all_records
            }
        
        return {
            "ok": True,
            "sheets_scanned": sheets_scanned,
            "students_found": total_found,
            "students_inserted": total_inserted,
        }


if __name__ == "__main__":
    """Test extractor with dry run."""
    import json
    from backend.config import DEFAULT_SPREADSHEET_ID
    
    print("=" * 70)
    print("Student Extractor - Dry Run Test")
    print("=" * 70)
    
    if not DEFAULT_SPREADSHEET_ID:
        print("\n✗ No DEFAULT_SPREADSHEET_ID configured!")
        exit(1)
    
    print(f"\nSpreadsheet ID: {DEFAULT_SPREADSHEET_ID}")
    print("\nScanning sheets for student data...")
    
    result = StudentExtractor.scan_and_populate_database(dry_run=True)
    
    print("\n" + "=" * 70)
    print("RESULT")
    print("=" * 70)
    
    if result.get("ok"):
        print(f"\n✓ Sheets scanned: {result['sheets_scanned']}")
        print(f"✓ Students found: {result['students_found']}")
        
        if result.get("records"):
            print("\nSample records (first 10):")
            for i, rec in enumerate(result["records"][:10], 1):
                print(f"\n{i}. {rec['full_name']} (MSSV: {rec.get('mssv', 'N/A')})")
                print(f"   Sheet: {rec['sheet']}, Row: {rec['row']}")
                print(f"   Snippet: {rec['snippet']}")
    else:
        print(f"\n✗ Error: {result.get('error')}")
