import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scriptbuddy.db")

def get_db_connection():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # Access columns by name
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}")
        raise

def query_all(sql, params=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # SQLite uses ? placeholder, MySQL uses %s. We need to standardize.
        # Simple replace for now, assuming standard usage.
        sql = sql.replace('%s', '?')
        cursor.execute(sql, params or ())
        result = cursor.fetchall()
        # Convert Row objects to dicts
        return [dict(row) for row in result]
    finally:
        cursor.close()
        conn.close()

def execute_query(sql, params=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        sql = sql.replace('%s', '?')
        cursor.execute(sql, params or ())
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()
