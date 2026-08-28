"""SQLite ของ จัสมิน — ความจำถาวร: memory (ข้อเท็จจริงเกี่ยวกับผู้ใช้) / tasks (to-do) / reminders (เตือนตามเวลา)
ไฟล์อยู่ที่ jusmin-ai/jusmin.db (อยู่ใน .gitignore). เปิด connection ใหม่ต่อ operation — SQLite รับ
concurrent reader ได้สบาย ส่วน write สั้นมาก (personal use คนเดียว + scheduler thread เดียว) timeout กันชนไว้
"""
import os
import sqlite3

# jusmin-ai/ = แม่ของ tools/ ที่ไฟล์นี้อยู่ (แบบเดียวกับ files._PROJECT_DIR)
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DB_PATH = os.path.join(_PROJECT_DIR, "jusmin.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memory (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT NOT NULL,
    tag        TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT NOT NULL,
    due_at     TEXT NOT NULL DEFAULT '',
    priority   TEXT NOT NULL DEFAULT 'normal',
    done       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    done_at    TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS reminders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    text       TEXT NOT NULL,
    remind_at  TEXT NOT NULL,
    fired      INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql: str, params: tuple = ()) -> list:
    conn = connect()
    try:
        return conn.execute(sql, params).fetchall()
    finally:
        conn.close()


def execute(sql: str, params: tuple = ()) -> tuple[int, int]:
    """รัน INSERT/UPDATE/DELETE — คืน (lastrowid, rowcount)"""
    conn = connect()
    try:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur.lastrowid, cur.rowcount
    finally:
        conn.close()


def _init() -> None:
    conn = connect()
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()


_init()
