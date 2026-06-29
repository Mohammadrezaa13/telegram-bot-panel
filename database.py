import sqlite3
import threading
import os
import logging
from datetime import datetime, timezone, timedelta

DB_NAME = os.getenv("DB_PATH", "/tmp/bot_data.db")
IRAN_TZ = timezone(timedelta(hours=3, minutes=30))


def now_iran():
    return datetime.now(IRAN_TZ).strftime("%Y-%m-%d %H:%M:%S")
local = threading.local()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_conn():
    if not hasattr(local, "conn"):
        local.conn = sqlite3.connect(DB_NAME, check_same_thread=False)
        local.conn.row_factory = sqlite3.Row
    return local.conn


def init_db():
    try:
        conn = get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                photo_url TEXT,
                first_seen TEXT,
                last_seen TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                detail TEXT,
                timestamp TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)
        conn.commit()
        logger.info("Database initialized at %s", DB_NAME)
    except Exception as e:
        logger.error("DB init failed: %s", e)


init_db()


def upsert_user(user_id, first_name, last_name, username, photo_url=None):
    conn = get_conn()
    ts = now_iran()
    conn.execute("""
        INSERT INTO users (user_id, first_name, last_name, username, photo_url, first_seen, last_seen)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            username=excluded.username,
            photo_url=COALESCE(excluded.photo_url, users.photo_url),
            last_seen=excluded.last_seen
    """, (user_id, first_name, last_name, username, photo_url, ts, ts))
    conn.commit()


def log_action(user_id, action, detail=""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO actions (user_id, action, detail, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, action, detail, now_iran())
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
    today_str = now_iran()[:10]
    today = conn.execute(
        "SELECT COUNT(*) FROM users WHERE first_seen LIKE ?",
        (today_str + "%",)
    ).fetchone()[0]
    actions = conn.execute("SELECT COUNT(*) FROM actions").fetchone()[0]
    return {"total_users": total, "new_today": today, "total_actions": actions}
