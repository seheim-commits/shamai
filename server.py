import asyncio
import json
import os
import subprocess
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from db import init_db, get_db
from api.moj import search_decisions, get_committees, get_appraisers, get_versions, pdf_url
from api.downloader import local_path as make_local_path, download_pdf, index_decision
from api.ocr import ocr_pdf, store_ocr
from api.claude import analyze_stream

app = FastAPI(title="שמאי מכריע")


@app.on_event("startup")
def startup():
    init_db()
    Path(os.getenv("PDFS_DIR", "pdfs")).mkdir(exist_ok=True)


@app.get("/api/search")
def api_search(
    skip: int = 0,
    Committee: Optional[str] = None,
    DecisiveAppraiser: Optional[str] = None,
    AppraisalType: Optional[str] = None,
    AppraisalVersion: Optional[str] = None,
    Block: Optional[str] = None,
    Plot: Optional[str] = None,
    DateFrom: Optional[str] = None,
    DateTo: Optional[str] = None,
    FreeText: Optional[str] = None,
):
    filters = {k: v for k, v in {
        "Committee": Committee, "DecisiveAppraiser": DecisiveAppraiser,
        "AppraisalType": AppraisalType, "AppraisalVersion": AppraisalVersion,
        "Block": Block, "Plot": Plot, "DateFrom": DateFrom,
        "DateTo": DateTo, "FreeText": FreeText,
    }.items() if v}
    return search_decisions(skip=skip, **filters)


@app.get("/api/filters")
def api_filters():
    return {
        "committees": get_committees(),
        "appraisers": get_appraisers(),
        "versions": get_versions(),
    }


@app.post("/api/download")
def api_download(body: dict):
    data = body.get("data", body)
    docs = data.get("Document", [])
    if not docs:
        return JSONResponse({"error": "no documents"}, status_code=400)

    token = docs[0]["FileName"].split("/")[-1]
    url = pdf_url(token)
    dest = make_local_path(
        data.get("Committee", ""),
        data.get("DecisionDate", ""),
        data.get("Block", ""),
        data.get("Plot", ""),
        data.get("DecisiveAppraiser", ""),
    )

    if dest.exists():
        return {"status": "exists", "path": str(dest)}

    download_pdf(url, dest)

    conn = get_db()
    row_id = index_decision(conn, data, str(dest))
    conn.close()

    return {"status": "ok", "path": str(dest), "id": row_id}


@app.get("/api/bulk")
async def api_bulk(
    Committee: Optional[str] = None,
    DecisiveAppraiser: Optional[str] = None,
    AppraisalType: Optional[str] = None,
    AppraisalVersion: Optional[str] = None,
    DateFrom: Optional[str] = None,
    DateTo: Optional[str] = None,
    max_results: int = 100,
    auto_ocr: bool = False,
    skip_existing: bool = True,
):
    filters = {k: v for k, v in {
        "Committee": Committee, "DecisiveAppraiser": DecisiveAppraiser,
        "AppraisalType": AppraisalType, "AppraisalVersion": AppraisalVersion,
        "DateFrom": DateFrom, "DateTo": DateTo,
    }.items() if v}

    async def generate():
        downloaded = errors = skip = 0

        while downloaded < max_results:
            batch = search_decisions(skip=skip, **filters)
            results = batch.get("Results", [])
            if not results:
                break

            for item in results:
                if downloaded >= max_results:
                    break
                data = item["Data"]
                docs = data.get("Document", [])
                if not docs:
                    continue

                token = docs[0]["FileName"].split("/")[-1]
                url = pdf_url(token)
                dest = make_local_path(
                    data.get("Committee", ""),
                    data.get("DecisionDate", ""),
                    data.get("Block", ""),
                    data.get("Plot", ""),
                    data.get("DecisiveAppraiser", ""),
                )
                name = data.get("AppraisalHeader", dest.name)

                if skip_existing and dest.exists():
                    yield f"data: {json.dumps({'status': 'skip', 'name': name})}\n\n"
                    continue

                yield f"data: {json.dumps({'status': 'downloading', 'name': name})}\n\n"

                try:
                    download_pdf(url, dest)
                    conn = get_db()
                    row_id = index_decision(conn, data, str(dest))
                    if auto_ocr and row_id:
                        text = ocr_pdf(dest)
                        store_ocr(conn, row_id, text)
                    conn.close()
                    downloaded += 1
                    yield f"data: {json.dumps({'status': 'ok', 'name': name, 'downloaded': downloaded, 'errors': errors})}\n\n"
                except Exception as e:
                    errors += 1
                    yield f"data: {json.dumps({'status': 'error', 'name': name, 'error': str(e), 'errors': errors})}\n\n"

                await asyncio.sleep(0.05)

            skip += len(results)
            if len(results) < 10:
                break

        yield f"data: {json.dumps({'status': 'done', 'downloaded': downloaded, 'errors': errors})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/ocr")
def api_ocr(body: dict):
    path = Path(body["path"])
    if not path.exists():
        return JSONResponse({"error": "file not found"}, status_code=404)

    conn = get_db()
    row = conn.execute("SELECT id FROM decisions WHERE local_path=?", (str(path),)).fetchone()
    if not row:
        return JSONResponse({"error": "not in index"}, status_code=404)

    conn.execute("UPDATE decisions SET ocr_status='pending' WHERE id=?", (row["id"],))
    conn.commit()

    text = ocr_pdf(path)
    store_ocr(conn, row["id"], text)
    conn.close()

    return {"status": "ok", "chars": len(text)}


@app.post("/api/analyze")
def api_analyze(body: dict):
    path = body.get("path")
    prompt = body.get("prompt", "סכם את ההכרעה בצורה תמציתית")

    conn = get_db()
    row = conn.execute(
        "SELECT dt.text FROM decision_text dt JOIN decisions d ON dt.rowid=d.id WHERE d.local_path=?",
        (path,),
    ).fetchone()
    conn.close()

    if not row or not row["text"]:
        return JSONResponse({"error": "no OCR text — run OCR first"}, status_code=400)

    def generate():
        for chunk in analyze_stream(row["text"], prompt):
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.get("/api/library")
def api_library(
    q: Optional[str] = None,
    committee: Optional[str] = None,
    appraiser: Optional[str] = None,
):
    conn = get_db()

    if q:
        rows = conn.execute(
            """SELECT d.* FROM decisions d
               JOIN decision_text dt ON dt.rowid = d.id
               WHERE decision_text MATCH ?
               ORDER BY d.downloaded_at DESC""",
            (q,),
        ).fetchall()
    else:
        clauses, params = ["1=1"], []
        if committee:
            clauses.append("committee=?")
            params.append(committee)
        if appraiser:
            clauses.append("appraiser=?")
            params.append(appraiser)
        rows = conn.execute(
            f"SELECT * FROM decisions WHERE {' AND '.join(clauses)} ORDER BY downloaded_at DESC",
            params,
        ).fetchall()

    conn.close()
    return {"results": [dict(r) for r in rows]}


@app.post("/api/open")
def api_open(body: dict):
    path = body.get("path", "")
    if path and Path(path).exists():
        subprocess.Popen(["open", path])  # macOS; use "xdg-open" on Linux
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
