import sqlite3
import os
import json

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scriptbuddy.db")

def init_db():
    print(f"Initializing SQLite database at: {DB_FILE}")
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
        print("Removed existing database")

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # 1. Create Tables
    print("Creating tables...")

    # Config table
    cursor.execute('''
    CREATE TABLE script_configs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category VARCHAR(50) NOT NULL DEFAULT '',
        key_name VARCHAR(50) NOT NULL DEFAULT '',
        value VARCHAR(500) NOT NULL DEFAULT '',
        UNIQUE(category, key_name)
    )
    ''')

    # Stories table
    cursor.execute('''
    CREATE TABLE script_stories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(100) NOT NULL DEFAULT '',
        description VARCHAR(255) DEFAULT '',
        role_map_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Lines table
    cursor.execute('''
    CREATE TABLE script_lines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        story_id INTEGER NOT NULL,
        role_key VARCHAR(50) NOT NULL DEFAULT '',
        content TEXT NOT NULL,
        duration_ms INTEGER DEFAULT 3000,
        sort_order INTEGER NOT NULL DEFAULT 0,
        FOREIGN KEY (story_id) REFERENCES script_stories(id)
    )
    ''')

    # Create index
    cursor.execute('CREATE INDEX idx_story_order ON script_lines(story_id, sort_order)')

    # 2. Insert Seed Data
    print("Inserting seed data...")

    # Configs
    configs = [
        ('asr', 'appId', '5349866810'),
        ('asr', 'token', 'j_DA2hGKCvrytiS1fM-1jN5Cqz6Mxpx3'),
        ('asr', 'secret', '1oJHD2KkFJTMbLgPIx4fAR9XS7qGZNM7'),
        ('asr', 'cluster', 'volc_auction_streaming_2.0'),
        ('tts', 'appId', '5349866810'),
        ('tts', 'token', 'j_DA2hGKCvrytiS1fM-1jN5Cqz6Mxpx3'),
        ('tts', 'secret', '1oJHD2KkFJTMbLgPIx4fAR9XS7qGZNM7'),
        ('tts', 'cluster', 'volcano_tts'),
        ('llm', 'apiKey', 'sk-903a962786f34773a1680f6fb6fad64d'),
        ('llm', 'baseUrl', 'https://api.deepseek.com')
    ]
    cursor.executemany("INSERT INTO script_configs (category, key_name, value) VALUES (?, ?, ?)", configs)

    # Story
    cursor.execute(
        "INSERT INTO script_stories (id, title, description, role_map_json) VALUES (?, ?, ?, ?)",
        (1, '面试练习：自我介绍', '模拟一场简单的HR面试场景。',
         json.dumps({"甲": "面试官", "乙": "求职者", "合": "旁白/系统"}, ensure_ascii=False))
    )

    # Lines
    lines = [
        (1, '甲', '您好，请先简单做一个自我介绍吧。', 3000, 1),
        (1, '乙', '好的。面试官您好，我叫陈驰，是一名全栈工程师。', 4000, 2),
        (1, '甲', '我看你的简历上写着熟悉 React 和 PHP？', 3000, 3),
        (1, '乙', '是的，我即使在 PHP 5.4 的环境下也能写出现代化的代码。', 4000, 4),
        (1, '合', '（面试官露出了满意的微笑）', 2000, 5),
        (1, '甲', '很有意思。那我们开始技术测试吧。', 3000, 6),
        (1, '乙', '没问题，请出题。', 2000, 7)
    ]
    cursor.executemany(
        "INSERT INTO script_lines (story_id, role_key, content, duration_ms, sort_order) VALUES (?, ?, ?, ?, ?)",
        lines
    )

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully!")
    print(f"Database location: {DB_FILE}")

if __name__ == "__main__":
    init_db()
