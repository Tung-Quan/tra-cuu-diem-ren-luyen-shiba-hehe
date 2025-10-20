# MySQL CTV Integration - Hướng Dẫn Sử Dụng

## Tổng Quan

Hệ thống đã được tích hợp MySQL để lưu trữ và tìm kiếm dữ liệu CTV (Cộng Tác Viên) trực tiếp từ database thay vì phải fetch từ Google Sheets mỗi lần tìm kiếm.

### Lợi Ích
- ⚡ **Tốc độ**: Tìm kiếm instant từ MySQL thay vì HTTP requests
- 🔍 **Full-text search**: Hỗ trợ tìm kiếm tiếng Việt có dấu và không dấu
- 📊 **Scalable**: Xử lý được lượng dữ liệu lớn
- 🔒 **Reliable**: Dữ liệu được lưu trữ an toàn

## Cấu Trúc Database

### Database: `ctv_links_db`

#### Table: `ctv_data`
```sql
- id (INT, AUTO_INCREMENT, PRIMARY KEY)
- sheet_name (VARCHAR(255))          # Tên sheet gốc
- row_number (INT)                    # Số dòng trong sheet
- full_name (VARCHAR(500))            # Họ và tên CTV
- full_name_normalized (VARCHAR(500)) # Tên không dấu (cho search)
- mssv (VARCHAR(50))                  # Mã số sinh viên
- unit (TEXT)                         # Đơn vị
- program (TEXT)                      # Chương trình
- row_text (TEXT)                     # Toàn bộ text của dòng
- row_text_normalized (TEXT)          # Text không dấu (cho search)
- links (JSON)                        # Mảng links trong dòng
- created_at, updated_at (TIMESTAMP)
```

#### Indexes
- **FULLTEXT**: `full_name`, `full_name_normalized`, `row_text`, `row_text_normalized`
- **Regular**: `mssv`, `sheet_name`, `row_number`

## API Endpoints

### 1. Đồng Bộ Dữ Liệu

#### POST `/mysql/sync_ctv_data`
Đồng bộ dữ liệu từ Google Sheets (DATABASE_ROWS) lên MySQL.

**Query Parameters:**
- `clear_first` (bool, optional): Xóa dữ liệu cũ trước khi sync (default: false)

**Example:**
```powershell
Invoke-WebRequest -Method POST -Uri "http://localhost:8000/mysql/sync_ctv_data?clear_first=true"
```

**Response:**
```json
{
  "ok": true,
  "inserted": 344,
  "total_in_db": 344,
  "synced_from_memory": 344,
  "hint": "Nếu trích xuất tên/MSSV chưa đúng, có thể cần điều chỉnh logic parsing trong code"
}
```

### 2. Kiểm Tra Số Lượng

#### GET `/mysql/ctv/count`
Đếm số record CTV trong database.

**Example:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/count"
```

**Response:**
```json
{
  "ok": true,
  "count": 344
}
```

### 3. Tìm Kiếm Theo Tên

#### GET `/mysql/ctv/search_name`
Tìm CTV theo tên (hỗ trợ tiếng Việt có dấu và không dấu).

**Query Parameters:**
- `q` (string, required): Tên để tìm
- `limit` (int, optional): Số kết quả tối đa (default: 50)

**Example:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/search_name?q=nguyen&limit=5"
```

**Search Strategy:**
1. FULLTEXT search trên `full_name` và `full_name_normalized`
2. Nếu không có kết quả → LIKE search với pattern `%query%`

### 4. Tìm Kiếm Theo MSSV

#### GET `/mysql/ctv/search_mssv`
Tìm CTV theo mã số sinh viên.

**Query Parameters:**
- `mssv` (string, required): MSSV để tìm
- `limit` (int, optional): Số kết quả tối đa (default: 50)

**Example:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/search_mssv?mssv=2053801015035"
```

### 5. Tìm Kiếm Tổng Hợp

#### GET `/mysql/ctv/search`
Tìm kiếm thông minh: tự động phát hiện query là MSSV (số) hay tên (text).

**Query Parameters:**
- `q` (string, required): Từ khóa tìm kiếm
- `limit` (int, optional): Số kết quả tối đa (default: 50)

**Example:**
```powershell
# Tìm theo tên
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/search?q=nguyen"

# Tìm theo MSSV
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/search?q=2053801015035"
```

**Response:**
```json
{
  "ok": true,
  "query": "nguyen",
  "search_type": "fulltext",
  "results": [
    {
      "id": 83,
      "sheet_name": "HỌC KỲ 2",
      "row_number": 88,
      "full_name": "Hội Sinh viên trường",
      "mssv": "",
      "unit": "...",
      "program": "",
      "score": 4.0407395362854
    }
  ],
  "count": 5,
  "execution_time_ms": 65
}
```

### 6. Lấy Danh Sách Theo Sheet

#### GET `/mysql/ctv/by_sheet`
Lấy tất cả CTV trong một sheet cụ thể.

**Query Parameters:**
- `sheet` (string, required): Tên sheet
- `limit` (int, optional): Số kết quả tối đa (default: 100)

**Example:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/by_sheet?sheet=HỌC KỲ 2&limit=10"
```

## Workflow Sử Dụng

### Lần Đầu Tiên Setup

1. **Tạo database và tables:**
```powershell
cd backend
..\.venv\Scripts\python.exe setup_mysql.py
```

2. **Tạo table ctv_data (nếu chưa có):**
```powershell
..\.venv\Scripts\python.exe create_ctv_table.py
```

3. **Start backend server:**
```powershell
cd ..
.venv\Scripts\python.exe -m uvicorn backend.backend:app --reload --host 127.0.0.1 --port 8000
```

4. **Đồng bộ dữ liệu CTV:**
```powershell
Invoke-WebRequest -Method POST -Uri "http://localhost:8000/mysql/sync_ctv_data?clear_first=true"
```

### Sử Dụng Hàng Ngày

1. **Kiểm tra dữ liệu:**
```powershell
# Check count
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/count"
```

2. **Tìm kiếm:**
```powershell
# Tìm theo tên
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/search?q=nguyen&limit=10"

# Tìm theo MSSV
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/search_mssv?mssv=2053801015035"
```

3. **Update dữ liệu (khi có thay đổi từ Google Sheets):**
```powershell
# Restart backend để load dữ liệu mới từ Sheets
# Ctrl+C để stop server, sau đó start lại

# Sau đó sync lại
Invoke-WebRequest -Method POST -Uri "http://localhost:8000/mysql/sync_ctv_data?clear_first=true"
```

## Kết Nối Frontend

Frontend (Vite + React) đã được cấu hình proxy:

```typescript
// vite.config.ts
server: {
  port: 5173,
  proxy: {
    "/api": {
      target: "http://localhost:8000",
      changeOrigin: true,
    },
  },
}
```

### Sử dụng trong Frontend

```typescript
// Search CTV
const response = await fetch('/api/mysql/ctv/search?q=' + encodeURIComponent(query));
const data = await response.json();

if (data.ok) {
  console.log('Found', data.count, 'results');
  console.log(data.results);
}
```

### Start Frontend
```powershell
cd frontend
npm install  # Nếu chưa cài
npm run dev  # Start dev server
```

Truy cập: http://localhost:5173

## ⚠️ Lưu Ý Quan Trọng

### 1. Parsing Logic Cần Điều Chỉnh

Hiện tại logic parsing tự động trong `sync_ctv_data` endpoint **chưa hoạt động tốt**. Bạn cần:

1. **Kiểm tra structure của DATABASE_ROWS:**
```python
# Trong backend.py, thêm debug endpoint:
@app.get("/debug/sample_rows")
def debug_sample_rows():
    return {"sample": DATABASE_ROWS[:3]}
```

2. **Xác định vị trí chính xác của các cột:**
   - Cột nào chứa TÊN?
   - Cột nào chứa MSSV?
   - Cột nào chứa ĐƠN VỊ?
   - Cột nào chứa CHƯƠNG TRÌNH?

3. **Điều chỉnh parsing logic trong `backend.py`:**
```python
# Tìm function mysql_sync_ctv_data() trong backend.py
# Sửa logic parsing theo structure thực tế:

if len(cols) >= 5:
    full_name = str(cols[1]).strip()  # Ví dụ: cột thứ 2 là tên
    mssv = str(cols[2]).strip()       # Cột thứ 3 là MSSV
    unit = str(cols[3]).strip()       # Cột thứ 4 là đơn vị
    program = str(cols[4]).strip()    # Cột thứ 5 là chương trình
```

### 2. Vietnamese Text Search

- MySQL FULLTEXT search yêu cầu từ khóa tối thiểu 3-4 ký tự
- Hỗ trợ tìm kiếm cả có dấu và không dấu nhờ `full_name_normalized`
- Nếu FULLTEXT không tìm thấy → fallback sang LIKE search

### 3. Performance

- Với 344 records: search thường < 100ms
- FULLTEXT indexes đã được tạo sẵn
- Nếu dữ liệu lớn hơn 10,000 records → cân nhắc thêm indexes

## Testing & Debug

### 1. Kiểm tra dữ liệu đã sync
```powershell
# Lấy sample data từ sheet
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/by_sheet?sheet=HỌC KỲ 2&limit=5" | 
  Select-Object -ExpandProperty Content | 
  ConvertFrom-Json | 
  ConvertTo-Json -Depth 10
```

### 2. Test search với nhiều query khác nhau
```powershell
# Test tiếng Việt có dấu
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/search?q=Nguyễn"

# Test không dấu
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/search?q=nguyen"

# Test partial match
Invoke-WebRequest -Uri "http://localhost:8000/mysql/ctv/search?q=sinh viên"
```

### 3. Xem logs trong terminal
Server sẽ log các operations:
```
[mysql] Cleared 344 old CTV records
[mysql] Inserted 344 CTV records
```

## Troubleshooting

### Lỗi: "Table 'ctv_links_db.ctv_data' doesn't exist"
```powershell
cd backend
..\.venv\Scripts\python.exe create_ctv_table.py
```

### Lỗi: "MySQL module not available"
```powershell
pip install mysql-connector-python
```

### Search không trả về kết quả
1. Check data đã sync chưa: `GET /mysql/ctv/count`
2. Check parsing có đúng không: `GET /mysql/ctv/by_sheet?sheet=...&limit=5`
3. Điều chỉnh logic parsing trong `mysql_sync_ctv_data()`

### Frontend không kết nối được backend
1. Check backend đang chạy: `curl http://localhost:8000/health`
2. Check frontend proxy config trong `vite.config.ts`
3. Restart cả backend và frontend

## Next Steps

1. ✅ MySQL integration hoàn tất
2. ✅ CTV sync endpoints đã tạo
3. ✅ Search endpoints đã test
4. ⚠️ **TODO**: Điều chỉnh parsing logic để trích xuất đúng tên/MSSV
5. 🔄 **TODO**: Tích hợp search vào frontend UI
6. 🔄 **TODO**: Thêm pagination cho results lớn

---

📝 **Created**: 2025-10-19
🔧 **Status**: MySQL integration complete, parsing needs adjustment
