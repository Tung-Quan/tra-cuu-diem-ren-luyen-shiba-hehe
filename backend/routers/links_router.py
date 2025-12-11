"""Links router - endpoints for managing links."""
from typing import Optional
from fastapi import APIRouter, Query, HTTPException

from backend.config import LINK_POOL, LINK_POOL_LIST, db_mysql, debug_log as _dlog
from backend.models import AddLinkRequest, AddLinkResponse, LinkRecord, LinksIndexResponse
from backend.utils.url_helpers import extract_gid_from_url

router = APIRouter(prefix="/api/links", tags=["Links"])


def _a1_addr(row: int, col: int) -> str:
    """Convert row/col to A1 notation."""
    COL_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    c = col
    label = ""
    while c:
        c, rem = divmod(c - 1, 26)
        label = COL_LETTERS[rem] + label
    return f"{label}{row}"


@router.post(
    "",
    response_model=AddLinkResponse,
    summary="Thêm link mới",
    description="""
    Thêm một link mới vào hệ thống.
    
    Link sẽ được:
    - Thêm vào LINK_POOL và LINK_POOL_LIST trong memory
    - Sync vào MySQL (nếu available)
    - Có thể tìm kiếm qua /search với follow_links=true
    """
)
async def add_link(
    url: str = Query(..., description="URL to add"),
    sheet: str = Query(..., description="Sheet name"),
    row: int = Query(..., ge=1, description="Row number"),
    col: int = Query(1, ge=1, description="Column number")
):
    """Add a new link to the system."""
    try:
        # Validate URL
        if not url or not url.startswith("http"):
            raise HTTPException(status_code=400, detail="URL must start with http:// or https://")
        
        # Extract gid if Google Sheets
        gid = extract_gid_from_url(url)
        
        # Create address
        address = _a1_addr(row, col)
        
        # Create link record
        link_record = {
            "url": url,
            "sheet": sheet,
            "row": row,
            "col": col,
            "address": address,
            "gid": gid,
            "sheet_name": ""
        }
        
        # Add to LINK_POOL_LIST
        LINK_POOL_LIST.append(link_record)
        
        # Add to LINK_POOL
        LINK_POOL.setdefault(url, []).append({
            "sheet": sheet,
            "row": row,
            "col": col,
            "address": address,
            **({"sheet_gid": gid} if gid else {})
        })
        
        # Sync to MySQL if available
        if db_mysql:
            try:
                db_mysql.insert_links_batch([link_record])
                _dlog(f"[add_link] Synced to MySQL: {url}")
            except Exception as e:
                _dlog(f"[add_link] MySQL sync failed: {e}")
        
        return AddLinkResponse(
            ok=True,
            link=LinkRecord(**link_record),
            total_links=len(LINK_POOL_LIST),
            message=f"Link added successfully at {sheet}!{address}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        _dlog(f"[add_link] Error: {e}")
        return AddLinkResponse(
            ok=False,
            link=None,
            total_links=len(LINK_POOL_LIST),
            message="Failed to add link",
            error=str(e)
        )


@router.get(
    "",
    response_model=LinksIndexResponse,
    summary="Lấy danh sách links đã index",
    description="Trả về danh sách tất cả links trong LINK_POOL_LIST"
)
async def get_links(
    limit: int = Query(100, ge=1, le=10000, description="Số links tối đa")
):
    """Get indexed links."""
    links = LINK_POOL_LIST[:limit] if limit else LINK_POOL_LIST
    
    return LinksIndexResponse(
        total=len(LINK_POOL_LIST),
        urls=len(LINK_POOL),
        links=[LinkRecord(**link) for link in links],
        limit=limit
    )


@router.get(
    "/summary",
    summary="Lấy thống kê links",
    description="Thống kê tổng quan về links đã index"
)
async def get_links_summary():
    """Get links summary."""
    return {
        "total_links": len(LINK_POOL_LIST),
        "unique_urls": len(LINK_POOL),
        "sample_links": LINK_POOL_LIST[:5]
    }
