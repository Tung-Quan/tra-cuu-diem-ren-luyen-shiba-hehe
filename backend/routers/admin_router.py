"""Admin router - endpoints for system management."""
import time
from fastapi import APIRouter, Query

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
