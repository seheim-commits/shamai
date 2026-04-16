import os
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ["DB_PATH"] = ":memory:"
os.environ["PDFS_DIR"] = "/tmp/shamai_test_pdfs"

from db import init_db, get_db
from api.downloader import local_path, download_pdf, index_decision


def test_local_path_structure():
    p = local_path(
        committee="תל אביב-יפו",
        decision_date="2025-08-24T00:00:00+03:00",
        block="6106",
        plot="316",
        appraiser="חיים מסילתי",
    )
    assert p.suffix == ".pdf"
    assert "2025-08-24" in p.name
    assert "6106" in p.name
    assert "316" in p.name
    assert "מסילתי" in p.name


def test_local_path_committee_is_parent_dir():
    p = local_path(
        committee="ירושלים",
        decision_date="2024-01-15T00:00:00",
        block="100",
        plot="50",
        appraiser="דוד כהן",
    )
    assert "ירושלים" in str(p.parent)


def test_index_decision_inserts_row():
    init_db()
    conn = get_db()
    data = {
        "AppraisalHeader": "גוש 6106 חלקה 316",
        "Committee": "תל אביב-יפו",
        "DecisiveAppraiser": "חיים מסילתי",
        "Block": "6106",
        "Plot": "316",
        "AppraisalType": "היטל השבחה",
        "AppraisalVersion": "שומה מקורית",
        "DecisionDate": "2025-08-24T00:00:00+03:00",
    }
    row_id = index_decision(conn, data, "/tmp/test.pdf")
    assert row_id is not None

    row = conn.execute("SELECT * FROM decisions WHERE id=?", (row_id,)).fetchone()
    assert row["committee"] == "תל אביב-יפו"
    assert row["block"] == "6106"
    assert row["ocr_status"] == "none"
    conn.close()


def test_index_decision_ignores_duplicate():
    init_db()
    conn = get_db()
    data = {"AppraisalHeader": "test", "Committee": "test", "DecisiveAppraiser": "test",
            "Block": "1", "Plot": "1", "AppraisalType": "", "AppraisalVersion": "", "DecisionDate": ""}
    index_decision(conn, data, "/tmp/unique.pdf")
    row_id2 = index_decision(conn, data, "/tmp/unique.pdf")  # duplicate path
    assert row_id2 == 0  # INSERT OR IGNORE returns 0 lastrowid on ignore
    conn.close()


def test_download_pdf_writes_file(tmp_path):
    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 fake content"
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        dest = tmp_path / "test.pdf"
        result = download_pdf("https://example.com/file.pdf", dest)

    assert result == dest
    assert dest.read_bytes() == b"%PDF-1.4 fake content"
