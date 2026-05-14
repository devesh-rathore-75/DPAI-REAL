"""
DPAI — Validation Service
Validates extracted invoice data for completeness, format, and duplicates.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── In-memory duplicate tracker (swap for DB in production) ──────────────────
_seen_invoices: dict[str, str] = {}  # invoice_number -> document_id


def validate_extracted_data(data: dict, doc_id: str) -> dict:
    """
    Validate extracted invoice data.
    Returns a validation report with errors, warnings, and overall status.
    """
    errors: list[dict] = []
    warnings: list[dict] = []

    # ── Required field checks ────────────────────────────────────────────
    required_fields = {
        "invoice_number": "Invoice Number",
        "date": "Date",
        "vendor_name": "Vendor Name",
        "total_amount": "Total Amount",
    }

    for field, label in required_fields.items():
        value = data.get(field)
        if not value:
            errors.append({
                "field": field,
                "message": f"{label} is missing",
                "severity": "error",
            })

    # ── Format validations ───────────────────────────────────────────────
    # Invoice number format
    inv_num = data.get("invoice_number")
    if inv_num:
        if len(inv_num) < 3:
            warnings.append({
                "field": "invoice_number",
                "message": f"Invoice number '{inv_num}' seems too short",
                "severity": "warning",
            })

    # Date format
    date_val = data.get("date")
    if date_val:
        # Check for reasonable date pattern
        date_patterns = [
            r"\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}",
            r"\d{4}[/\-\.]\d{1,2}[/\-\.]\d{1,2}",
            r"[A-Za-z]+\s+\d{1,2},?\s+\d{4}",
            r"\d{1,2}[\-/][A-Za-z]{3,9}[\-/]\d{4}",
        ]
        if not any(re.match(p, date_val) for p in date_patterns):
            warnings.append({
                "field": "date",
                "message": f"Date format '{date_val}' may not be standard",
                "severity": "warning",
            })

    # Amount format
    amount_val = data.get("total_amount")
    if amount_val:
        clean = amount_val.replace(",", "").replace("₹", "").strip()
        try:
            parsed = float(clean)
            if parsed <= 0:
                errors.append({
                    "field": "total_amount",
                    "message": "Total amount must be greater than zero",
                    "severity": "error",
                })
        except ValueError:
            errors.append({
                "field": "total_amount",
                "message": f"Cannot parse amount: '{amount_val}'",
                "severity": "error",
            })

    # ── GST validation ───────────────────────────────────────────────────
    gst = data.get("gst")
    if not gst:
        warnings.append({
            "field": "gst",
            "message": "No GST information found",
            "severity": "warning",
        })
    else:
        gstin = gst.get("gstin")
        if gstin:
            # GSTIN format: 2-digit state + 10-char PAN + 1 entity + 1 Z + 1 check
            if not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]$", gstin):
                warnings.append({
                    "field": "gst.gstin",
                    "message": f"GSTIN '{gstin}' may not be in valid format",
                    "severity": "warning",
                })

    # ── Duplicate check ──────────────────────────────────────────────────
    is_duplicate = False
    duplicate_of: Optional[str] = None

    if inv_num:
        normalized = inv_num.upper().replace(" ", "")
        if normalized in _seen_invoices:
            existing_id = _seen_invoices[normalized]
            if existing_id != doc_id:
                is_duplicate = True
                duplicate_of = existing_id
                warnings.append({
                    "field": "invoice_number",
                    "message": f"Possible duplicate of document {existing_id}",
                    "severity": "warning",
                })
        else:
            _seen_invoices[normalized] = doc_id

    # ── Build result ─────────────────────────────────────────────────────
    has_errors = len(errors) > 0
    status = "invalid" if has_errors else ("warning" if warnings else "valid")

    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "is_duplicate": is_duplicate,
        "duplicate_of": duplicate_of,
        "fields_found": sum(1 for f in required_fields if data.get(f)),
        "fields_total": len(required_fields),
    }


def reset_duplicate_tracker():
    """Clear the in-memory duplicate tracker (useful for testing)."""
    global _seen_invoices
    _seen_invoices = {}
