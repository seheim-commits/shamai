# Data Model — שמאי מכריע

## SQLite Database (`index.db`)

### `decisions` table
Metadata index for all downloaded PDFs.

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | Auto-increment |
| `filename` | TEXT | `AppraisalHeader` from MoJ — human-readable title |
| `committee` | TEXT | Planning committee name (Hebrew) |
| `appraiser` | TEXT | Decisive appraiser full name |
| `block` | TEXT | גוש (land block number) |
| `plot` | TEXT | חלקה (land plot number) |
| `appraisal_type` | TEXT | Type of appraisal |
| `appraisal_version` | TEXT | `שומה מקורית` / `שומה מתוקנת אחרי ערר` |
| `decision_date` | TEXT | ISO date string (YYYY-MM-DD) |
| `local_path` | TEXT UNIQUE | Absolute path to PDF on disk |
| `downloaded_at` | TEXT | SQLite `CURRENT_TIMESTAMP` |
| `ocr_status` | TEXT | `none` / `pending` / `done` |

### `decision_text` (FTS5 virtual table)
Full-text search index over OCR'd PDF content.

| Column | Notes |
|--------|-------|
| `text` | Raw OCR text from Tesseract |
| `rowid` | Matches `decisions.id` |

Query pattern:
```sql
SELECT d.* FROM decisions d
JOIN decision_text dt ON dt.rowid = d.id
WHERE dt MATCH 'קרית יובל'
ORDER BY d.downloaded_at DESC
```

## Filesystem Layout

```
pdfs/
└── <committee>/          # _safe(Committee) — Hebrew chars preserved
    └── <date>-gush<block>-chelka<plot>-<appraiser_last_name>.pdf
```

Example:
```
pdfs/ירושלים/2024-03-15-gush6106-chelka316-כהן.pdf
```

## MoJ API Response Shape

`SearchDecisions` returns:
```json
{
  "Results": [
    {
      "Data": {
        "AppraisalHeader": "הכרעה בגוש 6106 חלקה 316",
        "Committee": "ירושלים",
        "DecisiveAppraiser": "כהן אלי",
        "Block": "6106",
        "Plot": "316",
        "AppraisalType": "...",
        "AppraisalVersion": "שומה מקורית",
        "DecisionDate": "2024-03-15T00:00:00",
        "PublicityDate": "2024-04-01T00:00:00",
        "Document": [
          { "FileName": "/path/to/token" }
        ]
      }
    }
  ],
  "TotalResults": 42,
  "Status": "OK"
}
```

PDF token extracted from `Document[0].FileName.split("/")[-1]` and appended to the PDF base URL.
