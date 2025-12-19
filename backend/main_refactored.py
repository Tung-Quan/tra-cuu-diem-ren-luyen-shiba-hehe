"""
Refactored main application with Swagger/OpenAPI documentation.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routers import search_router, mysql_router, links_router, admin_router
from backend.config import USE_DEEP, HAS_GSPREAD

# ============= FastAPI App with OpenAPI =============
app = FastAPI(
    title="CTV Link-aware Search API",
    description="""
## Tổng quan

API tìm kiếm thông minh cho hệ thống CTV, hỗ trợ:

- **Tìm kiếm fuzzy**: Tìm kiếm với Vietnamese có dấu/không dấu
- **MySQL FULLTEXT**: Tìm kiếm nhanh với database indexing
- **Link management**: Quản lý và tìm kiếm trong links
- **Google Sheets integration**: Sync dữ liệu từ Google Sheets

## Các tính năng chính

### Search
- Tìm kiếm trong dữ liệu đã index
- Hỗ trợ fuzzy matching với rapidfuzz
- Vietnamese text normalization
- Extract snippets với highlight

### MySQL
- FULLTEXT search (10-100x nhanh hơn)
- Vietnamese FULLTEXT index support
- Real-time search trong 318 activities

### Links
- Quản lý 637+ links từ Google Sheets
- Thêm links mới qua API
- Auto-sync vào MySQL
- Support Google Sheets gid extraction

### Admin
- Health check & system stats
- Rebuild index từ Google Sheets
- Sync data vào MySQL
- Deep scan cho rich-text links

## Authentication

Hiện tại API không yêu cầu authentication (CORS enabled cho mọi origin).

## Rate Limiting
    
    Enabled: 100 requests / minute / IP.
    """,
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "CTV Search Team",
        "email": "support@ctv-search.example.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    }
)

from backend.middleware.rate_limiter import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,  # 100 requests per minute per IP
    window_seconds=60
)

# ============= CORS =============
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Routers =============
app.include_router(search_router.router)
app.include_router(mysql_router.router)
app.include_router(links_router.router)
app.include_router(admin_router.router)

# ============= Static Files (Frontend) =============
# Check if frontend dist folder exists
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    # Mount static assets
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")
    
    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend for SPA routing."""
        # Skip API routes
        if full_path.startswith("api/") or full_path in ["docs", "redoc", "openapi.json"]:
            return {"error": "Not found"}
        
        # Serve index.html for all other routes
        index_file = FRONTEND_DIST / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "Frontend not built"}

# ============= Root Endpoint =============
@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="Thông tin cơ bản về API"
)
async def root():
    """Root endpoint with API info."""
    return {
        "name": "CTV Link-aware Search API",
        "version": "3.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "features": {
            "fuzzy_search": True,
            "mysql_fulltext": True,
            "link_management": True,
            "google_sheets_sync": HAS_GSPREAD,
            "deep_scan": USE_DEEP
        },
        "endpoints": {
            "search": "/api/search",
            "mysql": "/api/mysql",
            "links": "/api/links",
            "admin": "/api/admin"
        }
    }


# ============= Startup Event =============
@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    from backend.config import DATABASE_ROWS, SHEETS, debug_log as _dlog
    from backend.services.index_service import IndexService
    
    _dlog("[startup] Building initial index...")
    
    try:
        rows, sheets = IndexService.build_index(verbose=False, deep=USE_DEEP)
        DATABASE_ROWS.extend(rows)
        SHEETS.extend(sheets)
        _dlog(f"[startup] Index ready: {len(DATABASE_ROWS)} rows, {len(SHEETS)} sheets")
    except Exception as e:
        _dlog(f"[startup] Index build failed: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
