# db_mysql.py — MySQL connection and operations for CTV system
import os
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
    HAS_MYSQL = True
except ImportError:
    HAS_MYSQL = False
    MySQLError = Exception  # type: ignore


# =========================
# Configuration
# =========================
MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "charset": "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "autocommit": False,
}

LINKS_DB = "ctv_links_db"
CONTENT_DB = "ctv_content_db"


# =========================
# Connection Management
# =========================
@contextmanager
def get_db_connection(database: Optional[str] = None):
    """
    Context manager để tạo MySQL connection.
    Usage:
        with get_db_connection(LINKS_DB) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
    """
    if not HAS_MYSQL:
        raise ImportError("mysql-connector-python not installed. Run: pip install mysql-connector-python")
    
    config = MYSQL_CONFIG.copy()
    if database:
        config["database"] = database
    
    conn = None
    try:
        conn = mysql.connector.connect(**config)
        yield conn
    except MySQLError as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn and conn.is_connected():
            conn.close()


def test_connection() -> Dict[str, Any]:
    """Test MySQL connection and return server info."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION(), NOW()")
            version, now = cursor.fetchone()
            cursor.close()
            return {
                "ok": True,
                "version": version,
                "server_time": str(now),
                "config": {k: v for k, v in MYSQL_CONFIG.items() if k != "password"}
            }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# =========================
# Links Database Operations
# =========================
def insert_links_batch(links: List[Dict[str, Any]]) -> Tuple[int, int]:
    """
    Insert hoặc update batch links vào ctv_links_db.links.
    Returns: (inserted_count, updated_count)
    """
    if not links:
        return 0, 0
    
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor()
        
        # Sử dụng INSERT ... ON DUPLICATE KEY UPDATE
        # (Tuy nhiên table links không có UNIQUE constraint trên url, nên sẽ luôn insert mới)
        # Để tránh duplicate, ta có thể check trước hoặc thêm UNIQUE index
        
        sql = """
            INSERT INTO links 
            (url, sheet_name, row_number, col_number, address, gid, target_sheet_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        values = []
        for link in links:
            values.append((
                link.get("url", "")[:2048],
                link.get("sheet", "")[:255],
                link.get("row") or None,
                link.get("col") or None,
                link.get("address", "")[:20],
                link.get("gid", "")[:100] if link.get("gid") else None,
                link.get("sheet_name", "")[:255],
            ))
        
        cursor.executemany(sql, values)
        conn.commit()
        inserted = cursor.rowcount
        cursor.close()
        
        return inserted, 0  # Chưa implement update logic


def clear_links_table() -> int:
    """Xóa toàn bộ dữ liệu trong bảng links. Returns: deleted count."""
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM links")
        conn.commit()
        deleted = cursor.rowcount
        cursor.close()
        return deleted


def get_links_count() -> int:
    """Đếm số lượng links trong database."""
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM links")
        count = cursor.fetchone()[0]
        cursor.close()
        return count


def get_link_summary_by_sheet() -> List[Dict[str, Any]]:
    """Lấy thống kê links theo sheet."""
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM link_summary_by_sheet")
        rows = cursor.fetchall()
        cursor.close()
        return rows


# =========================
# CTV Data Operations (DATABASE_ROWS)
# =========================
def insert_ctv_data_batch(ctv_records: List[Dict[str, Any]]) -> int:
    """
    Insert batch CTV data records vào ctv_links_db.ctv_data.
    ctv_records: [{
        "sheet": str, "row": int, "full_name": str, "mssv": str,
        "unit": str, "program": str, "row_text": str, "links": [...]
    }]
    Returns: inserted count
    """
    if not ctv_records:
        return 0
    
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO ctv_data 
            (sheet_name, row_number, full_name, full_name_normalized, mssv, 
             unit, program, row_text, row_text_normalized, links)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = []
        for rec in ctv_records:
            values.append((
                rec.get("sheet", "")[:255],
                rec.get("row", 0),
                rec.get("full_name", "")[:255],
                rec.get("full_name_normalized", "")[:255],
                rec.get("mssv", "")[:50],
                rec.get("unit", "")[:255],
                rec.get("program", "")[:500],
                rec.get("row_text", ""),
                rec.get("row_text_normalized", ""),
                json.dumps(rec.get("links", []), ensure_ascii=False),
            ))
        
        cursor.executemany(sql, values)
        conn.commit()
        inserted = cursor.rowcount
        cursor.close()
        
        return inserted


def clear_ctv_data_table() -> int:
    """Xóa toàn bộ dữ liệu trong bảng ctv_data."""
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ctv_data")
        conn.commit()
        deleted = cursor.rowcount
        cursor.close()
        return deleted


def get_ctv_data_count() -> int:
    """Đếm số records trong ctv_data."""
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ctv_data")
        count = cursor.fetchone()[0]
        cursor.close()
        return count


def search_ctv_by_name(name: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Tìm CTV theo tên (có dấu hoặc không dấu).
    Returns: list of matching records
    """
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor(dictionary=True)
        
        # Thử full-text search trước (có dấu)
        sql_fulltext = """
            SELECT id, sheet_name, row_number, full_name, mssv, unit, program,
                   MATCH(full_name) AGAINST(%s IN NATURAL LANGUAGE MODE) as score
            FROM ctv_data
            WHERE MATCH(full_name) AGAINST(%s IN NATURAL LANGUAGE MODE)
            ORDER BY score DESC
            LIMIT %s
        """
        
        cursor.execute(sql_fulltext, (name, name, limit))
        rows = cursor.fetchall()
        
        # Nếu không có kết quả, thử search không dấu
        if not rows:
            sql_normalized = """
                SELECT id, sheet_name, row_number, full_name, mssv, unit, program,
                       MATCH(full_name_normalized) AGAINST(%s IN NATURAL LANGUAGE MODE) as score
                FROM ctv_data
                WHERE MATCH(full_name_normalized) AGAINST(%s IN NATURAL LANGUAGE MODE)
                ORDER BY score DESC
                LIMIT %s
            """
            cursor.execute(sql_normalized, (name, name, limit))
            rows = cursor.fetchall()
        
        # Nếu vẫn không có, thử LIKE
        if not rows:
            sql_like = """
                SELECT id, sheet_name, row_number, full_name, mssv, unit, program, 0 as score
                FROM ctv_data
                WHERE full_name LIKE %s OR full_name_normalized LIKE %s
                LIMIT %s
            """
            pattern = f"%{name}%"
            cursor.execute(sql_like, (pattern, pattern, limit))
            rows = cursor.fetchall()
        
        cursor.close()
        return rows


def search_ctv_by_mssv(mssv: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Tìm CTV theo MSSV (exact hoặc partial match)."""
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor(dictionary=True)
        
        # Exact match first
        sql = """
            SELECT id, sheet_name, row_number, full_name, mssv, unit, program
            FROM ctv_data
            WHERE mssv = %s OR mssv LIKE %s
            LIMIT %s
        """
        
        cursor.execute(sql, (mssv, f"%{mssv}%", limit))
        rows = cursor.fetchall()
        cursor.close()
        return rows


def search_ctv_fulltext(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Full-text search toàn bộ text của CTV record (tên, đơn vị, chương trình).
    """
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor(dictionary=True)
        
        sql = """
            SELECT id, sheet_name, row_number, full_name, mssv, unit, program,
                   MATCH(row_text) AGAINST(%s IN NATURAL LANGUAGE MODE) as score
            FROM ctv_data
            WHERE MATCH(row_text) AGAINST(%s IN NATURAL LANGUAGE MODE)
            ORDER BY score DESC
            LIMIT %s
        """
        
        cursor.execute(sql, (query, query, limit))
        rows = cursor.fetchall()
        
        # Fallback: search không dấu
        if not rows:
            sql_normalized = """
                SELECT id, sheet_name, row_number, full_name, mssv, unit, program,
                       MATCH(row_text_normalized) AGAINST(%s IN NATURAL LANGUAGE MODE) as score
                FROM ctv_data
                WHERE MATCH(row_text_normalized) AGAINST(%s IN NATURAL LANGUAGE MODE)
                ORDER BY score DESC
                LIMIT %s
            """
            cursor.execute(sql_normalized, (query, query, limit))
            rows = cursor.fetchall()
        
        cursor.close()
        return rows


def get_ctv_by_sheet(sheet_name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Lấy tất cả CTV trong một sheet."""
    with get_db_connection(LINKS_DB) as conn:
        cursor = conn.cursor(dictionary=True)
        
        sql = """
            SELECT id, sheet_name, row_number, full_name, mssv, unit, program
            FROM ctv_data
            WHERE sheet_name = %s
            ORDER BY row_number
            LIMIT %s
        """
        
        cursor.execute(sql, (sheet_name, limit))
        rows = cursor.fetchall()
        cursor.close()
        return rows


# =========================
# Content Database Operations
# =========================
def upsert_fetched_content(
    url: str,
    raw_content: Optional[str],
    normalized_content: Optional[str],
    content_type: str = "text/csv",
    gid: Optional[str] = None,
    row_count: int = 0,
    status: str = "ok",
    error_message: Optional[str] = None,
) -> int:
    """
    Insert hoặc update nội dung đã fetch.
    Returns: affected row count
    """
    with get_db_connection(CONTENT_DB) as conn:
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO fetched_content 
            (url, gid, content_type, raw_content, normalized_content, row_count, status, error_message)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                gid = VALUES(gid),
                content_type = VALUES(content_type),
                raw_content = VALUES(raw_content),
                normalized_content = VALUES(normalized_content),
                row_count = VALUES(row_count),
                status = VALUES(status),
                error_message = VALUES(error_message),
                updated_at = CURRENT_TIMESTAMP
        """
        
        cursor.execute(sql, (
            url[:2048],
            gid[:100] if gid else None,
            content_type[:100],
            raw_content,
            normalized_content,
            row_count,
            status[:50],
            error_message,
        ))
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        return affected


def insert_parsed_rows_batch(url: str, rows_data: List[Dict[str, Any]]) -> int:
    """
    Insert batch parsed rows vào bảng parsed_rows.
    rows_data: [{"row_number": 1, "values": [...], "text": "...", "normalized": "..."}, ...]
    Returns: inserted count
    """
    if not rows_data:
        return 0
    
    with get_db_connection(CONTENT_DB) as conn:
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO parsed_rows 
            (url, row_number, row_data, row_text, normalized_text)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        values = []
        for row_info in rows_data:
            values.append((
                url[:2048],
                row_info.get("row_number", 0),
                json.dumps(row_info.get("values", []), ensure_ascii=False),
                row_info.get("text", ""),
                row_info.get("normalized", ""),
            ))
        
        cursor.executemany(sql, values)
        conn.commit()
        inserted = cursor.rowcount
        cursor.close()
        return inserted


def clear_content_tables() -> Tuple[int, int]:
    """Xóa toàn bộ dữ liệu content. Returns: (fetched_deleted, rows_deleted)."""
    with get_db_connection(CONTENT_DB) as conn:
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM parsed_rows")
        rows_deleted = cursor.rowcount
        
        cursor.execute("DELETE FROM fetched_content")
        fetched_deleted = cursor.rowcount
        
        conn.commit()
        cursor.close()
        
        return fetched_deleted, rows_deleted


def get_content_summary() -> List[Dict[str, Any]]:
    """Lấy thống kê content đã fetch."""
    with get_db_connection(CONTENT_DB) as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM content_summary")
        rows = cursor.fetchall()
        cursor.close()
        return rows


def search_in_parsed_rows(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Full-text search trong bảng parsed_rows.
    Returns: list of matching rows với url, row_number, row_text
    """
    with get_db_connection(CONTENT_DB) as conn:
        cursor = conn.cursor(dictionary=True)
        
        # Thử search có dấu trước
        sql_with_diacritic = """
            SELECT url, row_number, row_text, 
                   MATCH(row_text) AGAINST(%s IN NATURAL LANGUAGE MODE) as score
            FROM parsed_rows
            WHERE MATCH(row_text) AGAINST(%s IN NATURAL LANGUAGE MODE)
            ORDER BY score DESC
            LIMIT %s
        """
        
        cursor.execute(sql_with_diacritic, (query, query, limit))
        rows = cursor.fetchall()
        
        # Nếu không có kết quả, thử search không dấu
        if not rows:
            sql_normalized = """
                SELECT url, row_number, row_text,
                       MATCH(normalized_text) AGAINST(%s IN NATURAL LANGUAGE MODE) as score
                FROM parsed_rows
                WHERE MATCH(normalized_text) AGAINST(%s IN NATURAL LANGUAGE MODE)
                ORDER BY score DESC
                LIMIT %s
            """
            cursor.execute(sql_normalized, (query, query, limit))
            rows = cursor.fetchall()
        
        cursor.close()
        return rows


def log_search_query(query: str, normalized_query: str, result_count: int, execution_time_ms: int) -> int:
    """Ghi log search query vào database."""
    with get_db_connection(CONTENT_DB) as conn:
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO search_queries 
            (query, normalized_query, result_count, execution_time_ms)
            VALUES (%s, %s, %s, %s)
        """
        
        cursor.execute(sql, (query, normalized_query, result_count, execution_time_ms))
        conn.commit()
        inserted_id = cursor.lastrowid
        cursor.close()
        return inserted_id


# =========================
# Utility Functions
# =========================
def init_databases() -> Dict[str, Any]:
    """
    Tạo databases và tables nếu chưa có.
    Yêu cầu file schema.sql nằm cùng thư mục.
    """
    import subprocess
    import os
    
    schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")
    if not os.path.exists(schema_file):
        return {"ok": False, "error": "schema.sql not found"}
    
    try:
        # Chạy schema.sql bằng mysql command line
        cmd = [
            "mysql",
            f"-h{MYSQL_CONFIG['host']}",
            f"-P{MYSQL_CONFIG['port']}",
            f"-u{MYSQL_CONFIG['user']}",
        ]
        if MYSQL_CONFIG.get("password"):
            cmd.append(f"-p{MYSQL_CONFIG['password']}")
        
        with open(schema_file, "r", encoding="utf-8") as f:
            result = subprocess.run(
                cmd,
                stdin=f,
                capture_output=True,
                text=True,
            )
        
        if result.returncode != 0:
            return {"ok": False, "error": result.stderr}
        
        return {"ok": True, "message": "Databases and tables created successfully"}
    
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    # Test connection
    print("Testing MySQL connection...")
    result = test_connection()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if result.get("ok"):
        print("\n✓ MySQL connection successful!")
        print(f"  Server version: {result.get('version')}")
        print(f"  Server time: {result.get('server_time')}")
    else:
        print("\n✗ MySQL connection failed!")
        print(f"  Error: {result.get('error')}")
