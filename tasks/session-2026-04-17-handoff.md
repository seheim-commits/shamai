# Session Handoff — 2026-04-17

## Done ✅

### MoJ API Bug Fixes
- **FreeText → SearchText**: MoJ's `FreeText` field returns 500; correct field name is `SearchText`. Fixed in `api_search` and `api_bulk`.
- **Date filters broken server-side**: MoJ `DateFrom`/`DateTo` return 500. Implemented full client-side filtering in `api_search` — scans up to `MAX_SCAN=2000` results, filters `DecisionDate` and `PublicityDate` locally.
- **Early exit for PublicityDate**: MoJ sorts results descending by `PublicityDate`, so added early exit when `pub < pub_from` to avoid full scan.
- **Impossible date range short-circuit**: Returns empty immediately if `DateFrom > DateTo` or `PubDateFrom > PubDateTo`.
- **CommiteesList / DecisiveAppraisersList broken**: Both return 500. Added hardcoded fallback lists (65 committees, 31 appraisers) sampled from MoJ results at intervals.
- **AppraisalVersions returns objects**: Fixed `get_versions()` to extract `.Value` from each object and skip numeric entries.

### New Features
- **PublicityDate filters** added to both Search tab (`s-pub-from`, `s-pub-to`) and Bulk tab (`b-pub-from`, `b-pub-to`) — UI + server.
- **Free text search in Bulk tab** (`b-text`) — sends `SearchText` to MoJ, same as Search tab.

### Sharing / Distribution
- `README.md` — setup instructions including OS-level Tesseract install.
- `CLAUDE.md` — auto-setup script for Claude Code users: clone, install, configure, start, verify, print usage message in Hebrew. API key optional (only needed for Claude analysis feature).
- GitHub repo created: https://github.com/seheim-commits/shamai (public)
- All changes committed and pushed to `main`.
- Setup prompt drafted and emailed to seheim@gmail.com.

## Key Decisions
- **No auth** — shared library model; all users see the same downloaded decisions.
- **Vercel not viable** — no persistent filesystem, no long-running processes. VPS needed for production hosting.
- **ANTHROPIC_API_KEY optional** — app fully functional without it; only the "Claude ✦" analyze feature requires it.
- **Client-side date filtering** — necessary workaround for MoJ API bugs; same limitation exists on the official gov.il website.

## Files Changed This Session
| File | Change |
|------|--------|
| `api/moj.py` | Hardcoded fallbacks, fixed `get_versions()`, `SearchText` discovery |
| `server.py` | Client-side date filtering in `api_search`; `FreeText`/`PubDate` params in `api_bulk` |
| `static/index.html` | Added pub date fields to Search + Bulk tabs; added free text field to Bulk tab |
| `static/app.js` | Wired new fields; added try/catch on `doSearch()` |
| `CLAUDE.md` | New — auto-setup instructions |
| `README.md` | New — human-readable setup guide |

## Known Limitations
- `x-client-id` in `api/moj.py` is borrowed from gov.il browser session. If MoJ rotates it, all API calls break.
- Date filtering scans up to 2,000 results — very broad date ranges with no other filters can be slow.
- No rate limiting on MoJ API calls from bulk download.

## How to Resume
Server runs with:
```bash
cd /Users/aviadstark/Desktop/Claude/Code/Projects/Shamai
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```
Open http://localhost:8000
