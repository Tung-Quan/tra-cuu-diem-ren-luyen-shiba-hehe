"""MySQL router - endpoints for MySQL search."""
import time
from typing import List, Optional
from fastapi import APIRouter, Query, Path, HTTPException

from backend.config import db_mysql
from backend.models import MySQLSearchRequest, MySQLSearchResponse, MySQLActivity
from backend.db_mysql import (
    search_student_links,
    quick_search,
    get_student_links_by_mssv,
    get_stats,
    HAS_MYSQL
)

router = APIRouter(prefix="/api/mysql", tags=["MySQL"])


@router.get(
    "/search",
    summary="Tìm kiếm sinh viên trong MySQL",
    description="""
    Tìm kiếm sinh viên theo tên hoặc MSSV, trả về danh sách sinh viên và links.
    
    Alias cho /students/search để backward compatibility.
    """
)
def mysql_search(
    q: str = Query(..., description="Search query", example="Nguyễn"),
    limit: int = Query(50, ge=1, le=100, description="Max results")
):
    """Search students by name or MSSV - alias for /students/search."""
    if not HAS_MYSQL:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        start = time.time()
        results = search_student_links(q, limit=limit)
        elapsed_ms = (time.time() - start) * 1000
        
        return {
            "ok": True,
            "query": q,
            "count": len(results),
            "results": results,
            "execution_time_ms": round(elapsed_ms, 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MySQL search failed: {str(e)}")


@router.get(
    "/stats",
    summary="Thống kê database MySQL",
    description="Lấy thống kê tổng quan về students, links, connections"
)
def mysql_stats():
    """Get MySQL database statistics."""
    if not HAS_MYSQL:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        stats = get_stats()
        return {
            "ok": True,
            **stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats failed: {str(e)}")


@router.get(
    "/students/search",
    summary="Tìm sinh viên theo tên hoặc MSSV",
    description="""
    Tìm sinh viên trong database theo tên hoặc MSSV, trả về danh sách links.
    
    Ví dụ:
    - /api/mysql/students/search?q=Nguyễn Văn A
    - /api/mysql/students/search?q=2012345
    """
)
def search_students(
    q: str = Query(..., description="Tên hoặc MSSV sinh viên", example="Nguyễn"),
    limit: int = Query(50, ge=1, le=100, description="Số kết quả tối đa")
):
    """Search students by name or MSSV."""
    if not HAS_MYSQL:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        start = time.time()
        results = search_student_links(q, limit=limit)
        elapsed_ms = (time.time() - start) * 1000
        
        return {
            "ok": True,
            "query": q,
            "count": len(results),
            "results": results,
            "execution_time_ms": round(elapsed_ms, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get(
    "/students/quick",
    summary="Quick search sinh viên (chỉ count links)",
    description="Tìm nhanh sinh viên, chỉ trả về thông tin cơ bản + số lượng links"
)
def quick_search_students(
    q: str = Query(..., description="Tên hoặc MSSV sinh viên", example="Trần"),
    limit: int = Query(20, ge=1, le=50, description="Số kết quả tối đa")
):
    """Quick search students - returns only student info + link count."""
    if not HAS_MYSQL:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        start = time.time()
        results = quick_search(q, limit=limit)
        elapsed_ms = (time.time() - start) * 1000
        
        return {
            "ok": True,
            "query": q,
            "count": len(results),
            "results": results,
            "execution_time_ms": round(elapsed_ms, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quick search failed: {str(e)}")


@router.get(
    "/students/{mssv}",
    summary="Lấy thông tin sinh viên theo MSSV (exact)",
    description="Lấy tất cả links của sinh viên theo MSSV (exact match)"
)
def get_student_by_mssv(
    mssv: str = Path(..., description="MSSV của sinh viên", example="2012345")
):
    """Get student by exact MSSV."""
    if not HAS_MYSQL:
        raise HTTPException(status_code=503, detail="MySQL not available")
    
    try:
        result = get_student_links_by_mssv(mssv)
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Student with MSSV {mssv} not found")
        
        return {
            "ok": True,
            "student": result
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")
