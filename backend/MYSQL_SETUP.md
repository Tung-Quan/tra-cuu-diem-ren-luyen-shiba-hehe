# HƯỚNG DẪN SETUP MYSQL CHO CTV SYSTEM

## Bước 1: Cài đặt dependencies

```powershell
# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install MySQL connector
pip install mysql-connector-python

# Hoặc cài tất cả từ requirements
pip install -r backend\requirement.txt
```

## Bước 2: Khởi động MySQL Server

Đảm bảo MySQL đang chạy ở port 3306. Kiểm tra bằng:

```powershell
# Sử dụng mysqlsh hoặc mysql client
mysql -h localhost -P 3306 -u root -p
```

## Bước 3: Tạo databases và tables

**Cách 1: Chạy SQL file trực tiếp**

```powershell
# Từ thư mục backend
mysql -h localhost -P 3306 -u root -p < schema.sql
```

**Cách 2: Sử dụng API endpoint**

```powershell
# Start server trước
python backend\backend.py

# Sau đó gọi endpoint
curl http://localhost:8000/mysql/init_db -X POST
```

## Bước 4: Cấu hình MySQL credentials (nếu cần)

Tạo file `.env` trong thư mục backend:

```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
```

Hoặc set environment variables:

```powershell
$env:MYSQL_HOST="localhost"
$env:MYSQL_PORT="3306"
$env:MYSQL_USER="root"
$env:MYSQL_PASSWORD="your_password"
```

## Bước 5: Test kết nối

```powershell
# Test từ Python module
python backend\db_mysql.py

# Hoặc qua API
curl http://localhost:8000/mysql/test
```

## Bước 6: Sync dữ liệu lên MySQL

### 6.1. Sync links từ LINK_POOL

```powershell
# Sync toàn bộ links (giữ dữ liệu cũ)
curl http://localhost:8000/mysql/sync_links -X POST

# Xóa dữ liệu cũ trước khi sync
curl "http://localhost:8000/mysql/sync_links?clear_first=true" -X POST
```

### 6.2. Sync nội dung đã fetch

```powershell
# Sync 1 URL cụ thể
curl "http://localhost:8000/mysql/sync_content?url=https://docs.google.com/spreadsheets/d/..." -X POST

# Sync tất cả links (limit 50 đầu tiên)
curl "http://localhost:8000/mysql/sync_all_content?limit=50" -X POST
```

## Bước 7: Kiểm tra dữ liệu

### Qua API:

```powershell
# Đếm số links
curl http://localhost:8000/mysql/links/count

# Thống kê links theo sheet
curl http://localhost:8000/mysql/links/summary

# Thống kê content đã fetch
curl http://localhost:8000/mysql/content/summary

# Search trong MySQL
curl "http://localhost:8000/mysql/search?q=Nguyễn&limit=20"
```

### Qua MySQL client:

```sql
-- Kết nối vào MySQL
USE ctv_links_db;

-- Xem tổng số links
SELECT COUNT(*) FROM links;

-- Xem links theo sheet
SELECT * FROM link_summary_by_sheet;

-- Xem 10 links mới nhất
SELECT url, sheet_name, address, indexed_at 
FROM links 
ORDER BY indexed_at DESC 
LIMIT 10;

-- Chuyển sang database content
USE ctv_content_db;

-- Xem thống kê
SELECT * FROM content_summary;

-- Xem nội dung đã fetch
SELECT url, content_type, row_count, status, fetched_at
FROM fetched_content
ORDER BY fetched_at DESC
LIMIT 20;

-- Full-text search
SELECT url, row_number, row_text
FROM parsed_rows
WHERE MATCH(row_text) AGAINST('Nguyễn' IN NATURAL LANGUAGE MODE)
LIMIT 10;
```

## API Endpoints Summary

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/mysql/test` | GET | Kiểm tra kết nối MySQL |
| `/mysql/init_db` | POST | Tạo databases từ schema.sql |
| `/mysql/sync_links` | POST | Sync LINK_POOL lên MySQL |
| `/mysql/links/count` | GET | Đếm số links trong DB |
| `/mysql/links/summary` | GET | Thống kê links theo sheet |
| `/mysql/sync_content` | POST | Fetch và sync 1 URL |
| `/mysql/sync_all_content` | POST | Sync tất cả links (với limit) |
| `/mysql/content/summary` | GET | Thống kê content đã fetch |
| `/mysql/search` | GET | Full-text search trong MySQL |

## Troubleshooting

### Lỗi: "MySQL module not available"
```powershell
pip install mysql-connector-python
```

### Lỗi: "Access denied for user"
Kiểm tra username/password trong config hoặc environment variables.

### Lỗi: "Unknown database"
Chạy lại `schema.sql` hoặc gọi `/mysql/init_db`

### Lỗi: "Can't connect to MySQL server"
- Kiểm tra MySQL server đang chạy
- Kiểm tra port (mặc định 3306)
- Kiểm tra firewall

## Performance Tips

1. **Index optimization**: Schema đã có indexes cho url, sheet_name, gid
2. **Batch insert**: Sử dụng `sync_all_content` với limit hợp lý (50-100)
3. **Full-text search**: MySQL FULLTEXT index cho row_text và normalized_text
4. **Memory**: parsed_rows table có thể lớn, cân nhắc partition nếu có hàng triệu rows

## Backup & Restore

```powershell
# Backup
mysqldump -u root -p ctv_links_db > backup_links.sql
mysqldump -u root -p ctv_content_db > backup_content.sql

# Restore
mysql -u root -p ctv_links_db < backup_links.sql
mysql -u root -p ctv_content_db < backup_content.sql
```
