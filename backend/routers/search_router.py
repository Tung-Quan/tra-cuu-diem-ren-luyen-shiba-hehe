"""Search router - endpoints for searching content."""
from typing import Optional
from fastapi import APIRouter, Query

from backend.models import SearchRequest, SearchResponse, SearchResult
from backend.services.search_service import SearchService

router = APIRouter(prefix="/api/search", tags=["Search"])


@router.get(
    "",
    response_model=SearchResponse,
    summary="Tìm kiếm trong dữ liệu đã index",
    description="""
    Tìm kiếm trong dữ liệu đã được index từ Google Sheets.
    
    Hỗ trợ:
    - Tìm kiếm fuzzy matching (Vietnamese với/không dấu)
    - Tìm kiếm exact match (chứa tất cả từ khóa)
    - Trích xuất snippet có highlight
    - Lấy danh sách links từ các cells
    """
)
async def search(
    query: str = Query(..., description="Từ khóa tìm kiếm", example="MSSV 2210001"),
    top_k: int = Query(20, ge=1, le=100, description="Số kết quả tối đa"),
    fuzz_threshold: int = Query(85, ge=0, le=100, description="Ngưỡng fuzzy matching"),
    exact: bool = Query(False, description="Tìm kiếm exact match"),
    follow_links: bool = Query(False, description="Tìm trong nội dung URLs (chưa implement)")
):
    """Search in indexed rows."""
    results, elapsed = SearchService.search_with_timing(
        query=query,
        top_k=top_k,
        fuzz_threshold=fuzz_threshold,
        exact=exact
    )
    
    return SearchResponse(
        results=[SearchResult(**r) for r in results],
        count=len(results),
        query=query,
        execution_time=elapsed
    )
