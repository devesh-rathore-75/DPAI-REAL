"""Test real OCR pipeline with actual invoice image."""
import sys, os, json, time
sys.stdout.reconfigure(encoding="utf-8")
import requests

API = "http://localhost:8000"

print("=" * 60)
print("DPAI v2.0 - Real OCR Pipeline Test")
print("=" * 60)

# 1. Health
r = requests.get(f"{API}/health")
h = r.json()
print(f"\n[1] Health: {h['status']} | Engine: {h['ocr_engine']} | Mode: {h['ocr_mode']}")

# 2. Load real invoice image
invoice_path = os.path.join(os.path.dirname(__file__), "data", "test_invoice_real.png")
with open(invoice_path, "rb") as f:
    img_bytes = f.read()
print(f"\n[2] Test file: {invoice_path} ({len(img_bytes)} bytes)")

# 3. Pipeline
print("\n[3] Running real OCR pipeline...")
t0 = time.time()
r = requests.post(f"{API}/pipeline", files={"file": ("test_invoice_real.png", img_bytes)}, timeout=120)
elapsed = time.time() - t0
result = r.json()
print(f"    Status: {result.get('pipeline_status')} ({elapsed:.1f}s)")

# 4. Raw OCR text
raw = result.get("raw_text", "")
print(f"\n[4] Raw OCR Text ({len(raw)} chars):")
print("    " + raw[:300].replace("\n", "\n    ") + "...")

# 5. Extracted data
ext = result.get("extracted_data", {})
print(f"\n[5] Extracted Fields:")
for k in ["invoice_number", "date", "vendor_name", "total_amount"]:
    v = ext.get(k, "N/A")
    c = ext.get("confidence", {}).get(k, 0)
    print(f"    {k:20s}: {str(v):30s} [{int(c*100)}% conf]")

gst = ext.get("gst", {})
if gst:
    print(f"    GST: {gst}")
print(f"    Overall confidence: {int(ext.get('overall_confidence',0)*100)}%")

# 6. Validation
val = result.get("validation", {})
print(f"\n[6] Validation: {val.get('status')} ({val.get('fields_found')}/{val.get('fields_total')} fields)")
for e in val.get("errors", []):
    print(f"    [ERR]  {e['field']}: {e['message']}")
for w in val.get("warnings", []):
    print(f"    [WARN] {w['field']}: {w['message']}")

# 7. Verify it's REAL (not hardcoded)
print(f"\n[7] Anti-demo verification:")
if "INV-2026-00847" in str(ext):
    print("    FAIL - Still returning hardcoded demo data!")
else:
    print("    PASS - Extraction is from real OCR")

if raw and len(raw) > 20:
    print("    PASS - Real text extracted from image")
else:
    print("    WARN - Very little text extracted")

print("\n" + "=" * 60)
print("Test complete!")
print("=" * 60)
