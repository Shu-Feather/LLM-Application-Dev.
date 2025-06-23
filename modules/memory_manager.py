import os
import sqlite3
import json
from datetime import datetime

class MemoryManager:
    def __init__(self, db_path: str = None):
        path = db_path or os.getenv('MEMORY_DB', 'memory.db')
        self.db_path = path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS conversations (id INTEGER PRIMARY KEY, user_id TEXT, timestamp TEXT, role TEXT, content TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_profiles (user_id TEXT PRIMARY KEY, profile TEXT)''')
        conn.commit()
        conn.close()

    def add_message(self, user_id: str, role: str, content: str):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        ts = datetime.utcnow().isoformat() + 'Z'
        c.execute('INSERT INTO conversations (user_id, timestamp, role, content) VALUES (?, ?, ?, ?)', (user_id, ts, role, content))
        conn.commit()
        conn.close()

    def get_history(self, user_id: str, limit: int = None) -> list:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if limit:
            c.execute('SELECT role, content, timestamp FROM conversations WHERE user_id=? ORDER BY id DESC LIMIT ?', (user_id, limit))
        else:
            c.execute('SELECT role, content, timestamp FROM conversations WHERE user_id=? ORDER BY id DESC', (user_id,))
        rows = c.fetchall()
        conn.close()
        return [{'role': r[0], 'content': r[1], 'timestamp': r[2]} for r in reversed(rows)]

    def set_user_profile(self, user_id: str, profile: dict):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        profile_json = json.dumps(profile, ensure_ascii=False)
        c.execute('REPLACE INTO user_profiles (user_id, profile) VALUES (?, ?)', (user_id, profile_json))
        conn.commit()
        conn.close()

    def get_user_profile(self, user_id: str) -> dict:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT profile FROM user_profiles WHERE user_id=?', (user_id,))
        row = c.fetchone()
        conn.close()
        return json.loads(row[0]) if row else {}