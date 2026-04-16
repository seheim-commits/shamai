# שמאי מכריע

Search, download, OCR, and analyze decisive appraiser decisions from the Israeli MoJ.

## Requirements

- Python 3.10+
- Tesseract OCR (system package)

### Install Tesseract

**macOS:**
```bash
brew install tesseract tesseract-lang
```

**Ubuntu/Debian:**
```bash
sudo apt install tesseract-ocr tesseract-ocr-heb
```

## Setup

```bash
git clone <repo-url>
cd shamai
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

## Run

```bash
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

Open [http://localhost:8000](http://localhost:8000)

## Features

- **Search** — filter by committee, appraiser, version, block/plot, date range, free text
- **Bulk download** — download many decisions at once with optional auto-OCR
- **Library** — full-text search across downloaded PDFs
- **Claude analysis** — summarize or query any decision via Claude AI
