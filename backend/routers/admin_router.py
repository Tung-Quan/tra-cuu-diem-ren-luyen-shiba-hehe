"""Admin router - endpoints for system management."""
import time
from fastapi import APIRouter, Query
from typing import Optional, List

from backend.config import (
    DATABASE_ROWS,
    SHEETS,
    LINK_POOL,
    LINK_POOL_LIST,
    STATS,
    HAS_MYSQL,
    HAS_GSPREAD,
    HAS_GOOGLE_API,
    USE_DEEP
)
from backend.models import HealthResponse, RebuildResponse, BuildStats
from backend.services.index_service import IndexService
from backend.services.student_extractor import StudentExtractor
from backend.services.link_extractor import LinkExtractor

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Kiểm tra trạng thái hệ thống",
    description="Trả về thông tin về database, links, và các services có sẵn"
)
async def health():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        database_rows=len(DATABASE_ROWS),
        sheets=SHEETS,
        links={
            "total": len(LINK_POOL_LIST),
            "unique_urls": len(LINK_POOL)
        },
        mysql_available=HAS_MYSQL,
        gspread_available=HAS_GSPREAD,
        google_api_available=HAS_GOOGLE_API,
        deep_scan=USE_DEEP
    )


@router.post(
    "/rebuild",
    response_model=RebuildResponse,
    summary="Rebuild index từ Google Sheets",
    description="""
    Đọc lại dữ liệu từ Google Sheets và rebuild index.
    
    Options:
    - verbose: Enable chi tiết logging
    - deep: Enable deep scan để tìm rich-text links qua Sheets API
    """
)
async def rebuild_index(
    verbose: bool = Query(False, description="Enable verbose logging"),
    deep: bool = Query(False, description="Enable deep scan for rich-text links")
):
    """Rebuild the search index."""
    start = time.time()
    
    # Clear existing data
    DATABASE_ROWS.clear()
    SHEETS.clear()
    
    # Build index
    rows, sheets = IndexService.build_index(verbose=verbose, deep=deep)
    
    # Update globals
    DATABASE_ROWS.extend(rows)
    SHEETS.extend(sheets)
    
    duration = time.time() - start
    
    # Build stats
    stats = [BuildStats(**s) for s in STATS.get("per_sheet", [])]
    
    return RebuildResponse(
        ok=True,
        indexed_rows=len(DATABASE_ROWS),
        sheets=SHEETS,
        total_links=len(LINK_POOL_LIST),
        unique_urls=len(LINK_POOL),
        duration_seconds=duration,
        stats=stats
    )


@router.get(
    "/stats",
    summary="Lấy thống kê chi tiết",
    description="Thống kê chi tiết về index build, per-sheet stats"
)
async def get_stats():
    """Get detailed statistics."""
    return STATS


@router.post(
    "/sync-mysql",
    summary="Sync dữ liệu vào MySQL",
    description="Đồng bộ DATABASE_ROWS và LINK_POOL vào MySQL"
)
async def sync_mysql():
    """Sync data to MySQL."""
    from backend.config import db_mysql
    
    if not db_mysql:
        return {"ok": False, "error": "MySQL not available"}
    
    try:
        # Sync links
        db_mysql.sync_links(LINK_POOL_LIST)
        
        # Sync CTV data if available
        try:
            db_mysql.sync_ctv_data(DATABASE_ROWS)
        except Exception as e:
            pass  # CTV sync is optional
        
        return {
            "ok": True,
            "links_synced": len(LINK_POOL_LIST),
            "message": "Data synced to MySQL"
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.post(
    "/extract-students",
    summary="Extract sinh viên từ sheets vào MySQL",
    description="""
    Scan Google Sheets để tìm và extract thông tin sinh viên (Họ tên, MSSV).
    Tự động nhận diện các sheet có format:
    - HỌ VÀ TÊN | MSSV | LỚP
    - Lưu vào MySQL database để search được bằng tên hoặc MSSV
    """
)
async def extract_students(
    spreadsheet_id: Optional[str] = Query(None, description="Spreadsheet ID (default: from config)"),
    sheet_names: Optional[str] = Query(None, description="Comma-separated sheet names to process (default: all)"),
    dry_run: bool = Query(True, description="Dry run mode - chỉ show kết quả không insert DB")
):
    """Extract student data from sheets and populate database."""
    
    sheets_list = None
    if sheet_names:
        sheets_list = [s.strip() for s in sheet_names.split(",")]
    
    result = StudentExtractor.scan_and_populate_database(
        spreadsheet_id=spreadsheet_id,
        sheet_names=sheets_list,
        dry_run=dry_run
    )
    
    return result


@router.get(
    "/db-stats",
    summary="Thống kê MySQL database",
    description="Lấy thống kê về số sinh viên, links, connections trong MySQL"
)
async def get_db_stats():
    """Get database statistics."""
    from backend.db_mysql import get_stats, HAS_MYSQL
    
    if not HAS_MYSQL:
        return {"ok": False, "error": "MySQL not available"}
    
    try:
        stats = get_stats()
        return {"ok": True, **stats}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@router.get(
    "/config-info",
    summary="Hiển thị thông tin config",
    description="Hiển thị spreadsheet ID, service account email, và các config quan trọng"
)
async def get_config_info():
    """Get configuration information for debugging."""
    from backend.config import DEFAULT_SPREADSHEET_ID, GOOGLE_CREDS
    import os
    import json
    
    info = {
        "spreadsheet_id": DEFAULT_SPREADSHEET_ID or "NOT SET",
        "credentials_file": GOOGLE_CREDS,
        "credentials_exists": os.path.exists(GOOGLE_CREDS) if GOOGLE_CREDS else False,
        "service_account_email": None
    }
    
    # Try to read service account email from credentials
    if info["credentials_exists"]:
        try:
            with open(GOOGLE_CREDS, 'r') as f:
                creds_data = json.load(f)
                info["service_account_email"] = creds_data.get("client_email")
        except Exception as e:
            info["credentials_error"] = str(e)
    
    return info


@router.post(
    "/process-linked-sheets",
    summary="Process main sheet và extract students từ linked files",
    description="""
    Workflow hoàn chỉnh:
    1. Scan main sheet để tìm tất cả links (Google Sheets/Docs)
    2. Mở từng linked file
    3. Extract thông tin sinh viên (HỌ VÀ TÊN, MSSV)
    4. Lưu vào MySQL database
    
    Ví dụ: Main sheet chứa danh sách chương trình, mỗi chương trình có link đến file danh sách sinh viên
    """
)
async def process_linked_sheets(
    spreadsheet_id: Optional[str] = Query(None, description="Main spreadsheet ID (default: from config)"),
    sheet_names: Optional[str] = Query(None, description="Comma-separated sheet names to scan (default: all)"),
    dry_run: bool = Query(True, description="Dry run - chỉ show kết quả, không insert DB"),
    process_files: bool = Query(True, description="Process linked files or just list them")
):
    """Process main sheet and extract students from linked Google Sheets/Docs."""
    
    sheets_list = None
    if sheet_names:
        sheets_list = [s.strip() for s in sheet_names.split(",")]
    
    result = LinkExtractor.scan_main_sheet_and_process_links(
        spreadsheet_id=spreadsheet_id,
        sheet_names=sheets_list,
        dry_run=dry_run,
        process_linked_files=process_files
    )
    
    return result
