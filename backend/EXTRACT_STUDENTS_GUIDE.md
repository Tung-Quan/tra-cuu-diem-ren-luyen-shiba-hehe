# Hướng dẫn Extract Sinh viên vào Database

## Tổng quan
System giờ có khả năng extract thông tin sinh viên (Họ tên + MSSV) từ Google Sheets và lưu vào MySQL database để search nhanh.

## Cách sử dụng

### 1. Chuẩn bị Google Sheet
Sheet cần có format với headers:
- **HỌ VÀ TÊN** / **Họ và tên** / **Full Name** / **Name**
- **MSSV** / **Mã số sinh viên** / **Student ID** / **ID**
- **LỚP** / **Class** (optional)

Ví dụ:
```
STT | HỌ VÀ TÊN        | LỚP    | MSSV
1   | Nguyễn Văn A    | 21DTHB1| 2012345
2   | Trần Thị B      | 21DTHB2| 2012346
```

### 2. Extract qua API

#### Dry Run (xem trước kết quả)
```bash
curl "http://localhost:8000/api/admin/extract-students?spreadsheet_id=YOUR_SHEET_ID&dry_run=true"
```

#### Insert vào Database
```bash
curl -X POST "http://localhost:8000/api/admin/extract-students?spreadsheet_id=YOUR_SHEET_ID&dry_run=false"
```

#### Extract chỉ một số sheets cụ thể
```bash
curl -X POST "http://localhost:8000/api/admin/extract-students?spreadsheet_id=YOUR_SHEET_ID&sheet_names=Sheet1,Sheet2&dry_run=false"
```

### 3. Search sinh viên

#### Search bằng tên
```bash
curl "http://localhost:8000/api/mysql/students/search?q=Nguyễn"
```

Response:
```json
{
  "ok": true,
  "query": "Nguyễn",
  "count": 1,
  "students": [
    {
      "student_id": 1,
      "full_name": "Nguyễn Văn A",
      "mssv": "2012345",
      "links": [
        {
          "url": "https://docs.google.com/spreadsheets/d/...",
          "sheet": "Sheet1",
          "row": 5,
          "address": "A5"
        }
      ]
    }
  ],
  "elapsed_ms": 2.34
}
```

#### Search bằng MSSV
```bash
curl "http://localhost:8000/api/mysql/students/search?q=2012345"
```

#### Quick search (chỉ count links, nhanh hơn)
```bash
curl "http://localhost:8000/api/mysql/students/quick?q=Trần"
```

Response:
```json
{
  "ok": true,
  "students": [
    {
      "student_id": 2,
      "full_name": "Trần Thị B",
      "mssv": "2012346",
      "link_count": 3
    }
  ]
}
```

#### Get student by exact MSSV
```bash
curl "http://localhost:8000/api/mysql/students/2012345"
```

### 4. Kiểm tra thống kê database

```bash
curl "http://localhost:8000/api/admin/db-stats"
```

Response:
```json
{
  "ok": true,
  "students": 150,
  "links": 45,
  "connections": 320,
  "students_with_links": 145,
  "top_students": [
    {
      "full_name": "Nguyễn Văn A",
      "mssv": "2012345",
      "link_count": 15
    }
  ]
}
```

## Database Schema

### Table: `student`
- `student_id` (BIGINT, PK, AUTO_INCREMENT)
- `full_name` (VARCHAR(255), UNIQUE)
- `mssv` (VARCHAR(50))
- `search_name` (VARCHAR(255), GENERATED) - for accent-insensitive search
- `created_at` (TIMESTAMP)

### Table: `link`
- `link_id` (BIGINT, PK, AUTO_INCREMENT)
- `url` (TEXT)
- `url_hash` (BINARY(16), UNIQUE) - MD5 for deduplication
- `title` (VARCHAR(500))
- `kind` (VARCHAR(32))
- `gid` (VARCHAR(32))
- `created_at` (TIMESTAMP)

### Table: `student_link`
- `student_id` (BIGINT, FK)
- `link_id` (BIGINT, FK)
- `sheet_name` (VARCHAR(255))
- `row_number` (INT)
- `address` (VARCHAR(16)) - A1 notation
- `snippet` (VARCHAR(512))
- `created_at` (TIMESTAMP)
- PRIMARY KEY: (student_id, link_id, row_number)

## Features

✅ **Tự động nhận diện headers** - Không cần format cố định, hỗ trợ nhiều biến thể tên cột

✅ **Accent-insensitive search** - Tìm "Nguyen" sẽ match "Nguyễn"

✅ **Deduplication** - Tự động loại trừ duplicate URLs bằng MD5 hash

✅ **Batch insert** - Xử lý hàng nghìn records hiệu quả

✅ **Metadata tracking** - Lưu vị trí sheet/row/address của mỗi link

✅ **Fast search** - MySQL indexed search, < 5ms cho < 10k records

## Workflow

1. **Extract**: Admin chạy `/api/admin/extract-students` để scan sheets → insert DB
2. **Search**: Users query `/api/mysql/students/search?q=name_or_mssv`
3. **Results**: System trả về student info + tất cả links liên quan

## Notes

- Mỗi student được identify bởi `full_name` (UNIQUE constraint)
- Nếu insert duplicate name, MSSV sẽ được update
- Links được deduplicate bằng URL hash
- Search hỗ trợ cả partial match: "Nguyễn" → "Nguyễn Văn A", "Nguyễn Thị B"
