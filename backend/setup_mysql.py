#!/usr/bin/env python3
# setup_mysql.py - Script to initialize MySQL databases
import sys
import os

# Add current directory to path to import db_mysql
sys.path.insert(0, os.path.dirname(__file__))

try:
    import mysql.connector
    from mysql.connector import Error as MySQLError
except ImportError:
    print("ERROR: mysql-connector-python not installed")
    print("Run: pip install mysql-connector-python")
    sys.exit(1)

MYSQL_CONFIG = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", ""),
    "charset": "utf8mb4",
}

def run_sql_file(filepath: str):
    """Execute SQL file."""
    print(f"Reading {filepath}...")
    
    with open(filepath, "r", encoding="utf-8") as f:
        sql_content = f.read()
    
    # Split by semicolon and execute each statement
    statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
    
    print(f"Found {len(statements)} SQL statements")
    print(f"Connecting to MySQL at {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}...")
    
    conn = None
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        success = 0
        errors = 0
        
        for i, stmt in enumerate(statements, 1):
            # Skip comments
            if stmt.startswith("--") or not stmt:
                continue
            
            try:
                # Handle USE database separately
                if stmt.upper().startswith("USE "):
                    db_name = stmt.split()[1].strip(";")
                    print(f"  [{i}/{len(statements)}] Switching to database: {db_name}")
                    cursor.execute(stmt)
                elif stmt.upper().startswith("CREATE DATABASE"):
                    db_name = stmt.split("DATABASE")[1].split()[1] if "IF NOT EXISTS" in stmt.upper() else stmt.split()[2]
                    print(f"  [{i}/{len(statements)}] Creating database: {db_name}")
                    cursor.execute(stmt)
                elif stmt.upper().startswith("CREATE TABLE") or stmt.upper().startswith("CREATE OR REPLACE VIEW"):
                    # Extract table/view name
                    if "TABLE" in stmt.upper():
                        parts = stmt.split("TABLE")[1].strip().split()
                        name = parts[2] if parts[0].upper() == "IF" else parts[0]
                    else:
                        name = stmt.split("VIEW")[1].strip().split()[0]
                    print(f"  [{i}/{len(statements)}] Creating: {name}")
                    cursor.execute(stmt)
                else:
                    cursor.execute(stmt)
                
                success += 1
            except MySQLError as e:
                # Ignore "database exists" and "table exists" warnings
                if e.errno not in (1007, 1050):  # DB exists, Table exists
                    print(f"  ERROR on statement {i}: {e}")
                    errors += 1
        
        conn.commit()
        cursor.close()
        
        print(f"\n✓ Schema setup complete!")
        print(f"  Successful: {success}")
        print(f"  Errors: {errors}")
        
        # Verify databases
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES LIKE 'ctv_%'")
        dbs = cursor.fetchall()
        cursor.close()
        
        print(f"\n✓ Created databases:")
        for db in dbs:
            print(f"  - {db[0]}")
        
        return True
        
    except MySQLError as e:
        print(f"\n✗ MySQL Error: {e}")
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    schema_file = os.path.join(os.path.dirname(__file__), "schema.sql")
    
    if not os.path.exists(schema_file):
        print(f"ERROR: {schema_file} not found")
        sys.exit(1)
    
    print("=" * 60)
    print("MySQL Database Setup for CTV System")
    print("=" * 60)
    print()
    
    success = run_sql_file(schema_file)
    
    if success:
        print("\n" + "=" * 60)
        print("Next steps:")
        print("  1. Start backend server: python backend.py")
        print("  2. Sync links: curl http://localhost:8000/mysql/sync_links -X POST")
        print("  3. Check: curl http://localhost:8000/mysql/links/count")
        print("=" * 60)
        sys.exit(0)
    else:
        sys.exit(1)
