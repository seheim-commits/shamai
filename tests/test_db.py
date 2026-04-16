import os
import sqlite3
import pytest

os.environ["DB_PATH"] = ":memory:"

from db import init_db, get_db

def test_init_db_creates_tables():
    init_db()
    conn = get_db()
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "decisions" in tables
    conn.close()

def test_decisions_schema():
    init_db()
    conn = get_db()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(decisions)").fetchall()}
    expected = {"id", "filename", "committee", "appraiser", "block", "plot",
                "appraisal_type", "appraisal_version", "decision_date",
                "local_path", "downloaded_at", "ocr_status"}
    assert expected <= cols
    conn.close()

def test_fts5_table_exists():
    init_db()
    conn = get_db()
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE name='decision_text'"
    ).fetchone()
    assert row is not None
    conn.close()
