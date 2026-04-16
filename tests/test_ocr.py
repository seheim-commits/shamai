import os
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

os.environ["DB_PATH"] = ":memory:"

from db import init_db, get_db
from api.ocr import extract_text_pdfplumber, ocr_pdf, store_ocr


def _make_text_pdf(tmp_path: Path) -> Path:
    """Create a minimal valid PDF with extractable text using only stdlib."""
    pdf_path = tmp_path / "test.pdf"
    # Minimal PDF with the text "Hello World" embedded
    content = b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj
4 0 obj<</Length 44>>
stream
BT /F1 12 Tf 100 700 Td (Hello World) Tj ET
endstream
endobj
5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
0000000360 00000 n
trailer<</Size 6/Root 1 0 R>>
startxref
441
%%EOF"""
    pdf_path.write_bytes(content)
    return pdf_path


def test_extract_text_pdfplumber_returns_string(tmp_path):
    pdf = _make_text_pdf(tmp_path)
    # pdfplumber may or may not extract from this minimal PDF — we just check return type
    text = extract_text_pdfplumber(pdf)
    assert isinstance(text, str)


def test_ocr_pdf_falls_back_to_tesseract_when_empty(tmp_path):
    pdf = _make_text_pdf(tmp_path)
    with patch("api.ocr.extract_text_pdfplumber", return_value=""):
        with patch("api.ocr.extract_text_tesseract", return_value="tesseract result") as mock_tess:
            result = ocr_pdf(pdf)
    mock_tess.assert_called_once_with(pdf)
    assert result == "tesseract result"


def test_ocr_pdf_uses_pdfplumber_when_sufficient(tmp_path):
    pdf = _make_text_pdf(tmp_path)
    long_text = "א" * 200
    with patch("api.ocr.extract_text_pdfplumber", return_value=long_text):
        with patch("api.ocr.extract_text_tesseract") as mock_tess:
            result = ocr_pdf(pdf)
    mock_tess.assert_not_called()
    assert result == long_text


def test_store_ocr_saves_text_and_updates_status():
    init_db()
    conn = get_db()
    conn.execute(
        "INSERT INTO decisions (filename, local_path) VALUES (?, ?)",
        ("test.pdf", "/tmp/test.pdf")
    )
    conn.commit()
    row = conn.execute("SELECT id FROM decisions WHERE local_path='/tmp/test.pdf'").fetchone()
    decision_id = row["id"]

    store_ocr(conn, decision_id, "extracted text content")

    text_row = conn.execute(
        "SELECT text FROM decision_text WHERE rowid=?", (decision_id,)
    ).fetchone()
    assert text_row["text"] == "extracted text content"

    status_row = conn.execute(
        "SELECT ocr_status FROM decisions WHERE id=?", (decision_id,)
    ).fetchone()
    assert status_row["ocr_status"] == "done"
    conn.close()
