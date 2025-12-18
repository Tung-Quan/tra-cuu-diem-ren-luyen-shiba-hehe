# db_mysql.py — Simplified MySQL for CTV Links Query System
import os
import json
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
    "database": os.environ.get("MYSQL_DATABASE", "ctv_links"),
}

DB_NAME = "ctv_links"


# =========================
# Connection Management
# =========================
@contextmanager
def get_db_connection():
    """Context manager để tạo MySQL connection."""
    if not HAS_MYSQL:
        raise ImportError("mysql-connector-python not installed")
    
    conn = None
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        yield conn
    except MySQLError as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn and conn.is_connected():
            conn.close()


def test_connection() -> Dict[str, Any]:
    """Test MySQL connection."""
    try:
        # Connect without specifying database first
        config = MYSQL_CONFIG.copy()
        config.pop("database", None)
        
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return {
            "ok": True,
            "version": version,
            "database": None,
            "config": {k: v for k, v in MYSQL_CONFIG.items() if k != "password"}
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# =========================
# Core Query Functions: Query → MSSV/Name → Links
# =========================

def search_student_links(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Core function: Query tên hoặc MSSV sinh viên, trả về links.
    
    Returns: [{
        "student_id": int,
        "full_name": str,
        "mssv": str,
        "links": [{"url": str, "sheet": str, "row": int, "address": str}, ...]
    }]
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        
        # Search by MSSV (exact hoặc partial)
        sql = """
            SELECT 
                s.student_id,
                s.full_name,
                s.mssv,
                s.search_name,
                sl.link_id,
                l.url,
                l.title,
                l.kind,
                l.gid,
                sl.sheet_name,
                sl.row_number,
                sl.snippet,
            FROM student s
            LEFT JOIN student_link sl ON s.student_id = sl.student_id
            LEFT JOIN link l ON sl.link_id = l.link_id
            WHERE s.mssv LIKE %s 
               OR s.full_name LIKE %s
               OR s.search_name LIKE %s
            ORDER BY s.student_id, sl.sheet_name, sl.row_number
            LIMIT %s
        """
        
        pattern = f"%{query}%"
        cursor.execute(sql, (pattern, pattern, pattern, limit * 10))
        rows = cursor.fetchall()
        cursor.close()
        
        # Group by student
        students_dict = {}
        for row in rows:
            sid = row["student_id"]
            if sid not in students_dict:
                students_dict[sid] = {
                    "student_id": sid,
                    "full_name": row["full_name"],
                    "mssv": row["mssv"],
                    "search_name": row["search_name"],
                    "links": []
                }
            
            if row["url"]:  # Only add if link exists
                students_dict[sid]["links"].append({
                    "link_id": row["link_id"],
                    "url": row["url"],
                    "title": row["title"],
                    "kind": row["kind"],
                    "gid": row["gid"],
                    "sheet_name": row["sheet_name"],
                    "row_number": row["row_number"],
                    "snippet": row["snippet"]
                })
        
        return list(students_dict.values())[:limit]


def quick_search(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Quick search - chỉ trả về student info + count links.
    Nhanh hơn search_student_links() vì không JOIN link details.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        
        sql = """
            SELECT 
                s.student_id,
                s.full_name,
                s.mssv,
                COUNT(sl.link_id) as link_count
            FROM student s
            LEFT JOIN student_link sl ON s.student_id = sl.student_id
            WHERE s.mssv LIKE %s 
               OR s.full_name LIKE %s
               OR s.search_name LIKE %s
            GROUP BY s.student_id, s.full_name, s.mssv
            ORDER BY link_count DESC, s.full_name
            LIMIT %s
        """
        
        pattern = f"%{query}%"
        cursor.execute(sql, (pattern, pattern, pattern, limit))
        rows = cursor.fetchall()
        cursor.close()
        
        return rows


def get_student_links_by_mssv(mssv: str) -> Optional[Dict[str, Any]]:
    """Lấy tất cả links của 1 sinh viên theo MSSV (exact match)."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        
        sql = """
            SELECT 
                s.student_id,
                s.full_name,
                s.mssv,
                l.url,
                l.title,
                l.kind,
                l.gid,
                sl.sheet_name,
                sl.row_number,
                sl.address,
                sl.snippet
            FROM student s
            LEFT JOIN student_link sl ON s.student_id = sl.student_id
            LEFT JOIN link l ON sl.link_id = l.link_id
            WHERE s.mssv = %s
            ORDER BY sl.sheet_name, sl.row_number
        """
        
        cursor.execute(sql, (mssv,))
        rows = cursor.fetchall()
        cursor.close()
        
        if not rows:
            return None
        
        result = {
            "student_id": rows[0]["student_id"],
            "full_name": rows[0]["full_name"],
            "mssv": rows[0]["mssv"],
            "links": []
        }
        
        for row in rows:
            if row["url"]:
                result["links"].append({
                    "url": row["url"],
                    "title": row["title"],
                    "kind": row["kind"],
                    "gid": row["gid"],
                    "sheet": row["sheet_name"],
                    "row": row["row_number"],
                    "address": row["address"],
                    "snippet": row["snippet"]
                })
        
        return result


# =========================
# Insert/Update Functions
# =========================

def insert_student(full_name: str, mssv: Optional[str] = None) -> int:
    """Insert student, returns student_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO student (full_name, mssv)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE 
                mssv = VALUES(mssv),
                student_id = LAST_INSERT_ID(student_id)
        """
        
        cursor.execute(sql, (full_name, mssv))
        conn.commit()
        student_id = cursor.lastrowid
        cursor.close()
        
        return student_id


def insert_link(url: str, title: Optional[str] = None, kind: Optional[str] = None, 
                gid: Optional[str] = None) -> int:
    """Insert link, returns link_id."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO link (url, title, kind, gid)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                title = COALESCE(VALUES(title), title),
                kind = COALESCE(VALUES(kind), kind),
                gid = COALESCE(VALUES(gid), gid),
                link_id = LAST_INSERT_ID(link_id)
        """
        
        cursor.execute(sql, (url, title, kind, gid))
        conn.commit()
        link_id = cursor.lastrowid
        cursor.close()
        
        return link_id


def link_student_to_url(
    student_id: int,
    link_id: int,
    sheet_name: Optional[str] = None,
    row_number: Optional[int] = None,
    address: Optional[str] = None,
    snippet: Optional[str] = None
) -> bool:
    """Tạo mối liên kết student <-> link."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        sql = """
            INSERT INTO student_link 
            (student_id, link_id, sheet_name, row_number, address, snippet)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                sheet_name = VALUES(sheet_name),
                address = VALUES(address),
                snippet = VALUES(snippet)
        """
        
        cursor.execute(sql, (student_id, link_id, sheet_name, row_number, address, snippet))
        conn.commit()
        affected = cursor.rowcount
        cursor.close()
        
        return affected > 0


# =========================
# Batch Operations
# =========================

def get_student_id_by_name(full_name: str) -> Optional[int]:
    """Check if student exists by exact full_name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT student_id FROM student WHERE full_name = %s", (full_name,))
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None


def get_link_id_by_url(url: str) -> Optional[int]:
    """Check if link exists by url (using hash)."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT link_id FROM link WHERE url_hash = UNHEX(MD5(%s))", (url,))
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None


def check_student_link_exists(student_id: int, link_id: int, row_number: int) -> bool:
    """Check if connection exists."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM student_link WHERE student_id = %s AND link_id = %s AND row_number = %s",
            (student_id, link_id, row_number)
        )
        row = cursor.fetchone()
        cursor.close()
        return row is not None


def batch_insert_student_links(records: List[Dict[str, Any]]) -> int:
    """
    Batch insert student-link records.
    Uses a single connection to avoid socket exhaustion (Error 10048).
    """
    inserted = 0
    
    # SQL Templates
    sql_check_student = "SELECT student_id FROM student WHERE full_name = %s"
    sql_insert_student = """
        INSERT INTO student (full_name, mssv)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE 
            mssv = VALUES(mssv),
            student_id = LAST_INSERT_ID(student_id)
    """
    
    sql_check_link = "SELECT link_id FROM link WHERE url_hash = UNHEX(MD5(%s))"
    sql_insert_link = """
        INSERT INTO link (url, title, kind, gid)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE 
            title = VALUES(title),
            kind = VALUES(kind),
            gid = VALUES(gid),
            link_id = LAST_INSERT_ID(link_id)
    """
    
    sql_check_conn = "SELECT 1 FROM student_link WHERE student_id = %s AND link_id = %s AND row_number = %s"
    sql_insert_conn = """
        INSERT INTO student_link 
        (student_id, link_id, sheet_name, row_number, address, snippet)
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        for rec in records:
            try:
                # 1. Check/Get Student
                full_name = rec.get("full_name", "").strip()
                if not full_name:
                    continue

                mssv = rec.get("mssv")
                
                cursor.execute(sql_check_student, (full_name,))
                row = cursor.fetchone()
                
                if row:
                    student_id = row[0]
                else:
                    cursor.execute(sql_insert_student, (full_name, mssv))
                    student_id = cursor.lastrowid
                
                # 2. Check/Get Link
                url = rec.get("url", "")
                title = rec.get("title")
                kind = rec.get("kind")
                # Use 'main_sheet' (Spreadsheet Title) as gid primarily, fallback to 'program'
                gid = rec.get("main_sheet") or rec.get("program")
                
                if not url:
                    continue
                
                # Check link type for logging
                if kind == 'drive' or 'drive.google.com' in url or 'docs.google.com' in url:
                    print(f"[batch_insert] Processing Drive link: {url} (Title: {title}, Kind: {kind}, Gid: {gid})")
                    
                cursor.execute(sql_check_link, (url,))
                row = cursor.fetchone()
                
                if row:
                    link_id = row[0]
                    # Update metadata if available
                    if title or kind or gid:
                        cursor.execute(
                            "UPDATE link SET title = COALESCE(%s, title), kind = COALESCE(%s, kind), gid = COALESCE(%s, gid) WHERE link_id = %s",
                            (title, kind, gid, link_id)
                        )
                else:
                    cursor.execute(sql_insert_link, (url, title, kind, gid))
                    link_id = cursor.lastrowid
                
                # 3. Check/Create Connection
                row_num = rec.get("row") or 0
                cursor.execute(sql_check_conn, (student_id, link_id, row_num))
                
                if not cursor.fetchone():
                    cursor.execute(sql_insert_conn, (
                        student_id, link_id, 
                        rec.get("sheet"), row_num, 
                        rec.get("address"), rec.get("snippet")
                    ))
                    inserted += 1
                
                conn.commit()
                
            except Exception as e:
                print(f"[batch_insert] Error processing record {rec.get('full_name')}: {e}")
                continue
        
        cursor.close()
    
    return inserted


# =========================
# Statistics
# =========================

def get_stats() -> Dict[str, Any]:
    """Lấy thống kê tổng quan."""
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        
        stats = {}
        
        # Student count
        cursor.execute("SELECT COUNT(*) as count FROM student")
        stats["students"] = cursor.fetchone()["count"]
        
        # Link count
        cursor.execute("SELECT COUNT(*) as count FROM link")
        stats["links"] = cursor.fetchone()["count"]
        
        # Student-Link connections
        cursor.execute("SELECT COUNT(*) as count FROM student_link")
        stats["connections"] = cursor.fetchone()["count"]
        
        # Students with links
        cursor.execute("""
            SELECT COUNT(DISTINCT student_id) as count 
            FROM student_link
        """)
        stats["students_with_links"] = cursor.fetchone()["count"]
        
        # Top students by link count
        cursor.execute("""
            SELECT s.full_name, s.mssv, COUNT(*) as link_count
            FROM student s
            JOIN student_link sl ON s.student_id = sl.student_id
            GROUP BY s.student_id, s.full_name, s.mssv
            ORDER BY link_count DESC
            LIMIT 10
        """)
        stats["top_students"] = cursor.fetchall()
        
        cursor.close()
        return stats


# =========================
# Schema Init
# =========================

def init_schema() -> Dict[str, Any]:
    """Tạo schema nếu chưa có."""
    try:
        # Connect without database first
        config = MYSQL_CONFIG.copy()
        config.pop("database", None)
        
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        
        # Create database if not exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.execute(f"USE {DB_NAME}")
        
        # Student table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student (
                student_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                full_name VARCHAR(255) NOT NULL,
                mssv VARCHAR(50) NULL,
                search_name VARCHAR(255) GENERATED ALWAYS AS (
                    LOWER(REPLACE(REPLACE(full_name, ' ', ''), '-', ''))
                ) STORED,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_student_name (full_name),
                KEY idx_mssv (mssv),
                KEY idx_search_name (search_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Link table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS link (
                link_id BIGINT PRIMARY KEY AUTO_INCREMENT,
                url TEXT NOT NULL,
                url_hash BINARY(16) GENERATED ALWAYS AS (UNHEX(MD5(url))) STORED,
                title VARCHAR(500) NULL,
                kind VARCHAR(32) NULL,
                gid VARCHAR(512) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_link_hash (url_hash),
                KEY idx_kind (kind),
                KEY idx_gid (gid)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        # Student-Link junction table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_link (
                student_id BIGINT NOT NULL,
                link_id BIGINT NOT NULL,
                sheet_name VARCHAR(255) NULL,
                row_number INT NULL DEFAULT 0,
                address VARCHAR(16) NULL,
                snippet VARCHAR(512) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (student_id, link_id, row_number),
                CONSTRAINT fk_sl_student FOREIGN KEY (student_id) 
                    REFERENCES student(student_id) ON DELETE CASCADE,
                CONSTRAINT fk_sl_link FOREIGN KEY (link_id) 
                    REFERENCES link(link_id) ON DELETE CASCADE,
                KEY idx_sheet (sheet_name),
                KEY idx_row (row_number)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return {"ok": True, "message": f"Schema {DB_NAME} initialized successfully"}
        
    except Exception as e:
        return {"ok": False, "error": str(e)}


if __name__ == "__main__":
    print("=" * 60)
    print("CTV Links Query System - Database Module")
    print("=" * 60)
    
    # Test connection
    print("\n1. Testing connection...")
    result = test_connection()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if not result.get("ok"):
        print("\n✗ Connection failed!")
        exit(1)
    
    print("\n✓ Connection successful!")
    
    # Init schema
    print("\n2. Initializing schema...")
    result = init_schema()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    if result.get("ok"):
        print("\n✓ Schema ready!")
        
        # Show stats
        print("\n3. Database statistics:")
        stats = get_stats()
        print(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        print("\n✗ Schema init failed!")
