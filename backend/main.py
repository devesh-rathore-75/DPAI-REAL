"""
DPAI — FastAPI Backend (v2.0)
AI Document & Process Automation (Invoice System)

Real OCR pipeline using EasyOCR + PyMuPDF. No demo mode.
"""

import logging
import time
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, JSONResponse, Response

from backend.services.ocr_service import process_file
from backend.services.extraction import extract_all
from backend.services.validation import validate_extracted_data
from backend.services.export_service import export_to_csv, export_to_json, export_to_excel
from backend.utils.helpers import (
    generate_id, file_hash, timestamp_now, allowed_extension, UPLOAD_DIR
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-24s | %(levelname)-7s | %(message)s",
)
logger = logging.getLogger("dpai")

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="DPAI - Invoice Automation API",
    description="AI-powered document processing for invoice automation. Real OCR, no demo data.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory document store ────────────────────────────────────────────────
documents: dict[str, dict] = {}
file_hashes: dict[str, str] = {}


# ═══════════════════════════════════════════════════════════════════════════
#  ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "DPAI Invoice Automation",
        "version": "2.0.0",
        "ocr_engine": "EasyOCR",
        "ocr_mode": "production",
        "pdf_support": True,
        "documents_processed": len(documents),
    }


# ── 1. UPLOAD ────────────────────────────────────────────────────────────────
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload an invoice file. Always allows re-uploads for re-processing."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    if not allowed_extension(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Allowed: PDF, PNG, JPG, JPEG, TIFF, BMP, WEBP"
        )

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")

    content_hash = file_hash(content)
    doc_id = generate_id()

    save_path = UPLOAD_DIR / f"{doc_id}_{file.filename}"
    with open(save_path, "wb") as f:
        f.write(content)

    is_reupload = content_hash in file_hashes

    documents[doc_id] = {
        "document_id": doc_id,
        "filename": file.filename,
        "file_path": str(save_path),
        "file_size": len(content),
        "file_hash": content_hash,
        "uploaded_at": timestamp_now(),
        "status": "uploaded",
        "raw_text": None,
        "extracted_data": None,
        "validation": None,
        "processing_time_ms": None,
    }
    file_hashes[content_hash] = doc_id

    logger.info(f"Uploaded: {file.filename} -> {doc_id}{' (re-upload)' if is_reupload else ''}")

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "file_size": len(content),
        "status": "uploaded",
        "is_reupload": is_reupload,
        "message": "File uploaded successfully.",
    }


# ── 2. PROCESS (OCR) ────────────────────────────────────────────────────────
@app.post("/process")
async def process_document(document_id: str):
    """Run OCR with retry and multi-strategy preprocessing."""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    doc = documents[document_id]
    file_path = doc["file_path"]

    # Read file bytes fresh every time
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
        if len(file_bytes) == 0:
            raise ValueError("File is empty on disk")
    except FileNotFoundError:
        doc["status"] = "error"
        raise HTTPException(status_code=500, detail="Upload file not found on disk. Please re-upload.")
    except Exception as e:
        doc["status"] = "error"
        raise HTTPException(status_code=500, detail=f"Could not read file: {e}")

    # Run OCR with timing
    t_start = time.time()
    raw_text = ""
    error_detail = None

    try:
        raw_text = process_file(file_bytes, doc["filename"])
    except ValueError as e:
        error_detail = str(e)
        logger.error(f"OCR ValueError for {document_id}: {e}")
    except Exception as e:
        error_detail = f"Unexpected error: {str(e)}"
        logger.error(f"OCR failed for {document_id}: {e}", exc_info=True)

    elapsed = int((time.time() - t_start) * 1000)

    if error_detail:
        doc["status"] = "error"
        doc["processing_time_ms"] = elapsed
        doc["error_detail"] = error_detail
        raise HTTPException(status_code=500, detail=error_detail)

    doc["raw_text"] = raw_text
    doc["status"] = "processed"
    doc["processed_at"] = timestamp_now()
    doc["processing_time_ms"] = elapsed
    doc["error_detail"] = None

    logger.info(f"OCR complete: {document_id} ({len(raw_text)} chars, {elapsed}ms)")

    return {
        "document_id": document_id,
        "status": "processed",
        "text_length": len(raw_text),
        "processing_time_ms": elapsed,
        "raw_text": raw_text,
    }


# ── 3. EXTRACT ───────────────────────────────────────────────────────────────
@app.post("/extract")
async def extract_data(document_id: str):
    """Extract structured invoice data from OCR text."""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    doc = documents[document_id]
    if not doc.get("raw_text"):
        raise HTTPException(
            status_code=400,
            detail="Document has not been processed yet. Call /process first."
        )

    extracted = extract_all(doc["raw_text"])
    doc["extracted_data"] = extracted
    doc["status"] = "extracted"

    logger.info(f"Extraction complete: {document_id}")

    return {
        "document_id": document_id,
        "status": "extracted",
        "extracted_data": extracted,
    }


# ── 4. VALIDATE ──────────────────────────────────────────────────────────────
@app.post("/validate")
async def validate_document(document_id: str):
    """Validate extracted invoice data."""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    doc = documents[document_id]
    if not doc.get("extracted_data"):
        raise HTTPException(
            status_code=400,
            detail="Data has not been extracted yet. Call /extract first."
        )

    validation = validate_extracted_data(doc["extracted_data"], document_id)
    doc["validation"] = validation
    doc["status"] = "validated"

    logger.info(f"Validation complete: {document_id} -> {validation['status']}")

    return {
        "document_id": document_id,
        "status": "validated",
        "validation": validation,
    }


# ── 5. FULL PIPELINE ────────────────────────────────────────────────────────
@app.post("/pipeline")
async def full_pipeline(file: UploadFile = File(...)):
    """Full pipeline: Upload -> OCR -> Extract -> Validate. Always processes fresh."""
    upload_result = await upload_file(file)
    doc_id = upload_result["document_id"]

    try:
        await process_document(doc_id)
    except HTTPException as e:
        doc = documents.get(doc_id, {})
        return {
            "document_id": doc_id,
            "pipeline_status": "error",
            "pipeline_stage": "ocr",
            "error": e.detail,
            "filename": doc.get("filename"),
            "raw_text": "",
            "extracted_data": {"invoice_number": None, "date": None, "vendor_name": None, "total_amount": None, "gst": None, "confidence": {}, "overall_confidence": 0.0, "is_invoice": False, "detection_message": f"OCR failed: {e.detail}", "raw_text_preview": "", "raw_text_length": 0},
            "validation": {"status": "error", "errors": [{"field": "ocr", "message": e.detail, "severity": "error"}], "warnings": [], "fields_found": 0, "fields_total": 4},
            "processing_time_ms": doc.get("processing_time_ms"),
        }

    await extract_data(doc_id)
    await validate_document(doc_id)

    doc = documents[doc_id]

    return {
        "document_id": doc_id,
        "pipeline_status": "complete",
        "filename": doc["filename"],
        "raw_text": doc["raw_text"],
        "extracted_data": doc["extracted_data"],
        "validation": doc["validation"],
        "processing_time_ms": doc.get("processing_time_ms"),
        "processed_at": doc.get("processed_at"),
    }


# ── 5b. MULTI-FILE PIPELINE ─────────────────────────────────────────────────
@app.post("/pipeline/batch")
async def batch_pipeline(files: List[UploadFile] = File(...)):
    """Process multiple invoice files in one call."""
    results = []
    for f in files:
        try:
            result = await full_pipeline(f)
            results.append(result)
        except HTTPException as e:
            results.append({
                "filename": f.filename,
                "pipeline_status": "error",
                "error": e.detail,
            })
        except Exception as e:
            results.append({
                "filename": f.filename,
                "pipeline_status": "error",
                "error": str(e),
            })
    return {"total": len(results), "results": results}


# ── 6. UPDATE EXTRACTED DATA (manual correction) ────────────────────────────
@app.post("/update")
async def update_extracted(document_id: str, field: str, value: str):
    """Allow manual correction of an extracted field."""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

    doc = documents[document_id]
    if not doc.get("extracted_data"):
        raise HTTPException(status_code=400, detail="No extracted data to update")

    extracted = doc["extracted_data"]
    valid_fields = {"invoice_number", "date", "vendor_name", "total_amount"}

    if field in valid_fields:
        old_val = extracted.get(field)
        extracted[field] = value
        logger.info(f"Manual update: {document_id}.{field} = '{old_val}' -> '{value}'")

        # Re-validate after update
        validation = validate_extracted_data(extracted, document_id)
        doc["validation"] = validation

        return {
            "document_id": document_id,
            "field": field,
            "old_value": old_val,
            "new_value": value,
            "validation": validation,
        }
    elif field.startswith("gst."):
        gst_field = field.split(".", 1)[1]
        if not extracted.get("gst"):
            extracted["gst"] = {}
        extracted["gst"][gst_field] = value
        return {"document_id": document_id, "field": field, "new_value": value}
    else:
        raise HTTPException(status_code=400, detail=f"Unknown field: {field}")


# ── 7. EXPORT ────────────────────────────────────────────────────────────────
@app.get("/export/csv")
async def export_csv():
    """Export all processed documents as CSV."""
    records = [doc for doc in documents.values() if doc.get("extracted_data")]
    if not records:
        raise HTTPException(status_code=404, detail="No processed documents to export")

    csv_content = export_to_csv(records)
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dpai_invoices_export.csv"},
    )


@app.get("/export/json")
async def export_json():
    """Export all processed documents as JSON."""
    records = [doc for doc in documents.values() if doc.get("extracted_data")]
    if not records:
        raise HTTPException(status_code=404, detail="No processed documents to export")

    json_content = export_to_json(records)
    return JSONResponse(
        content={"export": json_content},
        headers={"Content-Disposition": "attachment; filename=dpai_invoices_export.json"},
    )


@app.get("/export/excel")
async def export_excel():
    """Export all processed documents as Excel (.xlsx)."""
    records = [doc for doc in documents.values() if doc.get("extracted_data")]
    if not records:
        raise HTTPException(status_code=404, detail="No processed documents to export")

    excel_bytes = export_to_excel(records)
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=dpai_invoices_export.xlsx"},
    )


# ── 8. DOCUMENTS LIST & SEARCH ──────────────────────────────────────────────
@app.get("/documents")
async def list_documents(
    search: str = Query(None, description="Search by filename or vendor"),
    status: str = Query(None, description="Filter by status"),
):
    """List all uploaded/processed documents with optional search & filter."""
    summary = []
    for doc in documents.values():
        # Apply search filter
        if search:
            search_lower = search.lower()
            filename_match = search_lower in doc.get("filename", "").lower()
            vendor_match = False
            if doc.get("extracted_data"):
                vendor = doc["extracted_data"].get("vendor_name") or ""
                vendor_match = search_lower in vendor.lower()
            if not filename_match and not vendor_match:
                continue

        # Apply status filter
        if status and doc.get("status") != status:
            continue

        summary.append({
            "document_id": doc["document_id"],
            "filename": doc["filename"],
            "file_size": doc.get("file_size"),
            "status": doc["status"],
            "uploaded_at": doc.get("uploaded_at"),
            "processed_at": doc.get("processed_at"),
            "processing_time_ms": doc.get("processing_time_ms"),
            "validation_status": doc.get("validation", {}).get("status") if doc.get("validation") else None,
            "extracted_data": doc.get("extracted_data"),
            "validation": doc.get("validation"),
        })

    return {"total": len(summary), "documents": summary}


# ── 9. SINGLE DOCUMENT DETAIL ───────────────────────────────────────────────
@app.get("/documents/{document_id}")
async def get_document(document_id: str):
    """Get full details of a single document."""
    if document_id not in documents:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    return documents[document_id]


# ═══════════════════════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
