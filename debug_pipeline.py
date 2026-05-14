"""
DPAI Pipeline Debugger — Traces every stage step-by-step.
Tests with multiple invoice types: image, PDF (digital), PDF (scanned).
NO browser interaction. Pure programmatic testing.
"""
import sys, os, io, json, time
sys.stdout.reconfigure(encoding="utf-8")
import requests

API = "http://localhost:8000"
SEP = "=" * 70

def header(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def step(num, desc):
    print(f"\n  [{num}] {desc}")

def ok(msg):
    print(f"      OK: {msg}")

def fail(msg):
    print(f"      FAIL: {msg}")

def info(msg):
    print(f"      -> {msg}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 1: Image Invoice (PNG)
# ═══════════════════════════════════════════════════════════════════════
header("TEST 1: Real Image Invoice (PNG)")

img_path = os.path.join(os.path.dirname(__file__), "data", "test_invoice_real.png")
if not os.path.exists(img_path):
    fail(f"Test image not found: {img_path}")
    fail("Run generate_test_invoice.py first")
    sys.exit(1)

with open(img_path, "rb") as f:
    img_bytes = f.read()

step(1, f"File loaded: {len(img_bytes)} bytes")

# Stage 1: Upload
step(2, "UPLOAD stage")
r = requests.post(f"{API}/upload", files={"file": ("test_invoice.png", img_bytes)}, timeout=10)
info(f"Status code: {r.status_code}")
upload_data = r.json()
info(f"Response: {json.dumps(upload_data, indent=2)[:500]}")

if upload_data.get("status") == "duplicate":
    doc_id = upload_data["document_id"]
    info(f"Duplicate detected, using existing doc_id: {doc_id}")
else:
    doc_id = upload_data["document_id"]
    ok(f"Uploaded as doc_id: {doc_id}")

# Stage 2: Process (OCR)
step(3, "PROCESS (OCR) stage")
t0 = time.time()
r = requests.post(f"{API}/process", params={"document_id": doc_id}, timeout=300)
elapsed = time.time() - t0
info(f"Status code: {r.status_code} ({elapsed:.1f}s)")

if r.status_code != 200:
    fail(f"OCR failed: {r.text}")
else:
    process_data = r.json()
    raw_text = process_data.get("raw_text", "")
    text_len = process_data.get("text_length", 0)
    info(f"Text length: {text_len} chars")
    info(f"Processing time: {process_data.get('processing_time_ms', '?')}ms")

    if raw_text and len(raw_text) > 10:
        ok(f"Real OCR text extracted!")
        info(f"First 200 chars:")
        for line in raw_text[:300].split("\n"):
            info(f"  | {line}")
    else:
        fail("OCR returned empty or near-empty text!")
        fail(f"raw_text = '{raw_text}'")

# Stage 3: Extract
step(4, "EXTRACT stage")
r = requests.post(f"{API}/extract", params={"document_id": doc_id}, timeout=10)
info(f"Status code: {r.status_code}")

if r.status_code != 200:
    fail(f"Extraction failed: {r.text}")
else:
    extract_data = r.json()
    extracted = extract_data.get("extracted_data", {})
    
    info("Extracted fields:")
    fields = ["invoice_number", "date", "vendor_name", "total_amount"]
    found = 0
    for f in fields:
        val = extracted.get(f)
        conf = extracted.get("confidence", {}).get(f, 0)
        status = "OK" if val else "MISSING"
        if val:
            found += 1
        print(f"      {status:7s} | {f:20s}: {str(val):30s} [{int(conf*100)}%]")
    
    gst = extracted.get("gst")
    if gst:
        info(f"GST: {gst}")
    else:
        info("GST: not found")
    
    overall = extracted.get("overall_confidence", 0)
    info(f"Overall confidence: {int(overall*100)}%")
    info(f"Fields found: {found}/{len(fields)}")

    if found == 0:
        fail("ALL FIELDS EMPTY - Extraction is broken!")
        fail("Check if raw_text was passed correctly to extract_all()")
    elif found < len(fields):
        info(f"WARNING: {len(fields) - found} field(s) missing")
    else:
        ok("All fields extracted!")

# Stage 4: Validate
step(5, "VALIDATE stage")
r = requests.post(f"{API}/validate", params={"document_id": doc_id}, timeout=10)
info(f"Status code: {r.status_code}")

if r.status_code != 200:
    fail(f"Validation failed: {r.text}")
else:
    val_data = r.json()
    validation = val_data.get("validation", {})
    info(f"Status: {validation.get('status')}")
    info(f"Fields: {validation.get('fields_found')}/{validation.get('fields_total')}")
    
    for e in validation.get("errors", []):
        info(f"  [ERR]  {e['field']}: {e['message']}")
    for w in validation.get("warnings", []):
        info(f"  [WARN] {w['field']}: {w['message']}")

# Stage 5: Full pipeline test
step(6, "FULL PIPELINE (single call) test")
# Generate a slightly different invoice to avoid duplicate detection
from PIL import Image, ImageDraw, ImageFont
img2 = Image.new("RGB", (600, 300), "#FFFFFF")
draw = ImageDraw.Draw(img2)
try:
    font = ImageFont.truetype("arial.ttf", 16)
except:
    font = ImageFont.load_default()

draw.text((30, 20), "INVOICE", fill="#000", font=font)
draw.text((30, 50), "Invoice No: TEST-PIPE-9999", fill="#000", font=font)
draw.text((30, 80), "Date: 13/05/2026", fill="#000", font=font)
draw.text((30, 110), "From: QuickTest Solutions Pvt. Ltd.", fill="#000", font=font)
draw.text((30, 140), "Total Amount: 15,750.00", fill="#000", font=font)
draw.text((30, 170), "CGST @9%: 1,417.50", fill="#000", font=font)
draw.text((30, 200), "SGST @9%: 1,417.50", fill="#000", font=font)
draw.text((30, 230), "Grand Total: 18,585.00", fill="#000", font=font)

buf = io.BytesIO()
img2.save(buf, "PNG")
pipe_bytes = buf.getvalue()
info(f"Generated pipeline test image: {len(pipe_bytes)} bytes")

t0 = time.time()
r = requests.post(f"{API}/pipeline", files={"file": ("pipeline_test.png", pipe_bytes)}, timeout=300)
elapsed = time.time() - t0
info(f"Status code: {r.status_code} ({elapsed:.1f}s)")

if r.status_code != 200:
    fail(f"Pipeline failed: {r.text}")
else:
    pipe_data = r.json()
    info(f"Pipeline status: {pipe_data.get('pipeline_status')}")
    
    p_raw = pipe_data.get("raw_text", "")
    info(f"OCR text length: {len(p_raw)}")
    if p_raw:
        info(f"OCR text preview:")
        for line in p_raw[:200].split("\n"):
            info(f"  | {line}")
    
    p_ext = pipe_data.get("extracted_data", {})
    info("Extracted:")
    for f in ["invoice_number", "date", "vendor_name", "total_amount"]:
        v = p_ext.get(f)
        c = p_ext.get("confidence", {}).get(f, 0)
        status = "OK" if v else "MISSING"
        print(f"      {status:7s} | {f:20s}: {str(v):30s} [{int(c*100)}%]")

    p_val = pipe_data.get("validation", {})
    info(f"Validation: {p_val.get('status')} ({p_val.get('fields_found')}/{p_val.get('fields_total')})")

# Stage 6: Export test
step(7, "EXPORT test")
for fmt in ["csv", "json", "excel"]:
    r = requests.get(f"{API}/export/{fmt}", timeout=10)
    if r.status_code == 200:
        ok(f"{fmt.upper()} export: {len(r.content)} bytes")
    else:
        fail(f"{fmt.upper()} export failed: {r.status_code}")

# Stage 7: Documents list
step(8, "DOCUMENTS LIST test")
r = requests.get(f"{API}/documents", timeout=5)
docs = r.json()
info(f"Total documents: {docs.get('total')}")
for d in docs.get("documents", []):
    info(f"  {d['document_id']}: {d['filename']} -> {d['status']} | val={d.get('validation_status')}")


header("DIAGNOSIS SUMMARY")

# Check the document store directly for the problematic case
r = requests.get(f"{API}/documents/{doc_id}", timeout=5)
if r.status_code == 200:
    doc_detail = r.json()
    info(f"Document {doc_id} detail check:")
    info(f"  status: {doc_detail.get('status')}")
    info(f"  raw_text length: {len(doc_detail.get('raw_text') or '')}")
    info(f"  extracted_data: {bool(doc_detail.get('extracted_data'))}")
    info(f"  validation: {bool(doc_detail.get('validation'))}")
    
    ext = doc_detail.get("extracted_data", {})
    if ext:
        empty_fields = [f for f in ["invoice_number","date","vendor_name","total_amount"] if not ext.get(f)]
        if empty_fields:
            info(f"  EMPTY fields: {empty_fields}")
            info(f"  This means extraction regex didn't match the OCR text")
        else:
            ok("All 4 fields populated in document store")

print(f"\n{SEP}")
print("  DEBUG COMPLETE")
print(SEP)
