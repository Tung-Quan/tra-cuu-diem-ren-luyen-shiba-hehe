# 🚀 Backend Refactored - CTV Search API

## 📁 Cấu trúc mới

```
backend/
├── app.py                     # Entry point cho production
├── main_refactored.py         # FastAPI app với Swagger
├── config.py                  # Configuration & global state
├── models/                    # Pydantic models
│   └── __init__.py           # Request/Response models
├── routers/                   # API endpoints
│   ├── __init__.py
│   ├── search_router.py      # /api/search
│   ├── mysql_router.py       # /api/mysql
│   ├── links_router.py       # /api/links
│   └── admin_router.py       # /api/admin
├── services/                  # Business logic
│   ├── __init__.py
│   ├── search_service.py     # Search logic
│   └── index_service.py      # Index building
└── utils/                     # Utilities
    ├── text_processing.py
    ├── url_helpers.py
    ├── csv_helpers.py
    └── google_api.py
```

## 🔧 Chạy server

### Development (auto-reload)
```bash
cd backend
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
cd backend
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Direct run
```bash
python backend/main_refactored.py
```

## 📚 API Documentation

Sau khi start server, truy cập:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 🎯 API Endpoints

### Search
- `GET /api/search` - Tìm kiếm fuzzy trong database
- Query params: `query`, `top_k`, `fuzz_threshold`, `exact`, `follow_links`

### MySQL
- `GET /api/mysql/search` - Tìm kiếm FULLTEXT trong MySQL
- `GET /api/mysql/count` - Đếm số records
- `GET /api/mysql/links/count` - Đếm số links
- `GET /api/mysql/links/summary` - Thống kê links

### Links
- `POST /api/links` - Thêm link mới
- `GET /api/links` - Lấy danh sách links
- `GET /api/links/summary` - Thống kê links

### Admin
- `GET /api/admin/health` - Health check
- `POST /api/admin/rebuild` - Rebuild index
- `GET /api/admin/stats` - Chi tiết statistics
- `POST /api/admin/sync-mysql` - Sync vào MySQL

## 🔍 Ví dụ sử dụng

### Tìm kiếm cơ bản
```bash
curl "http://localhost:8000/api/search?query=MSSV%202210001&top_k=10"
```

### MySQL FULLTEXT search
```bash
curl "http://localhost:8000/api/mysql/search?q=hoạt%20động&limit=50"
```

### Thêm link mới
```bash
curl -X POST "http://localhost:8000/api/links?url=https://docs.google.com/spreadsheets/d/abc&sheet=HK2&row=10&col=1"
```

### Health check
```bash
curl "http://localhost:8000/api/admin/health"
```

### Rebuild index
```bash
curl -X POST "http://localhost:8000/api/admin/rebuild?verbose=true&deep=false"
```

## 🎨 Features

### ✅ Đã implement
- ✅ Modular architecture (routers, services, models)
- ✅ Pydantic models với validation
- ✅ OpenAPI/Swagger documentation
- ✅ CORS enabled
- ✅ Search service với fuzzy matching
- ✅ MySQL FULLTEXT search
- ✅ Link management (add/list)
- ✅ Admin endpoints (health, rebuild, sync)
- ✅ Vietnamese text processing
- ✅ Google Sheets integration

### 🔄 Cải tiến so với version cũ
1. **Clean Architecture**: Tách rõ routers, services, models
2. **Type Safety**: Pydantic models cho tất cả requests/responses
3. **Documentation**: Auto-generated Swagger với examples
4. **Maintainability**: Dễ dàng thêm endpoints mới
5. **Testing**: Dễ test từng service riêng biệt

## 📊 OpenAPI Schema

Swagger UI tự động generate documentation từ:
- Pydantic models (validation + schema)
- Router decorators (summary, description, tags)
- Query/Path parameters với Field descriptions
- Response models với examples

## 🧪 Testing

```bash
# Test search
curl "http://localhost:8000/api/search?query=test"

# Test health
curl "http://localhost:8000/api/admin/health"

# Open Swagger UI
open http://localhost:8000/docs
```

## 🔒 Security Notes

- CORS: Enabled cho tất cả origins (`allow_origins=["*"]`)
- Authentication: Chưa có (cần thêm nếu deploy public)
- Rate limiting: Chưa có (cần thêm nếu cần)

## 🚀 Next Steps

1. Add authentication (JWT/OAuth)
2. Add rate limiting
3. Add caching (Redis)
4. Add logging middleware
5. Add unit tests
6. Add integration tests
7. Add performance monitoring

## 📝 Migration từ backend.py cũ

File `backend.py` cũ vẫn hoạt động bình thường.

Để chuyển sang version mới:
1. Stop server cũ
2. Run: `python -m uvicorn backend.app:app --reload`
3. Truy cập: http://localhost:8000/docs
4. Test các endpoints
5. Update frontend nếu cần (API routes thay đổi)

## 💡 Tips

- Dùng `/docs` để test API interactively
- Dùng `/redoc` để đọc docs đẹp hơn
- Check `/api/admin/health` để verify services
- Dùng `POST /api/admin/rebuild` để refresh data từ Sheets
