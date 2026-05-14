"""Test with a completely different invoice style."""
import sys, io, json
sys.stdout.reconfigure(encoding="utf-8")
import requests
from PIL import Image, ImageDraw, ImageFont

img = Image.new("RGB", (700, 500), "#FFFDF5")
d = ImageDraw.Draw(img)
try:
    f = ImageFont.truetype("arial.ttf", 14)
    fb = ImageFont.truetype("arial.ttf", 18)
except Exception:
    f = fb = ImageFont.load_default()

d.text((30, 20), "Sharma & Associates LLP", fill="#333", font=fb)
d.text((30, 50), "Tax Invoice", fill="#666", font=f)
d.text((400, 20), "Bill No: SA/2025/1187", fill="#333", font=f)
d.text((400, 45), "Date: 08-Jan-2025", fill="#333", font=f)
d.text((400, 70), "GSTIN: 07AAKFS1234N1ZQ", fill="#333", font=f)
d.text((30, 90), "To: Apex Retail Pvt. Ltd.", fill="#333", font=f)
d.line([(30, 120), (670, 120)], fill="#999")
d.text((30, 130), "Professional Fees", fill="#333", font=f)
d.text((550, 130), "42,000.00", fill="#333", font=f)
d.text((30, 160), "Consultation Charges", fill="#333", font=f)
d.text((550, 160), "18,000.00", fill="#333", font=f)
d.line([(30, 190), (670, 190)], fill="#999")
d.text((400, 200), "Subtotal: 60,000.00", fill="#333", font=f)
d.text((400, 225), "CGST @9%: 5,400.00", fill="#333", font=f)
d.text((400, 250), "SGST @9%: 5,400.00", fill="#333", font=f)
d.text((400, 280), "Total: Rs. 70,800.00", fill="#000", font=fb)
d.text((30, 320), "Payment Due: Net 15 Days", fill="#666", font=f)

buf = io.BytesIO()
img.save(buf, "PNG")

r = requests.post("http://localhost:8000/pipeline", files={"file": ("sharma_invoice.png", buf.getvalue())}, timeout=300)
res = r.json()
ext = res.get("extracted_data", {})
conf = ext.get("confidence", {})
val = res.get("validation", {})

print(f"Pipeline: {res.get('pipeline_status')}")
print(f"Invoice#: {ext.get('invoice_number')} [{int(conf.get('invoice_number',0)*100)}%]")
print(f"Date:     {ext.get('date')} [{int(conf.get('date',0)*100)}%]")
print(f"Vendor:   {ext.get('vendor_name')} [{int(conf.get('vendor_name',0)*100)}%]")
print(f"Amount:   {ext.get('total_amount')} [{int(conf.get('total_amount',0)*100)}%]")
print(f"GST:      {ext.get('gst')}")
print(f"Overall:  {int(ext.get('overall_confidence',0)*100)}%")
print(f"Valid:    {val.get('status')} ({val.get('fields_found')}/{val.get('fields_total')})")
print(f"Is Invoice: {ext.get('is_invoice')}")
print(f"Detection:  {ext.get('detection_message')}")
