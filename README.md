# DPAI — AI Document & Process Automation (Invoice System)

A modular, production-ready invoice automation system powered by OCR and intelligent data extraction.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)
![Streamlit](https://img.shields.io/badge/Streamlit-1.38-red)

---

## 🏗️ Architecture

```
dpai/
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application & endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr_service.py      # OCR processing (Tesseract)
│   │   ├── extraction.py       # Regex-based data extraction
│   │   ├── validation.py       # Field validation & duplicate detection
│   │   └── export_service.py   # CSV & JSON export
│   └── utils/
│       ├── __init__.py
│       └── helpers.py           # Shared utilities
├── frontend/
│   └── app.py                   # Streamlit UI
├── data/
│   ├── uploads/                 # Uploaded files
│   └── results/                 # Processing results
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd dpai
pip install -r requirements.txt
```

### 2. Start the Backend

```bash
cd dpai
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`
Interactive docs at: `http://localhost:8000/docs`

### 3. Start the Frontend

Open a **new terminal**:

```bash
cd dpai
python -m streamlit run frontend/app.py --server.port 8501
```

The UI will be available at: `http://localhost:8501`

---

## 🔍 OCR Engine

### Demo Mode (No Tesseract)
The system works **out of the box** without Tesseract installed. It uses a built-in sample invoice for demonstration purposes.

### Full OCR Mode (With Tesseract)
For real document processing, install Tesseract:

- **Windows**: Download from [UB-Mannheim](https://github.com/UB-Mannheim/tesseract/wiki)
- **macOS**: `brew install tesseract`
- **Linux**: `sudo apt install tesseract-ocr`

For PDF support, also install Poppler:
- **Windows**: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases/)
- **macOS**: `brew install poppler`
- **Linux**: `sudo apt install poppler-utils`

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | System health check |
| `/upload` | POST | Upload invoice file |
| `/process` | POST | Run OCR on uploaded document |
| `/extract` | POST | Extract structured data |
| `/validate` | POST | Validate extracted data |
| `/pipeline` | POST | Full pipeline (upload → OCR → extract → validate) |
| `/export/csv` | GET | Export all records as CSV |
| `/export/json` | GET | Export all records as JSON |
| `/documents` | GET | List all processed documents |

---

## 📊 Extracted Fields

| Field | Description |
|---|---|
| Invoice Number | Unique invoice identifier |
| Date | Invoice date (multiple formats) |
| Vendor Name | Seller/supplier company name |
| Total Amount | Grand total amount |
| GST | GSTIN, CGST, SGST, IGST, Total GST |

---

## ⚡ Features

- **Smart OCR** — Tesseract-based with demo fallback
- **Multi-pattern Extraction** — Robust regex engine with fallback patterns
- **Validation Engine** — Missing fields, format checks, duplicate detection
- **Export** — CSV and JSON download
- **Premium UI** — Dark theme with glassmorphism, card-based layout
- **Modular Design** — Easy to extend with new extractors or validators
- **File Dedup** — SHA-256 hash-based duplicate file detection

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| Frontend | Streamlit |
| OCR | Tesseract (pytesseract) |
| PDF Support | pdf2image + Poppler |
| Data | Pandas, CSV, JSON |

---

## 📈 Scaling to SaaS

This MVP is designed to scale. Next steps:
1. **Database** — Replace in-memory store with PostgreSQL/MongoDB
2. **Auth** — Add JWT-based authentication
3. **Queue** — Use Celery/Redis for async processing
4. **Storage** — S3/GCS for file storage
5. **ML** — Replace regex with trained NER models
6. **Multi-tenant** — Organization-based data isolation
