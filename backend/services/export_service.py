"""
DPAI — Export Service (v2.0)
Handles CSV, JSON, and Excel export of extracted invoice data.
"""

import csv
import io
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _flatten_record(record: dict) -> dict:
    """Flatten a single invoice record for tabular export."""
    flat = {
        "document_id": record.get("document_id", ""),
        "filename": record.get("filename", ""),
        "processed_at": record.get("processed_at", ""),
        "processing_time_ms": record.get("processing_time_ms", ""),
        "invoice_number": "",
        "date": "",
        "vendor_name": "",
        "total_amount": "",
        "gstin": "",
        "cgst": "",
        "sgst": "",
        "igst": "",
        "total_gst": "",
        "overall_confidence": "",
        "validation_status": "",
        "errors_count": 0,
        "warnings_count": 0,
    }

    extracted = record.get("extracted_data", {})
    if extracted:
        flat["invoice_number"] = extracted.get("invoice_number", "") or ""
        flat["date"] = extracted.get("date", "") or ""
        flat["vendor_name"] = extracted.get("vendor_name", "") or ""
        flat["total_amount"] = extracted.get("total_amount", "") or ""
        flat["overall_confidence"] = extracted.get("overall_confidence", "")

        gst = extracted.get("gst") or {}
        flat["gstin"] = gst.get("gstin", "") or ""
        flat["cgst"] = gst.get("cgst", "") or ""
        flat["sgst"] = gst.get("sgst", "") or ""
        flat["igst"] = gst.get("igst", "") or ""
        flat["total_gst"] = gst.get("total_gst", "") or ""

    validation = record.get("validation", {})
    if validation:
        flat["validation_status"] = validation.get("status", "")
        flat["errors_count"] = len(validation.get("errors", []))
        flat["warnings_count"] = len(validation.get("warnings", []))

    return flat


def export_to_csv(records: list[dict]) -> str:
    """Export a list of invoice records to CSV string."""
    if not records:
        return ""

    flat_records = [_flatten_record(r) for r in records]
    fieldnames = list(flat_records[0].keys())

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(flat_records)

    return output.getvalue()


def export_to_json(records: list[dict]) -> str:
    """Export a list of invoice records to formatted JSON string."""
    export_data = {
        "export_date": datetime.utcnow().isoformat() + "Z",
        "total_records": len(records),
        "records": records,
    }
    return json.dumps(export_data, indent=2, default=str)


def export_to_excel(records: list[dict]) -> bytes:
    """Export a list of invoice records to Excel (.xlsx) bytes."""
    import pandas as pd

    flat_records = [_flatten_record(r) for r in records]
    df = pd.DataFrame(flat_records)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Invoices", index=False)
    output.seek(0)

    return output.getvalue()
