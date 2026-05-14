"""Generate a realistic invoice image for testing real OCR."""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 800, 1100
img = Image.new("RGB", (WIDTH, HEIGHT), "#FFFFFF")
draw = ImageDraw.Draw(img)

try:
    font_b = ImageFont.truetype("arial.ttf", 22)
    font = ImageFont.truetype("arial.ttf", 16)
    font_s = ImageFont.truetype("arial.ttf", 13)
except:
    font_b = ImageFont.load_default()
    font = font_b
    font_s = font_b

y = 40
draw.text((50, y), "NEXGEN TECHNOLOGIES PVT. LTD.", fill="#1a1a2e", font=font_b); y += 30
draw.text((50, y), "45 Innovation Park, Whitefield", fill="#444", font=font_s); y += 20
draw.text((50, y), "Bangalore, Karnataka 560066", fill="#444", font=font_s); y += 20
draw.text((50, y), "GSTIN: 29AADCN5678K1Z5", fill="#444", font=font_s); y += 40

draw.text((550, 40), "INVOICE", fill="#2d2d7f", font=font_b)
draw.text((550, 70), "Invoice No: NXT-2026-0453", fill="#333", font=font)
draw.text((550, 95), "Date: 12/05/2026", fill="#333", font=font)

draw.line([(50, y), (750, y)], fill="#cccccc", width=2); y += 20

draw.text((50, y), "Bill To:", fill="#666", font=font_s); y += 20
draw.text((50, y), "Reliance Digital Services", fill="#333", font=font); y += 22
draw.text((50, y), "3rd Floor, Jio Tower, BKC", fill="#444", font=font_s); y += 18
draw.text((50, y), "Mumbai, Maharashtra 400051", fill="#444", font=font_s); y += 40

draw.line([(50, y), (750, y)], fill="#cccccc", width=2); y += 10

draw.text((50, y), "Description", fill="#2d2d7f", font=font)
draw.text((400, y), "Qty", fill="#2d2d7f", font=font)
draw.text((500, y), "Rate", fill="#2d2d7f", font=font)
draw.text((630, y), "Amount", fill="#2d2d7f", font=font)
y += 25
draw.line([(50, y), (750, y)], fill="#dddddd", width=1); y += 10

items = [
    ("Cloud Infrastructure Setup", "1", "85,000.00", "85,000.00"),
    ("API Integration Service", "2", "32,500.00", "65,000.00"),
    ("Security Audit & Compliance", "1", "45,000.00", "45,000.00"),
    ("Annual Maintenance Contract", "1", "28,000.00", "28,000.00"),
    ("Data Migration Service", "1", "35,000.00", "35,000.00"),
]

for desc, qty, rate, amt in items:
    draw.text((50, y), desc, fill="#333", font=font)
    draw.text((420, y), qty, fill="#333", font=font)
    draw.text((490, y), rate, fill="#333", font=font)
    draw.text((630, y), amt, fill="#333", font=font)
    y += 25

y += 10
draw.line([(50, y), (750, y)], fill="#cccccc", width=2); y += 15

draw.text((490, y), "Subtotal:", fill="#333", font=font)
draw.text((630, y), "2,58,000.00", fill="#333", font=font); y += 25

draw.text((490, y), "CGST @9%:", fill="#333", font=font)
draw.text((630, y), "23,220.00", fill="#333", font=font); y += 25

draw.text((490, y), "SGST @9%:", fill="#333", font=font)
draw.text((630, y), "23,220.00", fill="#333", font=font); y += 25

draw.text((490, y), "Total GST:", fill="#333", font=font)
draw.text((630, y), "46,440.00", fill="#333", font=font); y += 10

draw.line([(480, y), (750, y)], fill="#2d2d7f", width=2); y += 10

draw.text((490, y), "TOTAL:", fill="#1a1a2e", font=font_b)
draw.text((630, y), "3,04,440.00", fill="#1a1a2e", font=font_b); y += 50

draw.text((50, y), "Payment Terms: Net 30 Days", fill="#666", font=font_s); y += 20
draw.text((50, y), "Bank: ICICI Bank | A/C: 12345678901234 | IFSC: ICIC0001234", fill="#666", font=font_s)

out = os.path.join(os.path.dirname(__file__), "data", "test_invoice_real.png")
img.save(out, "PNG")
print(f"Invoice saved: {out}")
