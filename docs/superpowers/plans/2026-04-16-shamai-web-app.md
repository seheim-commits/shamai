# Shamai Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local FastAPI web app to search, bulk-download, OCR, and Claude-analyze decisive appraiser decisions from the Israeli Ministry of Justice API.

**Architecture:** Single Python FastAPI process serves a vanilla HTML/JS single-page app (RTL/Hebrew) and handles all backend operations — MoJ API proxying, PDF download to local disk, OCR via pdfplumber/pytesseract, and Claude streaming analysis. SQLite with FTS5 indexes downloaded PDFs for full-text search.

**Tech Stack:** Python 3.11+, FastAPI, uvicorn, httpx, pdfplumber, pytesseract, pdf2image, anthropic SDK, SQLite (built-in), python-dotenv, pytest

---

## File Map

| File | Responsibility |
|------|----------------|
| `requirements.txt` | All Python dependencies |
| `.env.example` | Template for ANTHROPIC_API_KEY |
| `.gitignore` | Exclude pdfs/, index.db, .env |
| `db.py` | SQLite connection, schema init, FTS5 table |
| `api/__init__.py` | Empty |
| `api/moj.py` | MoJ API client — search, filters, pdf_url |
| `api/downloader.py` | PDF fetch to disk, SQLite indexing, file naming |
| `api/ocr.py` | pdfplumber + pytesseract fallback, FTS5 storage |
| `api/claude.py` | Claude streaming analysis |
| `server.py` | FastAPI routes + static file mount |
| `static/index.html` | 3-tab SPA shell, RTL, Hebrew labels |
| `static/style.css` | Dark theme, RTL layout |
| `static/app.js` | Tab routing, all API calls, SSE handling |
| `tests/test_moj.py` | MoJ client unit tests (httpx mocked) |
| `tests/test_downloader.py` | Downloader unit tests (in-memory SQLite) |
| `tests/test_ocr.py` | OCR pipeline tests (fixture PDF) |
| `tests/test_claude.py` | Claude integration tests (anthropic mocked) |

---

## Task 1: Project Scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `api/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
fastapi==0.115.6
uvicorn==0.34.0
httpx==0.28.1
pdfplumber==0.11.4
pytesseract==0.3.13
pdf2image==1.17.0
Pillow==11.1.0
anthropic==0.49.0
python-dotenv==1.0.1
pytest==8.3.4
pytest-asyncio==0.25.2
```

- [ ] **Step 2: Create .env.example**

```
ANTHROPIC_API_KEY=sk-ant-...
DB_PATH=index.db
PDFS_DIR=pdfs
```

- [ ] **Step 3: Create .gitignore**

```
.env
pdfs/
index.db
__pycache__/
*.pyc
.pytest_cache/
.superpowers/
```

- [ ] **Step 4: Create empty init files**

```bash
touch api/__init__.py tests/__init__.py
```

- [ ] **Step 5: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without error. Note: pytesseract also requires the Tesseract binary:
```bash
brew install tesseract tesseract-lang
```

- [ ] **Step 6: Commit**

```bash
git init
git add requirements.txt .env.example .gitignore api/__init__.py tests/__init__.py
git commit -m "chore: project scaffold"
```

---

## Task 2: Database Module

**Files:**
- Create: `db.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_db.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'db'`

- [ ] **Step 3: Implement db.py**

```python
import os
import sqlite3

DB_PATH = os.getenv("DB_PATH", "index.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_db.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add db.py tests/test_db.py
git commit -m "feat: SQLite schema with FTS5"
```

---

## Task 3: MoJ API Client

**Files:**
- Create: `api/moj.py`
- Create: `tests/test_moj.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_moj.py`:

```python
import pytest
import httpx
from unittest.mock import patch, MagicMock

from api.moj import search_decisions, get_committees, get_appraisers, get_versions, pdf_url, HEADERS


def test_pdf_url_builds_correctly():
    token = "abc123"
    url = pdf_url(token)
    assert url.endswith("/abc123")
    assert "free-justice.openapi.gov.il" in url


def test_search_decisions_sends_correct_body():
    mock_response = MagicMock()
    mock_response.json.return_value = {"TotalResults": 0, "Results": []}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = search_decisions(skip=10, Committee="תל אביב-יפו", Block="6106")

    call_kwargs = mock_client.post.call_args
    body = call_kwargs[1]["json"]
    assert body["skip"] == 10
    assert body["Committee"] == "תל אביב-יפו"
    assert body["Block"] == "6106"
    assert "DecisiveAppraiser" not in body  # empty filters are excluded
    assert result == {"TotalResults": 0, "Results": []}


def test_search_decisions_uses_required_headers():
    mock_response = MagicMock()
    mock_response.json.return_value = {"TotalResults": 0, "Results": []}
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_client_cls.return_value = mock_client

        search_decisions(skip=0)

    headers = mock_client.post.call_args[1]["headers"]
    assert headers["x-client-id"] == "149a5bad-edde-49a6-9fb9-188bd17d4788"
    assert "gov.il" in headers["origin"]


def test_get_committees_returns_list():
    mock_response = MagicMock()
    mock_response.json.return_value = ["תל אביב-יפו", "ירושלים"]
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.get.return_value = mock_response
        mock_client_cls.return_value = mock_client

        result = get_committees()

    assert result == ["תל אביב-יפו", "ירושלים"]
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_moj.py -v
```

Expected: `ModuleNotFoundError: No module named 'api.moj'`

- [ ] **Step 3: Implement api/moj.py**

```python
import httpx

BASE_URL = (
    "https://pub-justice.openapi.gov.il/pub/moj/portal/rest"
    "/searchpredefinedapi/v1/SearchPredefinedApi/DecisiveAppraiser"
)
PDF_BASE_URL = (
    "https://free-justice.openapi.gov.il/free/moj/portal/rest"
    "/searchpredefinedapi/v1/SearchPredefinedApi/Documents/DecisiveAppraiser"
)

HEADERS = {
    "accept": "application/json",
    "content-type": "application/json;charset=UTF-8",
    "x-client-id": "149a5bad-edde-49a6-9fb9-188bd17d4788",
    "referer": "https://www.gov.il/he/departments/dynamiccollectors/decisive_appraisal_decisions?skip=0",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "origin": "https://www.gov.il",
}


def search_decisions(skip: int = 0, **filters) -> dict:
    body = {"skip": skip, **{k: v for k, v in filters.items() if v}}
    with httpx.Client(timeout=30) as client:
        r = client.post(f"{BASE_URL}/SearchDecisions", json=body, headers=HEADERS)
        r.raise_for_status()
        return r.json()


def get_committees() -> list:
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BASE_URL}/CommiteesList", headers=HEADERS)
        r.raise_for_status()
        return r.json()


def get_appraisers() -> list:
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BASE_URL}/DecisiveAppraisersList", headers=HEADERS)
        r.raise_for_status()
        return r.json()


def get_versions() -> list:
    with httpx.Client(timeout=30) as client:
        r = client.get(f"{BASE_URL}/AppraisalVersions", headers=HEADERS)
        r.raise_for_status()
        return r.json()


def pdf_url(token: str) -> str:
    return f"{PDF_BASE_URL}/{token}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_moj.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add api/moj.py tests/test_moj.py
git commit -m "feat: MoJ API client"
```

---

## Task 4: PDF Downloader

**Files:**
- Create: `api/downloader.py`
- Create: `tests/test_downloader.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_downloader.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_downloader.py -v
```

Expected: `ModuleNotFoundError: No module named 'api.downloader'`

- [ ] **Step 3: Implement api/downloader.py**

```python
import os
import re
import sqlite3
import httpx
from pathlib import Path

PDFS_DIR = Path(os.getenv("PDFS_DIR", "pdfs"))


def _safe(s: str) -> str:
    """Strip characters unsafe for filenames (keep Hebrew, alphanumeric, dash)."""
    return re.sub(r'[^\w\u0590-\u05ff\-]', '_', s or "unknown").strip("_") or "unknown"


def local_path(committee: str, decision_date: str, block: str, plot: str, appraiser: str) -> Path:
    date_str = (decision_date or "")[:10] or "unknown"
    last_name = (appraiser or "").split()[-1] if appraiser else "unknown"
    filename = f"{date_str}-gush{_safe(block)}-chelka{_safe(plot)}-{_safe(last_name)}.pdf"
    return PDFS_DIR / _safe(committee) / filename


def download_pdf(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60) as client:
        r = client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


def index_decision(conn: sqlite3.Connection, data: dict, path: str) -> int:
    cursor = conn.execute(
        """INSERT OR IGNORE INTO decisions
           (filename, committee, appraiser, block, plot,
            appraisal_type, appraisal_version, decision_date, local_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("AppraisalHeader", ""),
            data.get("Committee", ""),
            data.get("DecisiveAppraiser", ""),
            data.get("Block", ""),
            data.get("Plot", ""),
            data.get("AppraisalType", ""),
            data.get("AppraisalVersion", ""),
            data.get("DecisionDate", ""),
            path,
        ),
    )
    conn.commit()
    return cursor.lastrowid
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_downloader.py -v
```

Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add api/downloader.py tests/test_downloader.py
git commit -m "feat: PDF downloader with SQLite indexing"
```

---

## Task 5: OCR Pipeline

**Files:**
- Create: `api/ocr.py`
- Create: `tests/test_ocr.py`
- Create: `tests/fixtures/simple.pdf` (generated in test)

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ocr.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_ocr.py -v
```

Expected: `ModuleNotFoundError: No module named 'api.ocr'`

- [ ] **Step 3: Implement api/ocr.py**

```python
import sqlite3
from pathlib import Path


def extract_text_pdfplumber(path: Path) -> str:
    import pdfplumber
    parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
    return "\n".join(parts)


def extract_text_tesseract(path: Path) -> str:
    from pdf2image import convert_from_path
    import pytesseract
    images = convert_from_path(str(path))
    return "\n".join(
        pytesseract.image_to_string(img, lang="heb+eng") for img in images
    )


def ocr_pdf(path: Path) -> str:
    text = extract_text_pdfplumber(path)
    if len(text.strip()) < 100:
        text = extract_text_tesseract(path)
    return text


def store_ocr(conn: sqlite3.Connection, decision_id: int, text: str):
    conn.execute(
        "INSERT OR REPLACE INTO decision_text(rowid, text) VALUES (?, ?)",
        (decision_id, text),
    )
    conn.execute(
        "UPDATE decisions SET ocr_status='done' WHERE id=?",
        (decision_id,),
    )
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_ocr.py -v
```

Expected: 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add api/ocr.py tests/test_ocr.py
git commit -m "feat: OCR pipeline with pdfplumber + tesseract fallback"
```

---

## Task 6: Claude Integration

**Files:**
- Create: `api/claude.py`
- Create: `tests/test_claude.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_claude.py`:

```python
import os
import pytest
from unittest.mock import patch, MagicMock

os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"

from api.claude import analyze_stream, SYSTEM_PROMPT


def test_system_prompt_is_hebrew():
    assert "עברית" in SYSTEM_PROMPT or "שמאי" in SYSTEM_PROMPT


def test_analyze_stream_yields_chunks():
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter(["chunk1", " chunk2", " chunk3"])

    with patch("api.claude.client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream_ctx
        chunks = list(analyze_stream("some text", "סכם"))

    assert chunks == ["chunk1", " chunk2", " chunk3"]


def test_analyze_stream_passes_text_in_message():
    mock_stream_ctx = MagicMock()
    mock_stream_ctx.__enter__ = MagicMock(return_value=mock_stream_ctx)
    mock_stream_ctx.__exit__ = MagicMock(return_value=False)
    mock_stream_ctx.text_stream = iter([])

    with patch("api.claude.client") as mock_client:
        mock_client.messages.stream.return_value = mock_stream_ctx
        list(analyze_stream("decision text here", "מה השווי?"))

    call_kwargs = mock_client.messages.stream.call_args[1]
    user_content = call_kwargs["messages"][0]["content"]
    assert "decision text here" in user_content
    assert "מה השווי?" in user_content
    assert call_kwargs["model"] == "claude-opus-4-6"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_claude.py -v
```

Expected: `ModuleNotFoundError: No module named 'api.claude'`

- [ ] **Step 3: Implement api/claude.py**

```python
import os
from typing import Generator
import anthropic

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = (
    "אתה עוזר מומחה בניתוח הכרעות שמאי מכריע ישראלי. "
    "תענה בעברית אלא אם המשתמש מבקש אחרת. "
    "היה תמציתי, מדויק ומקצועי."
)


def analyze_stream(text: str, prompt: str) -> Generator[str, None, None]:
    messages = [
        {
            "role": "user",
            "content": f"להלן טקסט ההכרעה:\n\n{text}\n\n{prompt}",
        }
    ]
    with client.messages.stream(
        model="claude-opus-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages,
    ) as stream:
        for chunk in stream.text_stream:
            yield chunk
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_claude.py -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Run all tests to confirm no regressions**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 6: Commit**

```bash
git add api/claude.py tests/test_claude.py
git commit -m "feat: Claude streaming analysis integration"
```

---

## Task 7: FastAPI Server

**Files:**
- Create: `server.py`

- [ ] **Step 1: Create server.py**

```python
import asyncio
import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from db import init_db, get_db
from api.moj import search_decisions, get_committees, get_appraisers, get_versions, pdf_url
from api.downloader import local_path as make_local_path, download_pdf, index_decision
from api.ocr import ocr_pdf, store_ocr
from api.claude import analyze_stream

app = FastAPI(title="שמאי מכריע")


@app.on_event("startup")
def startup():
    init_db()
    Path(os.getenv("PDFS_DIR", "pdfs")).mkdir(exist_ok=True)


@app.get("/api/search")
def api_search(
    skip: int = 0,
    Committee: Optional[str] = None,
    DecisiveAppraiser: Optional[str] = None,
    AppraisalType: Optional[str] = None,
    AppraisalVersion: Optional[str] = None,
    Block: Optional[str] = None,
    Plot: Optional[str] = None,
    DateFrom: Optional[str] = None,
    DateTo: Optional[str] = None,
    FreeText: Optional[str] = None,
):
    filters = {k: v for k, v in {
        "Committee": Committee, "DecisiveAppraiser": DecisiveAppraiser,
        "AppraisalType": AppraisalType, "AppraisalVersion": AppraisalVersion,
        "Block": Block, "Plot": Plot, "DateFrom": DateFrom,
        "DateTo": DateTo, "FreeText": FreeText,
    }.items() if v}
    return search_decisions(skip=skip, **filters)


@app.get("/api/filters")
def api_filters():
    return {
        "committees": get_committees(),
        "appraisers": get_appraisers(),
        "versions": get_versions(),
    }


@app.post("/api/download")
def api_download(body: dict):
    data = body.get("data", body)
    docs = data.get("Document", [])
    if not docs:
        return JSONResponse({"error": "no documents"}, status_code=400)

    token = docs[0]["FileName"].split("/")[-1]
    url = pdf_url(token)
    dest = make_local_path(
        data.get("Committee", ""),
        data.get("DecisionDate", ""),
        data.get("Block", ""),
        data.get("Plot", ""),
        data.get("DecisiveAppraiser", ""),
    )

    if dest.exists():
        return {"status": "exists", "path": str(dest)}

    download_pdf(url, dest)

    conn = get_db()
    row_id = index_decision(conn, data, str(dest))
    conn.close()

    return {"status": "ok", "path": str(dest), "id": row_id}


@app.get("/api/bulk")
async def api_bulk(
    Committee: Optional[str] = None,
    DecisiveAppraiser: Optional[str] = None,
    AppraisalType: Optional[str] = None,
    AppraisalVersion: Optional[str] = None,
    DateFrom: Optional[str] = None,
    DateTo: Optional[str] = None,
    max_results: int = 100,
    auto_ocr: bool = False,
    skip_existing: bool = True,
):
    filters = {k: v for k, v in {
        "Committee": Committee, "DecisiveAppraiser": DecisiveAppraiser,
        "AppraisalType": AppraisalType, "AppraisalVersion": AppraisalVersion,
        "DateFrom": DateFrom, "DateTo": DateTo,
    }.items() if v}

    async def generate():
        downloaded = errors = skip = 0

        while downloaded < max_results:
            batch = search_decisions(skip=skip, **filters)
            results = batch.get("Results", [])
            if not results:
                break

            for item in results:
                if downloaded >= max_results:
                    break
                data = item["Data"]
                docs = data.get("Document", [])
                if not docs:
                    continue

                token = docs[0]["FileName"].split("/")[-1]
                url = pdf_url(token)
                dest = make_local_path(
                    data.get("Committee", ""),
                    data.get("DecisionDate", ""),
                    data.get("Block", ""),
                    data.get("Plot", ""),
                    data.get("DecisiveAppraiser", ""),
                )
                name = data.get("AppraisalHeader", dest.name)

                if skip_existing and dest.exists():
                    yield f"data: {json.dumps({'status': 'skip', 'name': name})}\n\n"
                    continue

                yield f"data: {json.dumps({'status': 'downloading', 'name': name})}\n\n"

                try:
                    download_pdf(url, dest)
                    conn = get_db()
                    row_id = index_decision(conn, data, str(dest))
                    if auto_ocr and row_id:
                        text = ocr_pdf(dest)
                        store_ocr(conn, row_id, text)
                    conn.close()
                    downloaded += 1
                    yield f"data: {json.dumps({'status': 'ok', 'name': name, 'downloaded': downloaded, 'errors': errors})}\n\n"
                except Exception as e:
                    errors += 1
                    yield f"data: {json.dumps({'status': 'error', 'name': name, 'error': str(e), 'errors': errors})}\n\n"

                await asyncio.sleep(0.05)

            skip += len(results)
            if len(results) < 10:
                break

        yield f"data: {json.dumps({'status': 'done', 'downloaded': downloaded, 'errors': errors})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/ocr")
def api_ocr(body: dict):
    path = Path(body["path"])
    if not path.exists():
        return JSONResponse({"error": "file not found"}, status_code=404)

    conn = get_db()
    row = conn.execute("SELECT id FROM decisions WHERE local_path=?", (str(path),)).fetchone()
    if not row:
        return JSONResponse({"error": "not in index"}, status_code=404)

    conn.execute("UPDATE decisions SET ocr_status='pending' WHERE id=?", (row["id"],))
    conn.commit()

    text = ocr_pdf(path)
    store_ocr(conn, row["id"], text)
    conn.close()

    return {"status": "ok", "chars": len(text)}


@app.post("/api/analyze")
def api_analyze(body: dict):
    path = body.get("path")
    prompt = body.get("prompt", "סכם את ההכרעה בצורה תמציתית")

    conn = get_db()
    row = conn.execute(
        "SELECT dt.text FROM decision_text dt JOIN decisions d ON dt.rowid=d.id WHERE d.local_path=?",
        (path,),
    ).fetchone()
    conn.close()

    if not row or not row["text"]:
        return JSONResponse({"error": "no OCR text — run OCR first"}, status_code=400)

    def generate():
        for chunk in analyze_stream(row["text"], prompt):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/library")
def api_library(
    q: Optional[str] = None,
    committee: Optional[str] = None,
    appraiser: Optional[str] = None,
):
    conn = get_db()

    if q:
        rows = conn.execute(
            """SELECT d.* FROM decisions d
               JOIN decision_text dt ON dt.rowid = d.id
               WHERE decision_text MATCH ?
               ORDER BY d.downloaded_at DESC""",
            (q,),
        ).fetchall()
    else:
        clauses, params = ["1=1"], []
        if committee:
            clauses.append("committee=?")
            params.append(committee)
        if appraiser:
            clauses.append("appraiser=?")
            params.append(appraiser)
        rows = conn.execute(
            f"SELECT * FROM decisions WHERE {' AND '.join(clauses)} ORDER BY downloaded_at DESC",
            params,
        ).fetchall()

    conn.close()
    return {"results": [dict(r) for r in rows]}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
```

- [ ] **Step 2: Create static/ directory**

```bash
mkdir -p static
```

- [ ] **Step 3: Smoke-test the server starts**

```bash
uvicorn server:app --reload --port 8000 &
sleep 2
curl -s http://localhost:8000/api/filters | python3 -m json.tool | head -5
kill %1
```

Expected: JSON response with `committees`, `appraisers`, `versions` keys (values from MoJ API).

- [ ] **Step 4: Commit**

```bash
git add server.py static/
git commit -m "feat: FastAPI server with all routes"
```

---

## Task 8: Frontend HTML + CSS

**Files:**
- Create: `static/index.html`
- Create: `static/style.css`

- [ ] **Step 1: Create static/style.css**

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #0f172a;
  --surface: #1e293b;
  --border: #334155;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --dim: #64748b;
  --blue: #3b82f6;
  --purple: #8b5cf6;
  --green: #22c55e;
  --amber: #f59e0b;
  --red: #ef4444;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  font-size: 14px;
  direction: rtl;
  min-height: 100vh;
}

/* Header */
.app-header {
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 0 20px;
  display: flex;
  align-items: center;
  gap: 0;
}

.app-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  padding: 14px 0;
  margin-left: 24px;
}

.tabs {
  display: flex;
  gap: 0;
}

.tab {
  padding: 14px 20px;
  font-size: 13px;
  color: var(--dim);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
  user-select: none;
}

.tab:hover { color: var(--text); }
.tab.active { color: var(--blue); border-bottom-color: var(--blue); font-weight: 600; }

/* Tab panels */
.panel { display: none; padding: 16px 20px; }
.panel.active { display: block; }

/* Filter bar */
.filter-bar {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: flex-end;
  margin-bottom: 14px;
}

.field { display: flex; flex-direction: column; gap: 4px; }
.field label { font-size: 11px; color: var(--dim); }

input, select {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 6px 9px;
  color: var(--text);
  font-size: 12px;
  direction: rtl;
  outline: none;
  transition: border-color 0.15s;
}
input:focus, select:focus { border-color: var(--blue); }
input::placeholder { color: var(--dim); }

/* Buttons */
.btn {
  padding: 7px 16px;
  border-radius: 5px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.15s;
}
.btn:hover { opacity: 0.85; }
.btn:disabled { opacity: 0.45; cursor: not-allowed; }
.btn-primary { background: var(--blue); color: #fff; }
.btn-secondary { background: var(--surface); color: var(--muted); border: 1px solid var(--border); }
.btn-purple { background: var(--purple); color: #fff; }
.btn-danger { background: var(--red); color: #fff; }

/* Results meta */
.results-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  color: var(--dim);
  font-size: 12px;
}

/* Table */
.results-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.results-table th {
  text-align: right;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  color: var(--dim);
  font-weight: 500;
}
.results-table td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--surface);
  vertical-align: middle;
}
.results-table tr:hover td { background: rgba(255,255,255,0.02); }

.badge {
  display: inline-block;
  padding: 2px 7px;
  border-radius: 3px;
  font-size: 10px;
  font-weight: 500;
}
.badge-original { background: #1e3a5f; color: #60a5fa; }
.badge-revised { background: #2d1b69; color: #a78bfa; }

.action-link {
  color: var(--blue);
  cursor: pointer;
  font-size: 11px;
  margin-left: 10px;
  text-decoration: none;
}
.action-link:hover { text-decoration: underline; }
.action-link.purple { color: var(--purple); }
.action-link.green { color: var(--green); }

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 16px;
}
.page-btn {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 5px 12px;
  color: var(--muted);
  cursor: pointer;
  font-size: 12px;
}
.page-btn.active { background: var(--blue); color: #fff; border-color: var(--blue); }
.page-btn:hover:not(.active) { border-color: var(--blue); color: var(--text); }

/* Bulk layout */
.bulk-layout {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.bulk-config {
  width: 240px;
  flex-shrink: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.bulk-config h3 { font-size: 13px; margin-bottom: 14px; }
.bulk-config .field { margin-bottom: 10px; }
.bulk-config select, .bulk-config input { width: 100%; }

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  cursor: pointer;
}
.checkbox-row input[type=checkbox] { width: 14px; height: 14px; accent-color: var(--blue); }
.checkbox-row label { font-size: 12px; color: var(--text); cursor: pointer; }

.bulk-progress { flex: 1; }
.progress-bar-wrap {
  background: var(--surface);
  border-radius: 4px;
  height: 6px;
  margin-bottom: 14px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.progress-bar-fill {
  background: linear-gradient(90deg, var(--blue), #60a5fa);
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s;
  width: 0%;
}

.stats-row {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
}
.stat-box {
  flex: 1;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px;
  text-align: center;
}
.stat-num { font-size: 20px; font-weight: 700; }
.stat-label { font-size: 10px; color: var(--dim); margin-top: 2px; }

.log-box {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 12px;
  font-family: monospace;
  font-size: 11px;
  max-height: 260px;
  overflow-y: auto;
  direction: rtl;
}
.log-ok { color: var(--green); }
.log-err { color: var(--amber); }
.log-downloading { color: var(--blue); }
.log-skip { color: var(--dim); }

/* Library */
.library-bar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}
.library-bar input { flex: 1; }
.library-stats { color: var(--dim); font-size: 12px; white-space: nowrap; }

.filter-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.chip {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 3px 10px;
  font-size: 11px;
  color: var(--dim);
  cursor: pointer;
}
.chip.active { background: #1e3a5f; color: #60a5fa; border-color: #3b82f6; }

/* Claude panel */
.claude-panel {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 14px;
  margin-top: 14px;
}
.claude-panel h4 { color: var(--purple); font-size: 12px; margin-bottom: 10px; }
.prompt-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.prompt-chip {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 5px 10px;
  font-size: 11px;
  color: var(--muted);
  cursor: pointer;
}
.prompt-chip:hover { border-color: var(--purple); color: var(--purple); }
.prompt-input-row {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}
.prompt-input-row input { flex: 1; }
.claude-response {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 10px 12px;
  font-size: 12px;
  line-height: 1.7;
  color: var(--text);
  min-height: 60px;
  white-space: pre-wrap;
}
.ocr-status-done { color: var(--green); font-size: 11px; }
.ocr-status-pending { color: var(--amber); font-size: 11px; }
.ocr-status-none { color: var(--dim); font-size: 11px; }

/* Utility */
.hidden { display: none !important; }
.mt-8 { margin-top: 8px; }
.section-title { font-size: 13px; font-weight: 600; margin-bottom: 12px; color: var(--text); }
```

- [ ] **Step 2: Create static/index.html**

```html
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>שמאי מכריע</title>
  <link rel="stylesheet" href="/style.css">
</head>
<body>

<header class="app-header">
  <span class="app-title">הכרעות שמאי מכריע</span>
  <nav class="tabs">
    <div class="tab active" data-tab="search">חיפוש</div>
    <div class="tab" data-tab="bulk">הורדה מרוכזת</div>
    <div class="tab" data-tab="library">הספרייה שלי</div>
  </nav>
</header>

<!-- ===== SEARCH TAB ===== -->
<div class="panel active" id="panel-search">
  <div class="filter-bar">
    <div class="field">
      <label>ועדה</label>
      <select id="s-committee"><option value="">הכל</option></select>
    </div>
    <div class="field">
      <label>שמאי מכריע</label>
      <select id="s-appraiser"><option value="">הכל</option></select>
    </div>
    <div class="field">
      <label>גרסת שומה</label>
      <select id="s-version"><option value="">הכל</option></select>
    </div>
    <div class="field">
      <label>גוש</label>
      <input id="s-block" type="text" placeholder="6106" style="width:70px">
    </div>
    <div class="field">
      <label>חלקה</label>
      <input id="s-plot" type="text" placeholder="316" style="width:60px">
    </div>
    <div class="field">
      <label>מתאריך</label>
      <input id="s-from" type="date">
    </div>
    <div class="field">
      <label>עד תאריך</label>
      <input id="s-to" type="date">
    </div>
    <div class="field">
      <label>טקסט חופשי</label>
      <input id="s-text" type="text" placeholder="חיפוש..." style="min-width:140px">
    </div>
    <button class="btn btn-primary" style="align-self:flex-end" onclick="doSearch(0)">חפש</button>
  </div>

  <div class="results-meta">
    <span id="s-count" style="color:var(--dim)">—</span>
    <button class="btn btn-secondary" onclick="downloadPage()" id="btn-dl-page">הורד עמוד זה</button>
  </div>

  <table class="results-table">
    <thead>
      <tr>
        <th>כותרת</th>
        <th>שמאי</th>
        <th>ועדה</th>
        <th>תאריך</th>
        <th>גרסה</th>
        <th>פעולות</th>
      </tr>
    </thead>
    <tbody id="s-results"></tbody>
  </table>

  <div class="pagination" id="s-pagination"></div>
</div>

<!-- ===== BULK TAB ===== -->
<div class="panel" id="panel-bulk">
  <div class="bulk-layout">
    <div class="bulk-config">
      <h3>הגדרות הורדה</h3>
      <div class="field"><label>ועדה</label><select id="b-committee"><option value="">הכל</option></select></div>
      <div class="field"><label>שמאי מכריע</label><select id="b-appraiser"><option value="">הכל</option></select></div>
      <div class="field"><label>גרסת שומה</label><select id="b-version"><option value="">הכל</option></select></div>
      <div class="field"><label>מתאריך</label><input id="b-from" type="date"></div>
      <div class="field"><label>עד תאריך</label><input id="b-to" type="date"></div>
      <div class="field">
        <label>מקסימום קבצים</label>
        <input id="b-max" type="number" value="100" min="1" max="5000">
      </div>
      <div class="checkbox-row">
        <input type="checkbox" id="b-ocr" checked>
        <label for="b-ocr">הפעל OCR אוטומטית</label>
      </div>
      <div class="checkbox-row">
        <input type="checkbox" id="b-skip" checked>
        <label for="b-skip">דלג על קבצים קיימים</label>
      </div>
      <button class="btn btn-primary" style="width:100%;margin-top:6px" id="btn-bulk-start" onclick="startBulk()">▶ התחל הורדה</button>
      <button class="btn btn-danger hidden" style="width:100%;margin-top:6px" id="btn-bulk-stop" onclick="stopBulk()">■ עצור</button>
    </div>

    <div class="bulk-progress">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <span class="section-title">התקדמות</span>
        <span id="b-pct" style="color:var(--dim);font-size:12px">—</span>
      </div>
      <div class="progress-bar-wrap"><div class="progress-bar-fill" id="b-bar"></div></div>
      <div class="stats-row">
        <div class="stat-box"><div class="stat-num" id="b-dl" style="color:var(--green)">0</div><div class="stat-label">הורדו</div></div>
        <div class="stat-box"><div class="stat-num" id="b-err" style="color:var(--amber)">0</div><div class="stat-label">שגיאות</div></div>
        <div class="stat-box"><div class="stat-num" id="b-rem" style="color:var(--muted)">—</div><div class="stat-label">נותרו</div></div>
      </div>
      <div class="log-box" id="b-log"></div>
    </div>
  </div>
</div>

<!-- ===== LIBRARY TAB ===== -->
<div class="panel" id="panel-library">
  <div class="library-bar">
    <input id="lib-search" type="text" placeholder="חיפוש בטקסט מלא בתוך PDF..." oninput="debounceLibSearch()">
    <span class="library-stats" id="lib-stats">טוען...</span>
  </div>

  <div class="filter-chips" id="lib-chips"></div>

  <table class="results-table">
    <thead>
      <tr>
        <th>קובץ</th>
        <th>ועדה</th>
        <th>שמאי</th>
        <th>תאריך</th>
        <th>OCR</th>
        <th>פעולות</th>
      </tr>
    </thead>
    <tbody id="lib-results"></tbody>
  </table>

  <div id="claude-panel" class="claude-panel hidden">
    <h4>✦ Claude — <span id="claude-filename"></span></h4>
    <div class="prompt-chips">
      <div class="prompt-chip" onclick="sendPrompt('סכם את ההכרעה בצורה תמציתית')">סכם את ההכרעה</div>
      <div class="prompt-chip" onclick="sendPrompt('מה שווי הנכס שנקבע בהכרעה?')">מה שווי הנכס?</div>
      <div class="prompt-chip" onclick="sendPrompt('מהן נקודות המפתח של ההכרעה?')">נקודות מפתח</div>
      <div class="prompt-chip" onclick="sendPrompt('כמה היטל השבחה נקבע ומה הנימוקים?')">גובה ההיטל</div>
    </div>
    <div class="prompt-input-row">
      <input id="claude-input" type="text" placeholder="שאל שאלה על ההכרעה...">
      <button class="btn btn-purple" onclick="sendCustomPrompt()">שלח</button>
    </div>
    <div class="claude-response" id="claude-response"></div>
  </div>
</div>

<script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 3: Verify HTML loads in browser**

```bash
uvicorn server:app --reload --port 8000
```

Open http://localhost:8000 — expect a dark Hebrew 3-tab page with empty tables (no JS yet).

- [ ] **Step 4: Commit**

```bash
git add static/index.html static/style.css
git commit -m "feat: frontend HTML shell and dark RTL CSS"
```

---

## Task 9: Frontend JavaScript

**Files:**
- Create: `static/app.js`

- [ ] **Step 1: Create static/app.js**

```javascript
// ─── State ──────────────────────────────────────────────────────────────────
let currentSkip = 0;
let currentTotal = 0;
let currentResults = [];
let bulkSource = null;
let activePdfPath = null;
let libSearchTimer = null;

const PAGE_SIZE = 10;

// ─── Tab routing ─────────────────────────────────────────────────────────────
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
    if (tab.dataset.tab === 'library') loadLibrary();
  });
});

// ─── Boot ────────────────────────────────────────────────────────────────────
async function boot() {
  try {
    const data = await apiFetch('/api/filters');
    populateSelect('s-committee', data.committees);
    populateSelect('s-appraiser', data.appraisers);
    populateSelect('s-version', data.versions);
    populateSelect('b-committee', data.committees);
    populateSelect('b-appraiser', data.appraisers);
    populateSelect('b-version', data.versions);
  } catch (e) {
    console.error('Failed to load filters:', e);
  }
}

function populateSelect(id, items) {
  const sel = document.getElementById(id);
  (items || []).forEach(item => {
    const opt = document.createElement('option');
    opt.value = item;
    opt.textContent = item;
    sel.appendChild(opt);
  });
}

// ─── Search tab ──────────────────────────────────────────────────────────────
async function doSearch(skip) {
  currentSkip = skip;
  const params = new URLSearchParams({ skip });
  const add = (k, id) => { const v = document.getElementById(id)?.value; if (v) params.set(k, v); };
  add('Committee', 's-committee');
  add('DecisiveAppraiser', 's-appraiser');
  add('AppraisalVersion', 's-version');
  add('Block', 's-block');
  add('Plot', 's-plot');
  add('DateFrom', 's-from');
  add('DateTo', 's-to');
  add('FreeText', 's-text');

  const data = await apiFetch('/api/search?' + params.toString());
  currentTotal = data.TotalResults || 0;
  currentResults = data.Results || [];

  document.getElementById('s-count').textContent =
    currentTotal.toLocaleString('he-IL') + ' תוצאות';

  renderSearchResults(currentResults);
  renderPagination(skip, currentTotal);
}

function renderSearchResults(results) {
  const tbody = document.getElementById('s-results');
  tbody.innerHTML = '';
  results.forEach(item => {
    const d = item.Data;
    const date = (d.DecisionDate || '').slice(0, 10);
    const isOriginal = (d.AppraisalVersion || '').includes('מקורית');
    const badgeClass = isOriginal ? 'badge-original' : 'badge-revised';
    const badgeText = isOriginal ? 'מקורית' : 'מתוקנת';

    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${esc(d.AppraisalHeader || '')}</td>
      <td style="color:var(--muted)">${esc(d.DecisiveAppraiser || '')}</td>
      <td style="color:var(--muted)">${esc(d.Committee || '')}</td>
      <td style="color:var(--muted)">${date}</td>
      <td><span class="badge ${badgeClass}">${badgeText}</span></td>
      <td>
        <a class="action-link" onclick='downloadOne(${JSON.stringify(d)})'>↓ PDF</a>
        <a class="action-link purple" onclick='analyzeFromSearch(${JSON.stringify(d)})'>Claude ✦</a>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function renderPagination(skip, total) {
  const container = document.getElementById('s-pagination');
  container.innerHTML = '';
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(skip / PAGE_SIZE);
  if (totalPages <= 1) return;

  const maxPages = 5;
  const start = Math.max(0, currentPage - 2);
  const end = Math.min(totalPages - 1, start + maxPages - 1);

  if (currentPage > 0) addPageBtn(container, currentPage - 1, '◀ הקודם');
  for (let i = start; i <= end; i++) addPageBtn(container, i, String(i + 1), i === currentPage);
  if (currentPage < totalPages - 1) addPageBtn(container, currentPage + 1, 'הבא ▶');
}

function addPageBtn(container, page, label, active = false) {
  const btn = document.createElement('div');
  btn.className = 'page-btn' + (active ? ' active' : '');
  btn.textContent = label;
  btn.onclick = () => doSearch(page * PAGE_SIZE);
  container.appendChild(btn);
}

async function downloadOne(data) {
  try {
    const res = await apiFetch('/api/download', { method: 'POST', body: JSON.stringify({ data }) });
    alert(res.status === 'exists' ? 'הקובץ כבר קיים: ' + res.path : 'הורד: ' + res.path);
  } catch (e) {
    alert('שגיאה בהורדה: ' + e.message);
  }
}

async function downloadPage() {
  for (const item of currentResults) {
    await downloadOne(item.Data);
  }
}

async function analyzeFromSearch(data) {
  // Download first if needed, then switch to library and open Claude panel
  try {
    const res = await apiFetch('/api/download', { method: 'POST', body: JSON.stringify({ data }) });
    activePdfPath = res.path;
    // Switch to library tab
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.querySelector('[data-tab="library"]').classList.add('active');
    document.getElementById('panel-library').classList.add('active');
    await loadLibrary();
    openClaudePanel(res.path, data.AppraisalHeader || res.path);
  } catch (e) {
    alert('שגיאה: ' + e.message);
  }
}

// ─── Bulk tab ────────────────────────────────────────────────────────────────
function startBulk() {
  const params = new URLSearchParams({
    max_results: document.getElementById('b-max').value || '100',
    auto_ocr: document.getElementById('b-ocr').checked ? 'true' : 'false',
    skip_existing: document.getElementById('b-skip').checked ? 'true' : 'false',
  });
  const add = (k, id) => { const v = document.getElementById(id)?.value; if (v) params.set(k, v); };
  add('Committee', 'b-committee');
  add('DecisiveAppraiser', 'b-appraiser');
  add('AppraisalVersion', 'b-version');
  add('DateFrom', 'b-from');
  add('DateTo', 'b-to');

  document.getElementById('btn-bulk-start').classList.add('hidden');
  document.getElementById('btn-bulk-stop').classList.remove('hidden');
  document.getElementById('b-log').innerHTML = '';

  const maxResults = parseInt(params.get('max_results'));
  let downloaded = 0, errors = 0;

  bulkSource = new EventSource('/api/bulk?' + params.toString());

  bulkSource.onmessage = (e) => {
    const msg = JSON.parse(e.data);

    if (msg.status === 'done') {
      stopBulk();
      addLog(`✓ הסתיים — ${msg.downloaded} הורדו, ${msg.errors} שגיאות`, 'ok');
      return;
    }

    if (msg.downloaded !== undefined) downloaded = msg.downloaded;
    if (msg.errors !== undefined) errors = msg.errors;

    const pct = maxResults > 0 ? Math.round((downloaded / maxResults) * 100) : 0;
    document.getElementById('b-bar').style.width = pct + '%';
    document.getElementById('b-pct').textContent = `${downloaded} / ${maxResults} • ${pct}%`;
    document.getElementById('b-dl').textContent = downloaded;
    document.getElementById('b-err').textContent = errors;
    document.getElementById('b-rem').textContent = maxResults - downloaded;

    const cls = { ok: 'ok', error: 'err', downloading: 'downloading', skip: 'skip' }[msg.status] || '';
    const prefix = { ok: '✓', error: '⚠', downloading: '⟳', skip: '—' }[msg.status] || '';
    addLog(`${prefix} ${msg.name}${msg.error ? ' — ' + msg.error : ''}`, cls);
  };

  bulkSource.onerror = () => {
    stopBulk();
    addLog('⚠ חיבור ל-server נותק', 'err');
  };
}

function stopBulk() {
  if (bulkSource) { bulkSource.close(); bulkSource = null; }
  document.getElementById('btn-bulk-start').classList.remove('hidden');
  document.getElementById('btn-bulk-stop').classList.add('hidden');
}

function addLog(text, cls) {
  const log = document.getElementById('b-log');
  const line = document.createElement('div');
  line.className = cls ? 'log-' + cls : '';
  line.textContent = text;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

// ─── Library tab ─────────────────────────────────────────────────────────────
async function loadLibrary(query = '', committee = '', appraiser = '') {
  const params = new URLSearchParams();
  if (query) params.set('q', query);
  if (committee) params.set('committee', committee);
  if (appraiser) params.set('appraiser', appraiser);

  const data = await apiFetch('/api/library?' + params.toString());
  const results = data.results || [];

  document.getElementById('lib-stats').textContent =
    results.length.toLocaleString('he-IL') + ' קבצים';

  const tbody = document.getElementById('lib-results');
  tbody.innerHTML = '';

  results.forEach(row => {
    const ocrStatus = row.ocr_status;
    const ocrHtml = ocrStatus === 'done'
      ? '<span class="ocr-status-done">✓ OCR</span>'
      : ocrStatus === 'pending'
      ? '<span class="ocr-status-pending">⟳ ממתין</span>'
      : '<span class="ocr-status-none">—</span>';

    const actions = ocrStatus === 'done'
      ? `<a class="action-link" onclick="openFile('${esc(row.local_path)}')">פתח</a>
         <a class="action-link purple" onclick="openClaudePanel('${esc(row.local_path)}','${esc(row.filename)}')">Claude ✦</a>`
      : `<a class="action-link" onclick="openFile('${esc(row.local_path)}')">פתח</a>
         <a class="action-link" style="color:var(--dim)" onclick="runOcr('${esc(row.local_path)}', this)">הפעל OCR</a>`;

    const date = (row.decision_date || '').slice(0, 10);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${esc(row.filename || '')}</td>
      <td style="color:var(--muted)">${esc(row.committee || '')}</td>
      <td style="color:var(--muted)">${esc(row.appraiser || '')}</td>
      <td style="color:var(--muted)">${date}</td>
      <td>${ocrHtml}</td>
      <td>${actions}</td>
    `;
    tbody.appendChild(tr);
  });
}

function debounceLibSearch() {
  clearTimeout(libSearchTimer);
  libSearchTimer = setTimeout(() => {
    loadLibrary(document.getElementById('lib-search').value);
  }, 350);
}

function openFile(path) {
  // Ask the server to open the file with the system viewer
  fetch('/api/open', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  }).catch(() => {});
}

async function runOcr(path, linkEl) {
  linkEl.textContent = 'מעבד...';
  linkEl.style.color = 'var(--amber)';
  try {
    await apiFetch('/api/ocr', { method: 'POST', body: JSON.stringify({ path }) });
    loadLibrary(document.getElementById('lib-search').value);
  } catch (e) {
    alert('שגיאת OCR: ' + e.message);
    linkEl.textContent = 'הפעל OCR';
    linkEl.style.color = '';
  }
}

// ─── Claude panel ─────────────────────────────────────────────────────────────
function openClaudePanel(path, filename) {
  activePdfPath = path;
  document.getElementById('claude-filename').textContent = filename;
  document.getElementById('claude-response').textContent = '';
  document.getElementById('claude-input').value = '';
  document.getElementById('claude-panel').classList.remove('hidden');
  document.getElementById('claude-panel').scrollIntoView({ behavior: 'smooth' });
}

function sendPrompt(prompt) {
  if (!activePdfPath) return;
  streamAnalysis(activePdfPath, prompt);
}

function sendCustomPrompt() {
  const prompt = document.getElementById('claude-input').value.trim();
  if (!prompt || !activePdfPath) return;
  streamAnalysis(activePdfPath, prompt);
}

async function streamAnalysis(path, prompt) {
  const responseEl = document.getElementById('claude-response');
  responseEl.textContent = '';

  const res = await fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, prompt }),
  });

  if (!res.ok) {
    const err = await res.json();
    responseEl.textContent = 'שגיאה: ' + (err.error || 'unknown');
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop();
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      const payload = line.slice(6).trim();
      if (payload === '[DONE]') return;
      try {
        const msg = JSON.parse(payload);
        if (msg.chunk) responseEl.textContent += msg.chunk;
      } catch {}
    }
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
async function apiFetch(url, opts = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

// ─── Boot ─────────────────────────────────────────────────────────────────────
boot();
```

- [ ] **Step 2: Add /api/open route to server.py**

Add this route to `server.py` before the `app.mount` line:

```python
import subprocess

@app.post("/api/open")
def api_open(body: dict):
    path = body.get("path", "")
    if path and Path(path).exists():
        subprocess.Popen(["open", path])  # macOS; use "xdg-open" on Linux
    return {"status": "ok"}
```

Also add `import subprocess` at the top of `server.py` (after existing imports).

- [ ] **Step 3: Run full integration test**

```bash
uvicorn server:app --reload --port 8000
```

Open http://localhost:8000 and verify:
1. Filter dropdowns populate with Hebrew committees/appraisers
2. Search for Committee "תל אביב-יפו" → results appear in table
3. Click "↓ PDF" on a result → file downloads to `pdfs/` directory
4. Switch to Library tab → downloaded file appears
5. Click "הפעל OCR" on a library row → status changes to ✓ OCR
6. Click "Claude ✦" on an OCR'd row → panel opens, try a preset prompt

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 5: Final commit**

```bash
git add static/app.js server.py
git commit -m "feat: complete frontend JS and open-file route"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Search tab with all filters | Task 9 (JS) + Task 7 (route) + Task 8 (HTML) |
| Per-row download + Claude actions | Task 9 |
| Bulk download with live progress (SSE) | Task 7 (/api/bulk) + Task 9 (bulkSource) |
| Auto-OCR option in bulk | Task 7 |
| Skip-existing option | Task 7 |
| Save PDFs to local disk organized by committee | Task 4 (local_path) |
| SQLite indexing of downloads | Task 4 (index_decision) |
| FTS5 full-text search | Task 2 (schema) + Task 7 (/api/library) |
| OCR via pdfplumber + pytesseract fallback | Task 5 |
| Store OCR text in FTS5 | Task 5 (store_ocr) |
| Claude streaming analysis | Task 6 + Task 7 (/api/analyze) |
| Preset prompts + custom input | Task 9 (claude panel) |
| Library tab with search + filter chips | Task 9 |
| Open PDF locally | Task 9 (openFile) + Task 7 (/api/open) |
| RTL Hebrew UI | Task 8 (html dir=rtl, CSS) |
| Dark theme | Task 8 (style.css) |
| .env for API key | Task 1 |
| Local-first (python server.py) | Task 7 |

**Placeholder scan:** No TBDs, TODOs, or vague steps found.

**Type consistency:** `index_decision` returns `cursor.lastrowid` (int) consistently used as `row_id` in Task 7. `local_path` returns `Path` consistently. `ocr_pdf` returns `str` fed into `store_ocr`. `analyze_stream` yields `str` chunks consumed by SSE generator. All consistent.
