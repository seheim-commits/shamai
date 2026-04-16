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
