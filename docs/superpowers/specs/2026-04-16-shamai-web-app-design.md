# Shamai Web App — Design Spec
_Date: 2026-04-16_

## Overview

A local-first web app for searching, bulk-downloading, and analyzing decisive appraiser decisions (הכרעות שמאי מכריע) from the Israeli Ministry of Justice open API. Built with Python FastAPI + vanilla HTML/JS. Starts as a personal tool, designed to be shareable with a small team later.

---

## Goals

- Search the MoJ API with all available filters and download specific PDFs
- Bulk-harvest PDFs (hundreds at a time) with live progress feedback
- Store PDFs locally, organized by committee/date
- Run OCR on downloaded PDFs and index full text for local search
- Send PDFs/text to Claude for summarization and analysis
- Run locally (`python server.py`), deployable later to Railway/Render

---

## Architecture

Single Python process: FastAPI serves the HTML frontend and handles all backend operations.

```
shamai/
├── server.py               # FastAPI entry point, mounts static/, registers routes
├── api/
│   ├── moj.py              # MoJ API client (search, filters, pagination)
│   ├── downloader.py       # PDF fetch → local disk + SQLite index
│   ├── ocr.py              # pdfplumber (text PDFs) + pytesseract fallback (scanned)
│   └── claude.py           # Claude API integration (analyze, summarize)
├── static/
│   ├── index.html          # Single-page app, RTL (dir="rtl")
│   ├── app.js              # All frontend logic (tab routing, API calls, SSE)
│   └── style.css           # Dark theme, RTL-aware layout
├── pdfs/                   # Downloaded PDFs (gitignored)
│   └── {committee}/
│       └── {YYYY-MM-DD}-gush{block}-chelka{plot}-{appraiser}.pdf
└── index.db                # SQLite with FTS5 full-text search index
```

---

## API Routes

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/search` | Proxy MoJ search with filter params, returns paginated results |
| `GET` | `/api/filters` | Returns committees, appraisers, appraisal versions from MoJ |
| `POST` | `/api/download` | Download single PDF to disk, add to SQLite index |
| `GET` | `/api/bulk` | Server-Sent Events stream — bulk download with live progress |
| `POST` | `/api/ocr` | Run OCR on a local PDF, store extracted text in SQLite FTS5 |
| `POST` | `/api/analyze` | Send PDF text + prompt to Claude API, stream response |
| `GET` | `/api/library` | List/search local PDFs (supports full-text query via SQLite FTS5) |

---

## MoJ API Integration

**Base URL:** `https://pub-justice.openapi.gov.il/pub/moj/portal/rest/searchpredefinedapi/v1/SearchPredefinedApi/DecisiveAppraiser`

**Required headers (all requests):**
```json
{
  "accept": "application/json",
  "content-type": "application/json;charset=UTF-8",
  "x-client-id": "149a5bad-edde-49a6-9fb9-188bd17d4788",
  "referer": "https://www.gov.il/he/departments/dynamiccollectors/decisive_appraisal_decisions?skip=0",
  "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  "origin": "https://www.gov.il"
}
```

**Endpoints used:**
- `POST /SearchDecisions` — main search (skip, Committee, DecisiveAppraiser, AppraisalType, AppraisalVersion, Block, Plot, DateFrom, DateTo, FreeText)
- `GET /CommiteesList` — 135 committees
- `GET /DecisiveAppraisersList` — 56 appraisers
- `GET /AppraisalVersions` — שומה מקורית / שומה מתוקנת אחרי ערר

**PDF download base URL:**
`https://free-justice.openapi.gov.il/free/moj/portal/rest/searchpredefinedapi/v1/SearchPredefinedApi/Documents/DecisiveAppraiser/<token>`

---

## UI — 3 Tabs

All tabs use a dark theme, RTL layout (`dir="rtl"`), Hebrew labels.

### Tab 1: חיפוש (Search)

- **Top filter bar:** Committee (dropdown), Appraiser (dropdown), Appraisal type (dropdown), Block (text), Plot (text), Date from, Date to, Free text, Search button
- **Results table columns:** Title (AppraisalHeader), Appraiser, Committee, Date, Version badge (מקורית/מתוקנת), Actions
- **Per-row actions:** `↓ PDF` (download to disk), `Claude ✦` (open analysis panel)
- **Table header actions:** "Download all (this page)" button
- **Pagination:** Previous / page numbers / Next
- Result count shown above table

### Tab 2: הורדה מרוכזת (Bulk Download)

- **Left config panel:** Same filters as Search tab, Max files input, "Auto-OCR" checkbox, "Skip existing files" checkbox, Start button
- **Right progress panel:**
  - Progress bar (percentage)
  - Stats row: Downloaded / Errors / Remaining / ETA
  - Live streaming log (Server-Sent Events) — one line per file, color-coded: green (success), amber (warning/skip), blue (in-progress)
- Stop button appears once job is running

### Tab 3: הספרייה שלי (My Library)

- **Search bar:** Full-text search via SQLite FTS5 across all OCR-indexed PDFs
- **Filter chips:** Committee, Appraiser, Year — add/remove inline
- **Stats bar:** Total file count, total size on disk, "Open folder" button
- **Results table columns:** File title, Committee, Appraiser, Date, OCR status (✓ OCR / ⟳ Pending / — None), Actions
- **Per-row actions:** `פתח` (open PDF locally), `Claude ✦` or `הפעל OCR` depending on OCR status
- **Inline Claude panel** (expands at bottom when triggered): preset prompt chips (summarize, key points, property value) + free-form question input + streamed response

---

## Data Model (SQLite)

```sql
CREATE TABLE decisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  filename TEXT NOT NULL,
  committee TEXT,
  appraiser TEXT,
  block TEXT,
  plot TEXT,
  appraisal_type TEXT,
  appraisal_version TEXT,
  decision_date TEXT,
  local_path TEXT NOT NULL,
  downloaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
  ocr_status TEXT DEFAULT 'none'  -- 'none' | 'pending' | 'done'
);

CREATE VIRTUAL TABLE decision_text USING fts5(
  text,
  content=decisions,
  content_rowid=id
);
```

---

## OCR Pipeline

1. Try `pdfplumber` first — fast, works for text-based PDFs (most MoJ decisions are text PDFs)
2. Fall back to `pytesseract` (with `pdf2image`) if pdfplumber returns empty/minimal text
3. Store extracted text in `decision_text` FTS5 table linked to `decisions.id`
4. Update `ocr_status` to `'done'` on success

**Dependencies:** `pdfplumber`, `pytesseract`, `pdf2image`, `Pillow`
Note: pytesseract requires Tesseract installed locally (`brew install tesseract tesseract-lang`)

---

## Claude Integration

- Uses Claude API (Anthropic SDK) with `claude-opus-4-6` model
- Input: extracted OCR text (preferred) or raw PDF bytes as base64 if text unavailable
- Output: streamed response via SSE to the browser
- Preset prompts available as quick-fire chips in the UI
- API key loaded from `.env` (`ANTHROPIC_API_KEY`)

---

## File Organization

PDFs saved to:
```
pdfs/{committee}/{YYYY-MM-DD}-gush{block}-chelka{plot}-{appraiser_last_name}.pdf
```
Example: `pdfs/תל אביב-יפו/2025-08-24-gush6106-chelka316-מסילתי.pdf`

Duplicates detected by checking `local_path` in SQLite before downloading.

---

## Deployment Path

**Phase 1 — Local:**
- `pip install -r requirements.txt`
- `python server.py` → serves on `http://localhost:8000`
- PDFs stored in `./pdfs/`, DB at `./index.db`

**Phase 2 — Team (future):**
- Deploy to Railway or Render as a single container
- Mount `./pdfs/` as a persistent volume (or swap to Supabase Storage)
- Add simple password protection (HTTP Basic Auth or a static token in `.env`)
- No code changes needed to the core logic

---

## Dependencies

```
fastapi
uvicorn
httpx
pdfplumber
pytesseract
pdf2image
Pillow
anthropic
python-dotenv
```

---

## Out of Scope (this version)

- User accounts / multi-user auth
- Cloud storage for PDFs
- Structured data extraction (field-level parsing beyond OCR)
- Scheduled/automated ingestion
- Mobile-responsive design
