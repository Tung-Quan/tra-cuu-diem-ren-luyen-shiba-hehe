"""Search router - endpoints for searching content."""
import time
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException

from backend.models import SearchResponse, SearchResult
try:
    from backend import db_mysql
except ImportError:
    import db_mysql

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="Tìm kiếm (Database)",
    description="""
    Tìm kiếm thông tin sinh viên và links từ Database MySQL.
    
    Microservice optimized for ~200 req/day.
    - Sử dụng MySQL backend
    - Stateless execution
    - Return format compatible with frontend
    """
)
def search(
    query: str = Query(..., description="Từ khóa tìm kiếm (Tên, MSSV)", example="2210001", min_length=2),
    top_k: int = Query(20, ge=1, le=100, description="Số kết quả tối đa"),
    fuzz_threshold: int = Query(85, ge=0, le=100, description="Ignored (DB uses LIKE)"),
    exact: bool = Query(False, description="Ignored (DB uses LIKE)"),
    follow_links: bool = Query(False, description="Ignored")
):
    """
    Perform search using MySQL database.
    Stateless and consistent.
    """
    start_time = time.time()
    
    try:
        # Search via DB
        # returns list of students with their links
        students = db_mysql.search_student_links(query, limit=top_k)
    except Exception as e:
        print(f"[Search Microservice] DB Error: {e}")
        # Fail gracefully or return empty
        return SearchResponse(
            results=[],
            count=0,
            query=query,
            execution_time=time.time() - start_time
        )

    results: List[SearchResult] = []
    
    for student in students:
        full_name = student.get("full_name", "Unknown")
        mssv = student.get("mssv", "")
        student_links = student.get("links", [])
        
        if not student_links:
            # Entry for student without links
            results.append(SearchResult(
                sheet="Student Info",
                row=0,
                snippet=f"{full_name} ({mssv})" if mssv else full_name,
                snippet_nodau=None,
                links=[],
                score=100,
                url=None
            ))
        else:
            # Flatten links
            for link in student_links:
                res_url = link.get("url")
                res_snippet = link.get("snippet") or f"{full_name} - {link.get('title') or 'Link'}"
                
                results.append(SearchResult(
                    sheet=link.get("sheet_name") or "Unknown",
                    row=link.get("row_number") or 0,
                    snippet=res_snippet,
                    snippet_nodau=None,
                    links=[res_url] if res_url else [],
                    score=100,
                    url=res_url
                ))
    
    # Slice to top_k matching the request
    filtered_results = results[:top_k]
    
    elapsed = time.time() - start_time
    
    return SearchResponse(
        results=filtered_results,
        count=len(filtered_results),
        query=query,
        execution_time=elapsed
    )
