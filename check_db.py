#!/usr/bin/env python3
import sqlite3
import json

DB_FILE = "scriptbuddy.db"

def check_db():
    print(f"Connecting to SQLite database: {DB_FILE}\n")
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Check configs
    print("=" * 60)
    print("📋 CONFIGS TABLE")
    print("=" * 60)
    cursor.execute("SELECT * FROM script_configs ORDER BY category, key_name")
    for row in cursor.fetchall():
        value = row['value']
        if len(value) > 40:
            value = value[:37] + "..."
        print(f"  {row['category']:10s} | {row['key_name']:10s} | {value}")

    # Check stories
    print("\n" + "=" * 60)
    print("📖 SCRIPT STORIES TABLE")
    print("=" * 60)
    cursor.execute("SELECT * FROM script_stories")
    for row in cursor.fetchall():
        print(f"  ID: {row['id']}")
        print(f"  Title: {row['title']}")
        print(f"  Description: {row['description']}")
        role_map = json.loads(row['role_map_json']) if row['role_map_json'] else {}
        print(f"  Role Map: {role_map}")
        print(f"  Created: {row['created_at']}")

    # Check lines
    print("\n" + "=" * 60)
    print("📝 SCRIPT LINES TABLE")
    print("=" * 60)
    cursor.execute("SELECT * FROM script_lines ORDER BY story_id, sort_order")
    for row in cursor.fetchall():
        content = row['content']
        if len(content) > 50:
            content = content[:47] + "..."
        print(f"  [{row['sort_order']}] {row['role_key']:4s} | {content:50s} | {row['duration_ms']}ms")

    conn.close()
    print("\n✅ Database check complete!\n")

if __name__ == "__main__":
    check_db()
