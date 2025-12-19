-- =====================================================
-- Schema for CTV Link Management System
-- =====================================================

-- Database 1: Link Index (LINK_POOL data)
CREATE DATABASE IF NOT EXISTS ctv_links_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ctv_links_db;

-- Bảng lưu trữ các link đã index từ Google Sheets
CREATE TABLE IF NOT EXISTS links (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(2048) NOT NULL,
    sheet_name VARCHAR(255) DEFAULT '',
    row_number INT DEFAULT NULL,
    col_number INT DEFAULT NULL,
    address VARCHAR(20) DEFAULT '',  -- A1 notation (e.g., "B13")
    gid VARCHAR(100) DEFAULT NULL,   -- Google Sheet ID
    target_sheet_name VARCHAR(255) DEFAULT '',  -- Tên sheet được link tới (nếu là internal link)
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_url (url(255)),
    INDEX idx_sheet (sheet_name),
    INDEX idx_gid (gid),
    INDEX idx_address (address)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bảng lưu trữ dữ liệu CTV (Cộng Tác Viên) từ DATABASE_ROWS
CREATE TABLE IF NOT EXISTS ctv_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sheet_name VARCHAR(255) NOT NULL,
    row_number INT NOT NULL,
    full_name VARCHAR(255) DEFAULT '',          -- HỌ VÀ TÊN
    full_name_normalized VARCHAR(255) DEFAULT '', -- Tên không dấu (để search)
    mssv VARCHAR(50) DEFAULT '',                -- MSSV (Mã số sinh viên)
    unit VARCHAR(255) DEFAULT '',               -- ĐƠN VỊ
    program VARCHAR(500) DEFAULT '',            -- TÊN CHƯƠNG TRÌNH HOẠT ĐỘNG
    row_text TEXT,                              -- Full text của row (để search tổng hợp)
    row_text_normalized TEXT,                   -- Text không dấu
    links JSON,                                 -- Array of links từ row này
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_sheet (sheet_name),
    INDEX idx_mssv (mssv),
    INDEX idx_full_name (full_name),
    INDEX idx_full_name_normalized (full_name_normalized),
    INDEX idx_unit (unit),
    FULLTEXT idx_row_text (row_text),
    FULLTEXT idx_row_text_normalized (row_text_normalized),
    FULLTEXT idx_full_name_fulltext (full_name),
    FULLTEXT idx_full_name_normalized_fulltext (full_name_normalized)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Database 2: Fetched Content Storage
CREATE DATABASE IF NOT EXISTS ctv_content_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE ctv_content_db;

-- Bảng lưu nội dung đã fetch từ các URL
CREATE TABLE IF NOT EXISTS fetched_content (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(2048) NOT NULL UNIQUE,
    gid VARCHAR(100) DEFAULT NULL,
    content_type VARCHAR(100) DEFAULT 'text/csv',  -- csv, sheets, docs, excel
    raw_content LONGTEXT,           -- Nội dung gốc (CSV text, HTML, etc.)
    normalized_content LONGTEXT,    -- Nội dung đã chuẩn hóa tiếng Việt
    row_count INT DEFAULT 0,        -- Số dòng dữ liệu (nếu là bảng)
    status VARCHAR(50) DEFAULT 'ok',  -- ok, error, private, unsupported
    error_message TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_url (url(255)),
    INDEX idx_gid (gid),
    INDEX idx_status (status),
    INDEX idx_fetched_at (fetched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bảng lưu từng dòng dữ liệu đã parse (để search nhanh)
CREATE TABLE IF NOT EXISTS parsed_rows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    url VARCHAR(2048) NOT NULL,
    row_number INT NOT NULL,
    row_data JSON,                  -- Mảng values của row
    row_text TEXT,                  -- Text ghép lại từ row (để search)
    normalized_text TEXT,           -- Text đã bỏ dấu (để search không dấu)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_url (url(255)),
    INDEX idx_row_number (row_number),
    FULLTEXT idx_row_text (row_text),
    FULLTEXT idx_normalized_text (normalized_text)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bảng thống kê search queries
CREATE TABLE IF NOT EXISTS search_queries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    query TEXT NOT NULL,
    normalized_query TEXT,
    result_count INT DEFAULT 0,
    execution_time_ms INT DEFAULT 0,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_searched_at (searched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- Useful Views
-- =====================================================

USE ctv_links_db;

-- View: tổng hợp số lượng link theo sheet
CREATE OR REPLACE VIEW link_summary_by_sheet AS
SELECT 
    sheet_name,
    COUNT(*) as total_links,
    COUNT(DISTINCT url) as unique_urls,
    COUNT(DISTINCT gid) as unique_gids,
    MAX(updated_at) as last_updated
FROM links
GROUP BY sheet_name
ORDER BY total_links DESC;

USE ctv_content_db;

-- View: tổng hợp content đã fetch
CREATE OR REPLACE VIEW content_summary AS
SELECT 
    status,
    content_type,
    COUNT(*) as total_urls,
    SUM(row_count) as total_rows,
    MAX(fetched_at) as last_fetched
FROM fetched_content
GROUP BY status, content_type
ORDER BY total_urls DESC;

-- =====================================================
-- Sample Queries
-- =====================================================

-- USE ctv_links_db;
-- SELECT * FROM link_summary_by_sheet;
-- SELECT * FROM links WHERE sheet_name = 'CTV HK1' LIMIT 10;

-- USE ctv_content_db;
-- SELECT * FROM content_summary;
-- SELECT url, row_count, status, fetched_at FROM fetched_content ORDER BY fetched_at DESC LIMIT 20;
-- SELECT * FROM parsed_rows WHERE MATCH(row_text) AGAINST('Nguyễn' IN NATURAL LANGUAGE MODE) LIMIT 10;
