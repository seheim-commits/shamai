# Auto-Setup Instructions

You are setting up the "שמאי מכריע" app for the user. Follow every step below autonomously. Fix any error before moving on. Do not ask the user anything — figure it out.

## Steps

### 1. Clone the repo
If not already cloned, clone it and cd into it:
```bash
git clone <REPO_URL> shamai && cd shamai
```

### 2. Install Tesseract (system dependency)
Detect the OS and install:
- **macOS:** `brew install tesseract tesseract-lang`
- **Ubuntu/Debian:** `sudo apt-get install -y tesseract-ocr tesseract-ocr-heb`
- **Other:** tell the user what to install manually, then continue

Verify: `tesseract --version` — must succeed before continuing.

### 3. Install Python dependencies
```bash
pip install -r requirements.txt
```
If `pip` fails, try `pip3`. If a package fails, fix it and retry.

### 4. Configure environment
```bash
cp .env.example .env
```
The app works without an API key. Only the "Claude ✦" analysis feature requires one. Do not ask the user for it — just leave `ANTHROPIC_API_KEY` blank in `.env` and continue.

### 5. Start the server
```bash
python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 &
```
Wait 3 seconds, then verify it's running:
```bash
curl -s http://localhost:8000/api/filters | head -c 100
```
Must return JSON. If it fails, check the error and fix it.

### 6. Done — tell the user

Print this message:
```
✓ הכל מוכן!

פתח את הדפדפן: http://localhost:8000

איך להשתמש:
• חיפוש — חפש החלטות לפי ועדה, שמאי, תאריך, או טקסט חופשי (שם שכונה, רחוב וכו')
• הורדה מרוכזת — הורד קבצים רבים בבת אחת (עם OCR אוטומטי אם תרצה)
• הספרייה שלי — חפש בתוך ה-PDF-ים שהורדת, ונתח עם Claude

להפעלה בפעם הבאה:
  cd shamai && python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```
