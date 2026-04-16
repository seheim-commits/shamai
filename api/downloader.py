import os
import re
import sqlite3
import httpx
from pathlib import Path

PDFS_DIR = Path(os.getenv("PDFS_DIR", "pdfs"))


def _safe(s: str) -> str:
    """Strip characters unsafe for filenames (keep Hebrew, alphanumeric, dash)."""
    return re.sub(r'[^\w\u0590-\u05ff\-]', '_', s or "unknown").strip("_") or "unknown"


def local_path(committee: str, decision_date: str, block: str, plot: str, appraiser: str) -> Path:
    date_str = (decision_date or "")[:10] or "unknown"
    last_name = (appraiser or "").split()[-1] if appraiser else "unknown"
    filename = f"{date_str}-gush{_safe(block)}-chelka{_safe(plot)}-{_safe(last_name)}.pdf"
    return PDFS_DIR / _safe(committee) / filename


def download_pdf(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60) as client:
        r = client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    return dest


def index_decision(conn: sqlite3.Connection, data: dict, path: str) -> int:
    cursor = conn.execute(
        """INSERT OR IGNORE INTO decisions
           (filename, committee, appraiser, block, plot,
            appraisal_type, appraisal_version, decision_date, local_path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("AppraisalHeader", ""),
            data.get("Committee", ""),
            data.get("DecisiveAppraiser", ""),
            data.get("Block", ""),
            data.get("Plot", ""),
            data.get("AppraisalType", ""),
            data.get("AppraisalVersion", ""),
            data.get("DecisionDate", ""),
            path,
        ),
    )
    conn.commit()
    return cursor.lastrowid if cursor.rowcount else 0
