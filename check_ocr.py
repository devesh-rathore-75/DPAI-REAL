import sys, json
sys.stdout.reconfigure(encoding="utf-8")
import requests

r = requests.get("http://localhost:8000/documents")
docs = r.json()["documents"]
sharma = [x for x in docs if "sharma" in x["filename"]]
if sharma:
    doc_id = sharma[0]["document_id"]
    r2 = requests.get(f"http://localhost:8000/documents/{doc_id}")
    d = r2.json()
    print("RAW OCR TEXT:")
    print(d["raw_text"])
else:
    print("No sharma invoice found")
