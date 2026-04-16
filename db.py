import os
import sqlite3
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "index.db")

_memory_conn: Optional[sqlite3.Connection] = None


def _is_closed(conn: sqlite3.Connection) -> bool:
    try:
        conn.execute("SELECT 1")
        return False
    except Exception:
        return True


def get_db() -> sqlite3.Connection:
    global _memory_conn
    path = DB_PATH
    if path == ":memory:":
        if _memory_conn is None or _is_closed(_memory_conn):
            _memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            _memory_conn.row_factory = sqlite3.Row
        return _memory_conn
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            committee TEXT,
            appraiser TEXT,
            block TEXT,
            plot TEXT,
            appraisal_type TEXT,
            appraisal_version TEXT,
            decision_date TEXT,
            local_path TEXT NOT NULL UNIQUE,
            downloaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            ocr_status TEXT DEFAULT 'none'
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS decision_text USING fts5(
            text,
            content=decisions,
            content_rowid=id
        );
    """)
    conn.commit()
    if DB_PATH != ":memory:" and conn is not _memory_conn:
        conn.close()
