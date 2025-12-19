"""Pydantic models for API requests/responses."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============= Search Models =============
class SearchRequest(BaseModel):
    """Search request parameters."""
    query: str = Field(..., description="Từ khóa tìm kiếm", example="MSSV 2210001")
    top_k: int = Field(20, ge=1, le=100, description="Số kết quả trả về tối đa")
    fuzz_threshold: int = Field(85, ge=0, le=100, description="Ngưỡng fuzzy matching")
    exact: bool = Field(False, description="Tìm kiếm exact match (chứa tất cả từ)")
    follow_links: bool = Field(False, description="Tìm kiếm trong nội dung URLs")


class SearchResult(BaseModel):
    """Single search result."""
    sheet: str
    row: int
    snippet: str
    snippet_nodau: Optional[str] = None
    links: List[str] = []
    score: int
    url: Optional[str] = None


class SearchResponse(BaseModel):
    """Search response."""
    results: List[SearchResult]
    count: int
    query: str
    execution_time: Optional[float] = None


# ============= MySQL Models =============
class MySQLSearchRequest(BaseModel):
    """MySQL search request."""
    q: str = Field(..., description="Search query", example="MSSV")
    limit: int = Field(100, ge=1, le=1000, description="Max results")


class MySQLActivity(BaseModel):
    """MySQL activity record."""
    id: int
    full_name: str
    unit: str
    program: str
    search_text: Optional[str] = None


class MySQLSearchResponse(BaseModel):
    """MySQL search response."""
    ok: bool
    data: List[MySQLActivity]
    count: int
    execution_time_ms: float


# ============= Link Models =============
class AddLinkRequest(BaseModel):
    """Add link request."""
    url: str = Field(..., description="URL to add", example="https://docs.google.com/spreadsheets/d/abc123")
    sheet: str = Field(..., description="Sheet name", example="HỌC KỲ 2")
    row: int = Field(..., ge=1, description="Row number")
    col: int = Field(1, ge=1, description="Column number (1=A, 2=B...)")


class LinkRecord(BaseModel):
    """Link record."""
    url: str
    sheet: str
    row: int
    col: int
    address: str
    gid: Optional[str] = None
    sheet_name: Optional[str] = None


class AddLinkResponse(BaseModel):
    """Add link response."""
    ok: bool
    link: Optional[LinkRecord] = None
    total_links: int
    message: str
    error: Optional[str] = None


class LinksIndexResponse(BaseModel):
    """Links index response."""
    total: int
    urls: int
    links: List[LinkRecord]
    limit: int


# ============= Health & Stats Models =============
class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database_rows: int
    sheets: List[str]
    links: Dict[str, int]
    mysql_available: bool
    gspread_available: bool
    google_api_available: bool
    deep_scan: bool


class BuildStats(BaseModel):
    """Build statistics."""
    sheet: str
    size: str
    non_empty_cells: int
    value_http_cells: int
    formula_http_cells: int
    cells_with_links_extracted: int
    added_to_list_flat: int
    added_url_keys_map: int


class RebuildResponse(BaseModel):
    """Rebuild response."""
    ok: bool
    indexed_rows: int
    sheets: List[str]
    total_links: int
    unique_urls: int
    duration_seconds: float
    stats: List[BuildStats]


# ============= Preview Models =============
class TablePreview(BaseModel):
    """Table preview."""
    name: str
    rows: List[List[str]]


class PreviewResponse(BaseModel):
    """Preview response."""
    kind: str
    tables: List[TablePreview]
