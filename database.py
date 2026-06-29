import sqlite3
import threading
import os

DB_NAME = os.getenv("DB_PATH", "bot_data.db")
local = threading.local()


def get_conn():
    if not hasattr(local, "conn"):
        local.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        local.conn.row_factory = sqlite3.Row
    return local.conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            photo_url TEXT,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            detail TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    conn.commit()


init_db()


def upsert_user(user_id, first_name, last_name, username, photo_url=None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO users (user_id, first_name, last_name, username, photo_url, last_seen)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            username=excluded.username,
            photo_url=COALESCE(excluded.photo_url, users.photo_url),
            last_seen=CURRENT_TIMESTAMP
    """, (user_id, first_name, last_name, username, photo_url))
    conn.commit()


def log_action(user_id, action, detail=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO actions (user_id, action, detail) VALUES (?, ?, ?)",
        (user_id, action, detail)
    )
    conn.commit()


def get_all_users():
    conn = get_conn()
    return conn.execute(
        "SELECT * FROM users ORDER BY last_seen DESC"
    ).fetchall()


def get_user_actions(user_id):
    conn = get_conn()
    return conn.execute(
        "SELECT * FROM actions WHERE user_id=? ORDER BY timestamp DESC LIMIT 50",
        (user_id,)
    ).fetchall()


def get_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    today = conn.execute(
        "SELECT COUNT(*) FROM users WHERE date(first_seen)=date('now')"
    ).fetchone()[0]
    actions = conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
    return {"total_users": total, "new_today": today, "total_actions": actions}
