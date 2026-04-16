# Architecture — שמאי מכריע

## Overview

A local-first web app that wraps the Israeli Ministry of Justice (MoJ) decisive appraiser API. Users search, download, OCR, and analyze PDF decisions via a browser UI.

## System Diagram

```
Browser (RTL Hebrew UI)
    │
    ▼
FastAPI (server.py) — port 8000
    │
    ├── /api/search      → MoJ SearchDecisions API (POST)
    ├── /api/filters     → MoJ CommiteesList / AppraisalVersions (GET, with fallbacks)
    ├── /api/download    → MoJ PDF download → local disk
    ├── /api/bulk        → streaming SSE bulk download
    ├── /api/ocr         → Tesseract OCR → SQLite FTS5
    ├── /api/analyze     → Claude API (streaming SSE)
    ├── /api/library     → SQLite query (with FTS5 full-text search)
    └── /api/open        → subprocess open (macOS Preview)
    │
    ├── MoJ API (pub-justice.openapi.gov.il)
    │       SearchDecisions — POST, works
    │       CommiteesList — broken (500), using fallback list
    │       DecisiveAppraisersList — broken (500), using fallback list
    │       AppraisalVersions — works (returns objects, not strings)
    │       Documents — PDF download via free-justice subdomain
    │
    ├── SQLite (index.db)
    │       decisions table — metadata index
    │       decision_text — FTS5 virtual table for full-text search
    │
    ├── Local filesystem (pdfs/)
    │       Organized as: pdfs/<committee>/<date>-gush<block>-chelka<plot>-<appraiser>.pdf
    │
    ├── Tesseract OCR (system binary)
    │       Hebrew language pack required
    │
    └── Anthropic Claude API (optional)
            claude-3-5-sonnet — streaming text generation
```

## Key Design Decisions

### Local-first
No cloud infra. PDFs, DB, and OCR all run on the user's machine. Trivial to set up, zero cost, works offline after download.

### Client-side date filtering
MoJ's `DateFrom`/`DateTo` fields return HTTP 500. We scan MoJ results page by page and filter `DecisionDate` and `PublicityDate` locally. Results are sorted by `PublicityDate` desc, enabling early exit on pub date lower bound.

### SSE streaming for bulk + analysis
Bulk download and Claude analysis use Server-Sent Events so the UI updates in real time without polling.

### Hardcoded dropdown fallbacks
MoJ committee and appraiser list endpoints are broken. Fallback lists were sampled from ~3,000 MoJ results and hardcoded in `api/moj.py`.

## Request Flow — Search with Date Filter

```
doSearch() → GET /api/search?Committee=X&DateFrom=Y
    → api_search() detects date params → client-side scan mode
    → loop: search_decisions(skip=0,10,20,...) until enough collected
    → filter each result by DecisionDate / PublicityDate
    → return page slice to browser
```

## Request Flow — Bulk Download

```
startBulk() → EventSource /api/bulk?...
    → api_bulk() async generator
    → loop: search_decisions() pages
    → for each: download_pdf() → index_decision() → [optional] ocr_pdf()
    → yield SSE events: downloading / ok / skip / error / done
```
