"""
Link Extractor Service - Extract links from sheets and process student data from linked documents.
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from backend.config import DEFAULT_SPREADSHEET_ID, HAS_GSPREAD, debug_log as _dlog
from backend.utils.google_api import get_gspread_client, get_sheets_service, get_drive_service
from backend.db_mysql import batch_insert_student_links


class LinkExtractor:
    """Extract links from main sheet and process student data from linked documents."""
    
    # Google file ID patterns
    SHEETS_PATTERN = r'docs\.google\.com/spreadsheets/d/([a-zA-Z0-9_-]+)'
    DOCS_PATTERN = r'docs\.google\.com/document/d/([a-zA-Z0-9_-]+)'
    DRIVE_PATTERN = r'drive\.google\.com/(?:file/d/|open\?id=)([a-zA-Z0-9_-]+)'
    
    @staticmethod
    def extract_links_from_sheet(worksheet) -> List[Dict[str, Any]]:
        """
        Extract all Google Drive links from a worksheet.
        
        Returns: [{
            "file_id": str,
            "file_type": "sheets" | "docs" | "drive",
            "url": str,
            "context": str (surrounding text)
        }]
        """
        links = []
        
        # Get all cell formulas (rich-text links are in formulas)
        try:
            # Method 1: Try to get formulas via API
            ss_id = worksheet.spreadsheet.id
            ws_title = worksheet.title
            
            sheets_service = get_sheets_service()
            if sheets_service:
                result = sheets_service.spreadsheets().get(
                    spreadsheetId=ss_id,
                    ranges=[ws_title],
                    fields='sheets(data(rowData(values(hyperlink,formattedValue))))'
                ).execute()
                
                for sheet in result.get('sheets', []):
                    for data in sheet.get('data', []):
                        for row_idx, row_data in enumerate(data.get('rowData', [])):
                            for col_idx, cell in enumerate(row_data.get('values', [])):
                                hyperlink = cell.get('hyperlink')
                                formatted_value = cell.get('formattedValue', '')
                                
                                if hyperlink:
                                    file_info = LinkExtractor._parse_google_url(hyperlink)
                                    if file_info:
                                        file_info['context'] = formatted_value
                                        file_info['row'] = row_idx + 1
                                        file_info['col'] = col_idx + 1
                                        links.append(file_info)
        except Exception as e:
            _dlog(f"[link_extractor] Error getting formulas: {e}")
        
        # Method 2: Fallback - scan plain text for URLs
        if not links:
            all_values = worksheet.get_all_values()
            for row_idx, row in enumerate(all_values):
                for col_idx, cell in enumerate(row):
                    if not cell:
                        continue
                    
                    # Find URLs in text
                    file_info = LinkExtractor._parse_google_url(cell)
                    if file_info:
                        file_info['context'] = cell[:100]
                        file_info['row'] = row_idx + 1
                        file_info['col'] = col_idx + 1
                        links.append(file_info)
        
        _dlog(f"[link_extractor] Found {len(links)} links in sheet '{worksheet.title}'")
        return links
    
    @staticmethod
    def _parse_google_url(url: str) -> Optional[Dict[str, Any]]:
        """Parse Google Drive/Docs/Sheets URL and extract file ID + type."""
        if not url or not isinstance(url, str):
            return None
        
        # Try Sheets
        match = re.search(LinkExtractor.SHEETS_PATTERN, url)
        if match:
            return {
                'file_id': match.group(1),
                'file_type': 'sheets',
                'url': f"https://docs.google.com/spreadsheets/d/{match.group(1)}"
            }
        
        # Try Docs
        match = re.search(LinkExtractor.DOCS_PATTERN, url)
        if match:
            return {
                'file_id': match.group(1),
                'file_type': 'docs',
                'url': f"https://docs.google.com/document/d/{match.group(1)}"
            }
        
        # Try Drive
        match = re.search(LinkExtractor.DRIVE_PATTERN, url)
        if match:
            return {
                'file_id': match.group(1),
                'file_type': 'drive',
                'url': f"https://drive.google.com/file/d/{match.group(1)}"
            }
        
        return None
    
    @staticmethod
    def process_linked_sheet(file_id: str, context: str = "") -> List[Dict[str, Any]]:
        """
        Process a linked Google Sheet to extract student data.
        Uses StudentExtractor to find student tables.
        """
        from backend.services.student_extractor import StudentExtractor
        from backend.utils.google_api import get_drive_service
        
        # First check if it's actually a Sheet using Drive API
        drive_service = get_drive_service()
        if drive_service:
            try:
                file_meta = drive_service.files().get(
                    fileId=file_id, 
                    fields='mimeType,name,permissions'
                ).execute()
                
                mime_type = file_meta.get('mimeType', '')
                file_name = file_meta.get('name', 'Unknown')
                
                _dlog(f"[link_extractor] File {file_id} ({file_name}): mime={mime_type}")
                
                # If it's a Google Doc
                if mime_type == 'application/vnd.google-apps.document':
                    _dlog(f"[link_extractor] File {file_id} is a Google Doc, redirecting...")
                    return LinkExtractor.process_linked_doc(file_id, context)
                
                # If it's a Google Sheet
                if mime_type == 'application/vnd.google-apps.spreadsheet':
                    _dlog(f"[link_extractor] File {file_id} confirmed as Google Sheet")
                    # Continue to process as sheet
                
                # If it's an Excel file (.xlsx), try to copy/convert to Google Sheets
                elif mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                    _dlog(f"[link_extractor] File {file_id} is Excel (.xlsx), attempting to copy as Google Sheet...")
                    try:
                        # Copy the file and convert to Google Sheets format
                        copied_file = drive_service.files().copy(
                            fileId=file_id,
                            body={
                                'name': f"[Converted] {file_name}",
                                'mimeType': 'application/vnd.google-apps.spreadsheet'
                            }
                        ).execute()
                        
                        new_file_id = copied_file['id']
                        _dlog(f"[link_extractor] Converted Excel to Google Sheet: {new_file_id}")
                        
                        # Process the converted sheet
                        client = get_gspread_client()
                        if not client:
                            return []
                        
                        ss = client.open_by_key(new_file_id)
                        base_url = f"https://docs.google.com/spreadsheets/d/{new_file_id}"
                        
                        all_records = []
                        for ws in ss.worksheets():
                            props = getattr(ws, "_properties", {}) or {}
                            gid = props.get("sheetId") or props.get("id")
                            sheet_url = f"{base_url}/edit#gid={gid}" if gid else base_url
                            
                            records = StudentExtractor.extract_students_from_sheet(ws, sheet_url)
                            
                            # Add context from parent sheet
                            for rec in records:
                                if context:
                                    rec['program'] = context
                            
                            all_records.extend(records)
                        
                        _dlog(f"[link_extractor] Extracted {len(all_records)} students from converted Excel file")
                        
                        # Optionally delete the converted file to clean up
                        try:
                            drive_service.files().delete(fileId=new_file_id).execute()
                            _dlog(f"[link_extractor] Cleaned up converted file {new_file_id}")
                        except:
                            pass
                        
                        return all_records
                        
                    except Exception as e:
                        _dlog(f"[link_extractor] Error converting Excel file {file_id}: {e}")
                        return []
                
                # If it's PDF, image, or other file type
                elif mime_type not in ['application/vnd.google-apps.spreadsheet']:
                    _dlog(f"[link_extractor] File {file_id} ({file_name}) is {mime_type}, skipping (not a Sheet/Doc)")
                    return []
                    
            except Exception as e:
                error_str = str(e)
                if '404' in error_str or 'not found' in error_str.lower():
                    _dlog(f"[link_extractor] File {file_id} not found or not shared with service account")
                    return []
                elif '403' in error_str or 'permission' in error_str.lower():
                    _dlog(f"[link_extractor] No permission to access file {file_id}")
                    return []
                else:
                    _dlog(f"[link_extractor] Could not check file type for {file_id}: {e}")
        
        try:
            client = get_gspread_client()
            if not client:
                return []
            
            ss = client.open_by_key(file_id)
            base_url = f"https://docs.google.com/spreadsheets/d/{file_id}"
            
            all_records = []
            for ws in ss.worksheets():
                props = getattr(ws, "_properties", {}) or {}
                gid = props.get("sheetId") or props.get("id")
                sheet_url = f"{base_url}/edit#gid={gid}" if gid else base_url
                
                records = StudentExtractor.extract_students_from_sheet(ws, sheet_url)
                
                # Add context from parent sheet
                for rec in records:
                    if context:
                        rec['program'] = context
                
                all_records.extend(records)
            
            _dlog(f"[link_extractor] Extracted {len(all_records)} students from linked sheet {file_id}")
            return all_records
            
        except Exception as e:
            _dlog(f"[link_extractor] Error processing linked sheet {file_id}: {e}")
            return []
    
    @staticmethod
    def process_linked_doc(file_id: str, context: str = "") -> List[Dict[str, Any]]:
        """
        Process a linked Google Doc to extract student data from tables.
        Reads tables and finds student data (HỌ VÀ TÊN, MSSV columns).
        """
        from backend.utils.google_api import get_docs_service
        from backend.services.student_extractor import StudentExtractor
        
        docs_service = get_docs_service()
        if not docs_service:
            _dlog(f"[link_extractor] Docs API not available")
            return []
        
        try:
            # Verify it's actually a Google Doc via Drive API first
            drive_service = get_drive_service()
            if drive_service:
                try:
                    file_meta = drive_service.files().get(
                        fileId=file_id,
                        fields='mimeType,name'
                    ).execute()
                    
                    mime_type = file_meta.get('mimeType', '')
                    if mime_type != 'application/vnd.google-apps.document':
                        _dlog(f"[link_extractor] File {file_id} is {mime_type}, not a Google Doc. Skipping.")
                        return []
                except Exception as e:
                    _dlog(f"[link_extractor] Cannot verify file type for {file_id}: {e}")
                    return []
            
            # Get document
            doc = docs_service.documents().get(documentId=file_id).execute()
            title = doc.get('title', 'Untitled')
            _dlog(f"[link_extractor] Processing Google Doc: {title} ({file_id})")
            
            # Extract tables from document
            content = doc.get('body', {}).get('content', [])
            records = []
            
            for element in content:
                if 'table' not in element:
                    continue
                
                table = element['table']
                table_rows = table.get('tableRows', [])
                
                if len(table_rows) < 2:  # Need at least header + 1 data row
                    continue
                
                # Convert table to 2D array
                rows_data = []
                for table_row in table_rows:
                    row_cells = []
                    for cell in table_row.get('tableCells', []):
                        # Extract text from cell
                        cell_text = []
                        for content_elem in cell.get('content', []):
                            if 'paragraph' in content_elem:
                                for elem in content_elem['paragraph'].get('elements', []):
                                    if 'textRun' in elem:
                                        text = elem['textRun'].get('content', '')
                                        cell_text.append(text)
                        
                        cell_value = ''.join(cell_text).strip()
                        row_cells.append(cell_value)
                    
                    rows_data.append(row_cells)
                
                # Try to find student data in this table
                # Look for header row with "HỌ VÀ TÊN", "MSSV" patterns
                name_col = None
                mssv_col = None
                class_col = None
                header_row_idx = None
                
                for idx, row in enumerate(rows_data[:5]):  # Check first 5 rows for header
                    name_idx, mssv_idx, class_idx = StudentExtractor._find_header_indices(row)
                    
                    if name_idx is not None and mssv_idx is not None:
                        name_col = name_idx
                        mssv_col = mssv_idx
                        class_col = class_idx
                        header_row_idx = idx
                        _dlog(f"[link_extractor] Found header at row {idx}: name_col={name_col}, mssv_col={mssv_col}")
                        break
                
                if name_col is None or mssv_col is None:
                    continue
                
                # Extract students from data rows
                doc_url = f"https://docs.google.com/document/d/{file_id}"
                
                for row_idx in range(header_row_idx + 1, len(rows_data)):
                    data_row = rows_data[row_idx]
                    
                    if len(data_row) <= max(name_col, mssv_col):
                        continue
                    
                    raw_name = data_row[name_col] if name_col < len(data_row) else ""
                    raw_mssv = data_row[mssv_col] if mssv_col < len(data_row) else ""
                    raw_class = data_row[class_col] if class_col is not None and class_col < len(data_row) else ""
                    
                    full_name = StudentExtractor._clean_name(raw_name)
                    mssv = StudentExtractor._clean_mssv(raw_mssv)
                    
                    # Skip empty rows
                    if not full_name and not mssv:
                        continue
                    
                    # Skip if looks like another header
                    if full_name and re.search(r'h[oọ].*t[eê]n', full_name.lower()):
                        break
                    
                    record = {
                        "full_name": full_name or "Unknown",
                        "mssv": mssv,
                        "url": doc_url,
                        "sheet": title,
                        "row": row_idx + 1,
                        "address": f"Table row {row_idx + 1}",
                        "snippet": f"{full_name or ''} - {mssv or ''} - {raw_class or ''}".strip(" -"),
                        "class": raw_class or None,
                        "program": context or title
                    }
                    
                    records.append(record)
            
            _dlog(f"[link_extractor] Extracted {len(records)} students from Doc {file_id}")
            return records
            
        except Exception as e:
            error_str = str(e)
            if '404' in error_str:
                _dlog(f"[link_extractor] Doc {file_id} not found or not shared")
            elif '403' in error_str:
                _dlog(f"[link_extractor] No permission to access Doc {file_id}")
            elif '400' in error_str:
                _dlog(f"[link_extractor] Doc {file_id} invalid or wrong file type (maybe PDF/image?)")
            else:
                _dlog(f"[link_extractor] Error processing Doc {file_id}: {e}")
            return []
    
    @staticmethod
    def scan_main_sheet_and_process_links(
        spreadsheet_id: Optional[str] = None,
        sheet_names: Optional[List[str]] = None,
        dry_run: bool = False,
        process_linked_files: bool = True
    ) -> Dict[str, Any]:
        """
        Main workflow:
        1. Scan main sheet for links
        2. For each link, determine type
        3. If Sheets: extract students
        4. If Docs: extract from tables (TODO)
        5. Populate database
        
        Returns: {
            "ok": bool,
            "main_sheet": str,
            "links_found": int,
            "sheets_processed": int,
            "docs_processed": int,
            "students_found": int,
            "students_inserted": int (if not dry_run),
            "records": List[Dict] (if dry_run)
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
            _dlog(f"[link_extractor] Opening main spreadsheet: {spreadsheet_id}")
            ss = client.open_by_key(spreadsheet_id)
            worksheets = ss.worksheets()
            _dlog(f"[link_extractor] Opened '{ss.title}' with {len(worksheets)} sheets")
        except Exception as e:
            return {"ok": False, "error": f"Cannot open spreadsheet: {e}"}
        
        # Filter sheets if specified
        if sheet_names:
            worksheets = [ws for ws in worksheets if ws.title in sheet_names]
        
        # Step 1: Extract all links from main sheet(s)
        all_links = []
        for ws in worksheets:
            links = LinkExtractor.extract_links_from_sheet(ws)
            all_links.extend(links)
        
        _dlog(f"[link_extractor] Total links found: {len(all_links)}")
        
        if not process_linked_files:
            return {
                "ok": True,
                "main_sheet": ss.title,
                "links_found": len(all_links),
                "links": all_links
            }
        
        # Step 2: Process each link
        all_records = []
        sheets_processed = 0
        docs_processed = 0
        
        for link in all_links:
            file_id = link['file_id']
            file_type = link['file_type']
            context = link.get('context', '')
            
            if file_type == 'sheets':
                records = LinkExtractor.process_linked_sheet(file_id, context)
                all_records.extend(records)
                sheets_processed += 1
            
            elif file_type == 'docs':
                records = LinkExtractor.process_linked_doc(file_id, context)
                all_records.extend(records)
                docs_processed += 1
            
            else:
                _dlog(f"[link_extractor] Skipping drive file: {file_id}")
        
        # Step 3: Populate database (if not dry_run)
        inserted = 0
        if not dry_run and all_records:
            inserted = batch_insert_student_links(all_records)
            _dlog(f"[link_extractor] Inserted {inserted} student-link records into database")
        
        result = {
            "ok": True,
            "main_sheet": ss.title,
            "links_found": len(all_links),
            "sheets_processed": sheets_processed,
            "docs_processed": docs_processed,
            "students_found": len(all_records),
        }
        
        if dry_run:
            result['records'] = all_records[:20]  # Sample only
            result['total_records'] = len(all_records)
        else:
            result['students_inserted'] = inserted
        
        return result
