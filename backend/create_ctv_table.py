#!/usr/bin/env python3
"""
Quick script to create the ctv_data table
"""
import mysql.connector

MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
}

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS ctv_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sheet_name VARCHAR(255) NOT NULL,
    row_number INT NOT NULL,
    full_name VARCHAR(255) DEFAULT '',
    full_name_normalized VARCHAR(255) DEFAULT '',
    mssv VARCHAR(50) DEFAULT '',
    unit VARCHAR(255) DEFAULT '',
    program VARCHAR(500) DEFAULT '',
    row_text TEXT,
    row_text_normalized TEXT,
    links JSON,
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

if __name__ == "__main__":
    print("Creating ctv_data table...")
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("USE ctv_links_db")
        cursor.execute(CREATE_TABLE_SQL)
        conn.commit()
        
        print("✓ Table ctv_data created successfully")
        
        cursor.execute("SHOW TABLES")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"\nTables in ctv_links_db: {', '.join(tables)}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error: {e}")
