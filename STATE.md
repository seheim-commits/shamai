# STATE.md — שמאי מכריע

## Status
| Component | Status |
|-----------|--------|
| FastAPI server | Local only (no production host yet) |
| MoJ API | Connected — partial (date/list endpoints broken server-side) |
| SQLite DB | Local — `index.db` |
| PDF storage | Local — `pdfs/` |
| OCR | Working — requires Tesseract installed |
| Claude analysis | Optional — requires `ANTHROPIC_API_KEY` |
| GitHub repo | https://github.com/seheim-commits/shamai (public) |

## Local Dev
```bash
cd /Users/aviadstark/Desktop/Claude/Code/Projects/Shamai
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
# http://localhost:8000
```

## Environment Variables
| Var | Default | Required |
|-----|---------|----------|
| `ANTHROPIC_API_KEY` | — | No (only for Claude analysis) |
| `DB_PATH` | `index.db` | No |
| `PDFS_DIR` | `pdfs` | No |

## Branching
- `main` — production branch (only one branch currently; no staging)

## Session Log
- **2026-04-17** — Initial build + launch. Fixed MoJ API bugs (dates, dropdowns, SearchText). Added pub date + bulk free-text filters. Created README, CLAUDE.md. Published to GitHub.

## Known Issues
- No production hosting (VPS needed for multi-user access)
- `x-client-id` in `api/moj.py` borrowed from gov.il browser — may break if MoJ rotates it
- Date filtering is client-side (MoJ server-side date API is broken)
