# Lessons Learned

## MoJ API

**Rule: Never trust MoJ API field names — validate against browser network tab.**
The documented `FreeText` field returns 500. Correct field is `SearchText`. Always cross-check with browser DevTools on the official gov.il site before assuming a field works.

**Rule: Always implement fallbacks for MoJ list endpoints.**
`CommiteesList` and `DecisiveAppraisersList` return 500. Wrap all MoJ list calls in try/except with hardcoded fallback lists. Sample at least 3,000 results at multiple skip offsets to get a representative fallback.

**Rule: MoJ date filter is broken server-side — always filter client-side.**
`DateFrom`/`DateTo` return 500. Implement client-side scan with `MAX_SCAN=2000` cap. Use early exit for `PublicityDate` lower bound (results are sorted desc by pub date). Short-circuit immediately if `DateFrom > DateTo`.

**Rule: MoJ `AppraisalVersions` returns objects `{Value, Key, ParentKey}`, not strings.**
Extract `.Value`, skip numeric entries. Don't assume list endpoints return plain arrays.

## Python / FastAPI

**Rule: Use `python3 -m uvicorn` not `python server.py`.**
The server entry point is via uvicorn, not a direct Python script. Document this clearly.
