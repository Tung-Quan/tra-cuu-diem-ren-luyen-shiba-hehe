"""MySQL router - endpoints for MySQL search."""
import time
from fastapi import APIRouter, Query, HTTPException

from backend.config import db_mysql
from backend.models import MySQLSearchRequest, MySQLSearchResponse, MySQLActivity

router = APIRouter(prefix="/api/mysql", tags=["MySQL"])


@router.get(
    "/search",
    response_model=MySQLSearchResponse,
    summary="Tìm kiếm trong MySQL (nhanh hơn)",
    description="""
    Tìm kiếm trong bảng ctv_data với FULLTEXT index.
    
    Ưu điểm:
    - Nhanh hơn 10-100x so với fuzzy search
    - Hỗ trợ Vietnamese FULLTEXT
    - Scale tốt với dữ liệu lớn
    """
)
async def mysql_search(
    q: str = Query(..., description="Search query", example="MSSV"),
    limit: int = Query(100, ge=1, le=1000, description="Max results")
):
    """Search in MySQL ctv_data table."""
    if not db_mysql:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        start = time.time()
        results = db_mysql.search_ctv_data(q, limit=limit)
        elapsed_ms = (time.time() - start) * 1000
        
        activities = [
            MySQLActivity(
                id=r["id"],
                full_name=r["full_name"],
                unit=r["unit"],
                program=r["program"],
                search_text=r.get("search_text")
            )
            for r in results
        ]
        
        return MySQLSearchResponse(
            ok=True,
            data=activities,
            count=len(activities),
            execution_time_ms=elapsed_ms
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MySQL search failed: {str(e)}")


@router.get(
    "/count",
    summary="Đếm số records trong MySQL",
    description="Trả về tổng số records trong bảng ctv_data"
)
async def mysql_count():
    """Get total count of records in ctv_data."""
    if not db_mysql:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        count = db_mysql.count_ctv_data()
        return {"ok": True, "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Count failed: {str(e)}")


@router.get(
    "/links/count",
    summary="Đếm số links trong MySQL",
    description="Trả về tổng số links trong bảng links"
)
async def mysql_links_count():
    """Get total count of links in MySQL."""
    if not db_mysql:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        count = db_mysql.count_links()
        return {"ok": True, "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Count failed: {str(e)}")


@router.get(
    "/links/summary",
    summary="Lấy thống kê links trong MySQL",
    description="Thống kê về links đã sync vào MySQL"
)
async def mysql_links_summary():
    """Get MySQL links summary."""
    if not db_mysql:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        count = db_mysql.count_links()
        # Get sample links
        sample = db_mysql.get_links(limit=5)
        
        return {
            "ok": True,
            "total_links": count,
            "sample_links": sample
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")
