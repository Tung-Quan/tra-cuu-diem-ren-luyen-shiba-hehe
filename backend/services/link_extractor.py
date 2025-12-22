"""
Link Extractor Service - Extract links from sheets and process student data from linked documents.
"""
import re
import os
import io
from typing import List, Dict, Any, Optional, Tuple
from backend.config import DEFAULT_SPREADSHEET_ID, HAS_GSPREAD, debug_log as _dlog
from backend.utils.google_api import get_gspread_client, get_sheets_service, get_drive_service
from backend.db_mysql import batch_insert_student_links

# Import for file download
try:
    from googleapiclient.http import MediaIoBaseDownload
except ImportError:
    MediaIoBaseDownload = None


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
        Handles both:
        1. Cell-level hyperlinks (using =HYPERLINK or Insert Link)
        2. Rich text links (multiple links in one cell)
        3. Raw text URLs scannable via regex
        
        Returns: List of dicts with file_id, file_type, url, context, row, col
        """
        links = []
        
        # Method 1: Try to get formulas and rich text via API
        try:
            ss_id = worksheet.spreadsheet.id
            ws_title = worksheet.title
            
            sheets_service = get_sheets_service()
            if sheets_service:
                # Include textFormatRuns to detect multiple links in one cell
                result = sheets_service.spreadsheets().get(
                    spreadsheetId=ss_id,
                    ranges=[ws_title],
                    fields='sheets(data(rowData(values(hyperlink,formattedValue,textFormatRuns))))'
                ).execute()
                
                for sheet in result.get('sheets', []):
                    for data in sheet.get('data', []):
                        for row_idx, row_data in enumerate(data.get('rowData', [])):
                            for col_idx, cell in enumerate(row_data.get('values', [])):
                                cell_links = LinkExtractor._get_links_from_cell_object(
                                    cell, row_idx + 1, col_idx + 1
                                )
                                links.extend(cell_links)
                                
        except Exception as e:
            _dlog(f"[link_extractor] Error getting rich text data: {e}")
        
        # Method 2: Fallback - scan plain text for URLs if API failed or returned nothing
        # Note: If Method 1 worked but found 0 links, we might still want to scan text 
        # just in case there are raw URLs that aren't hyperlinked.
        # But to avoid duplicates, we typically rely on Method 1. 
        # However, if 'links' is empty, we definitely fallback.
        if not links:
            all_values = worksheet.get_all_values()
            for row_idx, row in enumerate(all_values):
                for col_idx, cell_text in enumerate(row):
                    if not cell_text:
                        continue
                    
                    found_links = LinkExtractor._get_links_from_text_scan(
                        cell_text, row_idx + 1, col_idx + 1
                    )
                    links.extend(found_links)
        
        _dlog(f"[link_extractor] Found {len(links)} links in sheet '{worksheet.title}'")
        return links

    @staticmethod
    def _get_links_from_cell_object(cell: Dict, row: int, col: int) -> List[Dict[str, Any]]:
        """Extract links from a cell object (API response)."""
        found = []
        formatted_val = cell.get('formattedValue', '')
        
        # 1. Check textFormatRuns (Rich Text - potentially multiple links)
        runs = cell.get('textFormatRuns', [])
        rich_links_found = False
        
        if runs:
            for i, run in enumerate(runs):
                uri = run.get('format', {}).get('link', {}).get('uri')
                if uri:
                    # Calculate segment text for context
                    start_idx = run.get('startIndex', 0)
                    
                    # End index is the start of the next run, or end of string
                    if i + 1 < len(runs):
                        end_idx = runs[i+1].get('startIndex')
                        # Note: If next run has no startIndex, it implies it follows immediately? 
                        # API quirk: 0 is omitted. Non-zero is present.
                        # Safely assume if key missing it might be 0 but that shouldn't happen for i>0
                        # Ideally we just take the slice.
                        if end_idx is None:
                             # This is edge case. Assume end of string or handle gracefully.
                             end_idx = len(formatted_val)
                    else:
                        end_idx = len(formatted_val)
                    
                    # Extract context
                    try:
                        segment_text = formatted_val[start_idx:end_idx]
                    except:
                        segment_text = formatted_val # Fallback
                        
                    info = LinkExtractor._parse_google_url(uri)
                    if info:
                        info['context'] = segment_text.strip()
                        info['row'] = row
                        info['col'] = col
                        found.append(info)
                        rich_links_found = True
        
        # 2. Check cell-level hyperlink (if no rich text links found)
        # Often if the whole cell is a link, textFormatRuns might logic varies, 
        # but 'hyperlink' field is reliable for simple cases.
        if not rich_links_found:
            uri = cell.get('hyperlink')
            if uri:
                info = LinkExtractor._parse_google_url(uri)
                if info:
                    info['context'] = formatted_val
                    info['row'] = row
                    info['col'] = col
                    found.append(info)
        
        return found

    @staticmethod
    def _get_links_from_text_scan(text: str, row: int, col: int) -> List[Dict[str, Any]]:
        """Scan plain text for multiple Google Drive URLs."""
        found = []
        if not text:
            return []
            
        # Combine patterns to find all potential links
        # We search for the ID part mostly, but regexes in _parse_google_url are specific.
        # Let's just find anything looking like a google url
        
        # We'll use a general scanner regex or iterate known patterns
        # Simpler: Split by whitespace/newline and check? Or findall?
        # Given the complexity of existing regexes, let's just use re.finditer on a broad pattern
        # or reuse the patterns.
        
        # Patterns from class
        patterns = [
            (LinkExtractor.SHEETS_PATTERN, 'sheets', "https://docs.google.com/spreadsheets/d/"),
            (LinkExtractor.DOCS_PATTERN, 'docs', "https://docs.google.com/document/d/"),
            (LinkExtractor.DRIVE_PATTERN, 'drive', "https://drive.google.com/file/d/")
        ]
        
        for pattern_re, ftype, base_url in patterns:
            for match in re.finditer(pattern_re, text):
                file_id = match.group(1)
                
                # Context is tricky in plain text scan (maybe the whole line?)
                # We'll use the whole cell text as context usually, or a snippet
                context = text[:100] + "..." if len(text) > 100 else text
                
                info = {
                    'file_id': file_id,
                    'file_type': ftype,
                    'url': f"{base_url}{file_id}",
                    'context': context,
                    'row': row,
                    'col': col
                }
                found.append(info)
                
        # Deduplicate by file_id to avoid same link matching multiple patterns (unlikely) 
        # or appearing multiple times? 
        # User might want multiple occurrences if context differs?
        # But here context is the same (whole cell). So dedupe.
        
        unique_found = []
        seen_ids = set()
        for item in found:
            if item['file_id'] not in seen_ids:
                unique_found.append(item)
                seen_ids.add(item['file_id'])
                
        return unique_found
    
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
                
                # If it's a Google Doc or Word Doc
                if mime_type == 'application/vnd.google-apps.document' or mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                    _dlog(f"[link_extractor] File {file_id} is Doc/Word, redirecting...")
                    return LinkExtractor.process_linked_doc(file_id, context)
                
                # If it's a Google Sheet
                if mime_type == 'application/vnd.google-apps.spreadsheet':
                    _dlog(f"[link_extractor] File {file_id} confirmed as Google Sheet")
                    # Continue to process as sheet
                
                # If it's an Excel file (.xlsx), download and process locally
                elif mime_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                    _dlog(f"[link_extractor] File {file_id} is Excel (.xlsx), downloading to temp directory...")
                    
                    # Check if MediaIoBaseDownload is available
                    if MediaIoBaseDownload is None:
                        _dlog("[link_extractor] googleapiclient not installed, cannot download files")
                        return []
                    
                    try:
                        # Ensure temp download directory exists
                        temp_dir = os.path.join(os.path.dirname(__file__), 'temp_download')
                        os.makedirs(temp_dir, exist_ok=True)
                        
                        temp_file_path = os.path.join(temp_dir, f"{file_id}.xlsx")
                        _dlog(f"[link_extractor] Downloading to: {temp_file_path}")
                        
                        request = drive_service.files().get_media(fileId=file_id)
                        with io.FileIO(temp_file_path, 'wb') as fh:
                            downloader = MediaIoBaseDownload(fh, request)
                            done = False
                            while not done:
                                status, done = downloader.next_chunk()
                                if status:
                                    _dlog(f"[link_extractor] Download progress: {int(status.progress() * 100)}%")
                        
                        _dlog(f"[link_extractor] Downloaded Excel file, processing locally...")
                        
                        # Process the Excel file using pandas and openpyxl
                        try:
                            import pandas as pd
                        except ImportError:
                            _dlog("[link_extractor] pandas not installed, cannot process Excel file")
                            return []
                        
                        all_records = []
                        try:
                            # Read all sheets from Excel file
                            with pd.ExcelFile(temp_file_path) as excel_file:
                                _dlog(f"[link_extractor] Found {len(excel_file.sheet_names)} sheets in Excel file")
                                
                                for sheet_name in excel_file.sheet_names:
                                    _dlog(f"[link_extractor] Processing sheet: {sheet_name}")
                                    # Read without treating first row as header to preserve all data
                                    df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
                                    
                                    # Convert DataFrame to list of lists (similar to gspread format)
                                    # Fill NaN values with empty strings
                                    sheet_data = df.fillna('').astype(str).values.tolist()
                                    
                                    # Create a mock worksheet object that StudentExtractor can work with
                                    class MockWorksheet:
                                        def __init__(self, data, title):
                                            self._data = data
                                            self.title = title
                                        
                                        def get_all_values(self):
                                            return self._data
                                    
                                    mock_ws = MockWorksheet(sheet_data, sheet_name)
                                    sheet_url = f"https://drive.google.com/file/d/{file_id}"
                                    
                                    records = StudentExtractor.extract_students_from_sheet(mock_ws, sheet_url)
                                    
                                    # Add context from parent sheet
                                    for rec in records:
                                        if context:
                                            rec['program'] = context
                                        rec['sheet'] = sheet_name  # Update sheet name
                                        rec['title'] = file_name
                                        rec['kind'] = 'excel'
                                    
                                    all_records.extend(records)
                            
                            _dlog(f"[link_extractor] Extracted {len(all_records)} students from Excel file")
                        
                        finally:
                            # Clean up downloaded file
                            try:
                                os.remove(temp_file_path)
                                _dlog(f"[link_extractor] Cleaned up temp file: {temp_file_path}")
                            except Exception as e:
                                _dlog(f"[link_extractor] Failed to delete temp file: {e}")
                        
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
                    rec['title'] = ss.title
                    rec['kind'] = 'google_sheet'
                
                all_records.extend(records)
            
            _dlog(f"[link_extractor] Extracted {len(all_records)} students from linked sheet {file_id}")
            return all_records
            
        except Exception as e:
            _dlog(f"[link_extractor] Error processing linked sheet {file_id}: {e}")
            return []
    
    @staticmethod
    def _extract_students_from_rows(rows_data: List[List[str]], url: str, title: str, context: str, kind: str) -> List[Dict[str, Any]]:
        """Helper to extract students from 2D array of strings."""
        from backend.services.student_extractor import StudentExtractor
        records = []
        name_col = None
        mssv_col = None
        class_col = None
        header_row_idx = None
        
        for idx, row in enumerate(rows_data[:5]):
            name_idx, mssv_idx, class_idx = StudentExtractor._find_header_indices(row)
            if name_idx is not None and mssv_idx is not None:
                name_col = name_idx
                mssv_col = mssv_idx
                class_col = class_idx
                header_row_idx = idx
                _dlog(f"[link_extractor] Found header at row {idx}: name_col={name_col}, mssv_col={mssv_col}")
                break
        
        if name_col is None or mssv_col is None:
            return []
            
        for row_idx in range(header_row_idx + 1, len(rows_data)):
            data_row = rows_data[row_idx]
            if len(data_row) <= max(name_col, mssv_col):
                continue
            
            raw_name = data_row[name_col] if name_col < len(data_row) else ""
            raw_mssv = data_row[mssv_col] if mssv_col < len(data_row) else ""
            raw_class = data_row[class_col] if class_col is not None and class_col < len(data_row) else ""
            
            full_name = StudentExtractor._clean_name(raw_name)
            mssv = StudentExtractor._clean_mssv(raw_mssv)
            
            if not full_name and not mssv:
                continue
            
            if full_name and re.search(r'h[oọ].*t[eê]n', full_name.lower()):
                break
            
            record = {
                "full_name": full_name or "Unknown",
                "mssv": mssv,
                "url": url,
                "title": title,
                "kind": kind,
                "sheet": title,
                "row": row_idx + 1,
                "address": f"Table row {row_idx + 1}",
                "snippet": f"{full_name or ''} - {mssv or ''} - {raw_class or ''}".strip(" -"),
                "class": raw_class or None,
                "program": context or title
            }
            records.append(record)
            
        return records

    @staticmethod
    def _process_word_file(file_id: str, file_name: str, context: str) -> List[Dict[str, Any]]:
        """Download and process Word (.docx) file locally."""
        from backend.utils.google_api import get_drive_service
        
        try:
            import docx
        except ImportError:
            _dlog("[link_extractor] python-docx not installed, cannot process Word file")
            return []
            
        drive_service = get_drive_service()
        if not drive_service:
            return []
            
        if MediaIoBaseDownload is None:
            _dlog("[link_extractor] googleapiclient not installed, cannot download files")
            return []
            
        try:
            # Download
            temp_dir = os.path.join(os.path.dirname(__file__), 'temp_download')
            os.makedirs(temp_dir, exist_ok=True)
            # Use only file_id for temp file name to avoid "File name too long" error on Linux
            temp_file_path = os.path.join(temp_dir, f"{file_id}.docx")
            
            _dlog(f"[link_extractor] Downloading Word file to: {temp_file_path}")
            
            request = drive_service.files().get_media(fileId=file_id)
            with io.FileIO(temp_file_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            # Process
            _dlog(f"[link_extractor] Processing Word file locally...")
            doc = docx.Document(temp_file_path)
            all_records = []
            
            doc_url = f"https://drive.google.com/file/d/{file_id}"
            
            for table in doc.tables:
                rows_data = []
                for row in table.rows:
                    # python-docx cell text might contain newlines, we strip them or join
                    row_cells = [cell.text.replace('\n', ' ').strip() for cell in row.cells]
                    rows_data.append(row_cells)
                
                records = LinkExtractor._extract_students_from_rows(
                    rows_data, doc_url, file_name, context, "word_docx"
                )
                all_records.extend(records)
                
            # Cleanup
            try:
                os.remove(temp_file_path)
            except:
                pass
                
            _dlog(f"[link_extractor] Extracted {len(all_records)} students from Word file {file_name}")
            return all_records
            
        except Exception as e:
            _dlog(f"[link_extractor] Error processing Word file {file_id}: {e}")
            try:
                if os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
            except:
                pass
            return []

    @staticmethod
    def process_linked_doc(file_id: str, context: str = "") -> List[Dict[str, Any]]:
        """
        Process a linked Google Doc (or Word Doc) to extract student data from tables.
        Reads tables and finds student data (HỌ VÀ TÊN, MSSV columns).
        """
        from backend.utils.google_api import get_docs_service
        
        # 1. Check file type via Drive API
        mime_type = ""
        file_name = "Untitled"
        
        try:
            from backend.utils.google_api import get_drive_service
            drive_service = get_drive_service()
            if drive_service:
                file_meta = drive_service.files().get(
                    fileId=file_id, 
                    fields='mimeType,name'
                ).execute()
                mime_type = file_meta.get('mimeType', '')
                file_name = file_meta.get('name', 'Untitled')
        except Exception as e:
            _dlog(f"[link_extractor] Warn: Cannot verify file type for {file_id}: {e}")

        # 2. Redirect if Word Doc
        if mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return LinkExtractor._process_word_file(file_id, file_name, context)

        # 3. Process as Google Doc
        docs_service = get_docs_service()
        if not docs_service:
            _dlog(f"[link_extractor] Docs API not available")
            return []
        
        try:
            # Check mime if we haven't already (or if it's not doc/word)
            if drive_service and mime_type and mime_type != 'application/vnd.google-apps.document':
                _dlog(f"[link_extractor] File {file_id} is {mime_type}, not a Google Doc. Skipping.")
                return []
            
            # Get document
            doc = docs_service.documents().get(documentId=file_id).execute()
            title = doc.get('title', 'Untitled')
            _dlog(f"[link_extractor] Processing Google Doc: {title} ({file_id})")
            
            # Extract tables from document
            content = doc.get('body', {}).get('content', [])
            all_records = []
            doc_url = f"https://docs.google.com/document/d/{file_id}"
            
            for element in content:
                if 'table' not in element:
                    continue
                
                table = element['table']
                table_rows = table.get('tableRows', [])
                
                rows_data = []
                for table_row in table_rows:
                    row_cells = []
                    for cell in table_row.get('tableCells', []):
                        cell_text = []
                        for content_elem in cell.get('content', []):
                            if 'paragraph' in content_elem:
                                for elem in content_elem['paragraph'].get('elements', []):
                                    if 'textRun' in elem:
                                        cell_text.append(elem['textRun'].get('content', ''))
                        
                        cell_value = ''.join(cell_text).strip()
                        row_cells.append(cell_value)
                    rows_data.append(row_cells)
                
                records = LinkExtractor._extract_students_from_rows(
                    rows_data, doc_url, title, context, "google_doc"
                )
                all_records.extend(records)
            
            _dlog(f"[link_extractor] Extracted {len(all_records)} students from Doc {file_id}")
            return all_records
            
        except Exception as e:
            error_str = str(e)
            if '404' in error_str:
                _dlog(f"[link_extractor] Doc {file_id} not found or not shared")
            elif '403' in error_str:
                _dlog(f"[link_extractor] No permission to access Doc {file_id}")
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
            row = link.get('row', '?')
            
            col = link.get('col', '?')
            
            _dlog(f"[link_extractor] Processing link at Row {row}, Col {col} - File ID: {file_id} (Type: {file_type})")
            
            if file_type == 'sheets':
                records = LinkExtractor.process_linked_sheet(file_id, context)
                # Inject main sheet info
                for rec in records:
                    rec['main_sheet'] = ss.title
                all_records.extend(records)
                sheets_processed += 1
            
            elif file_type == 'docs':
                records = LinkExtractor.process_linked_doc(file_id, context)
                # Inject main sheet info
                for rec in records:
                    rec['main_sheet'] = ss.title
                all_records.extend(records)
                docs_processed += 1
            
            else:
                _dlog(f"[link_extractor] Skipping drive file: {file_id} (Row {row}, Col {col})")
        
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
