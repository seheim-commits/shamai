# Project Index — שמאי מכריע

## Quick Start
```bash
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
# http://localhost:8000
```

## Documentation
| File | Purpose |
|------|---------|
| [README.md](README.md) | Setup guide for new users |
| [STATE.md](STATE.md) | Live infra status, URLs, env vars, session log |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, request flows |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | DB schema, filesystem layout, MoJ API shape |
| [docs/TECH_STACK.md](docs/TECH_STACK.md) | All dependencies and versions |
| [tasks/lessons.md](tasks/lessons.md) | Rules derived from bugs and corrections |
| [tasks/session-2026-04-17-handoff.md](tasks/session-2026-04-17-handoff.md) | Session handoff — what was built |

## Source Code
| File | Purpose |
|------|---------|
| [server.py](server.py) | FastAPI routes — search, download, bulk, OCR, analyze, library |
| [db.py](db.py) | SQLite connection + schema init |
| [api/moj.py](api/moj.py) | MoJ API client + fallback lists |
| [api/downloader.py](api/downloader.py) | PDF download + local path generation + DB indexing |
| [api/ocr.py](api/ocr.py) | Tesseract OCR + FTS5 storage |
| [api/claude.py](api/claude.py) | Claude API streaming |
| [static/index.html](static/index.html) | UI — search, bulk, library tabs |
| [static/app.js](static/app.js) | Frontend logic |
| [static/style.css](static/style.css) | RTL Hebrew styles |

## Config
| File | Purpose |
|------|---------|
| [.env.example](.env.example) | Environment variable template |
| [requirements.txt](requirements.txt) | Python dependencies |
| [CLAUDE.md](CLAUDE.md) | Auto-setup instructions for Claude Code users |
