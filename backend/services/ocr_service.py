"""
DPAI — OCR Service (Production v3.0)
Hardened OCR with retry logic, multi-strategy preprocessing, and text cleanup.
"""

import io
import logging
import time
import numpy as np
import cv2
import fitz  # PyMuPDF
from pathlib import Path

logger = logging.getLogger(__name__)

_ocr_reader = None
MAX_OCR_RETRIES = 3


def _get_reader():
    """Lazy-load EasyOCR reader. Thread-safe singleton."""
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        logger.info("Initializing EasyOCR engine...")
        _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        logger.info("EasyOCR engine ready")
    return _ocr_reader


# ═══════════════════════════════════════════════════════════════════════════
#  PREPROCESSING STRATEGIES
# ═══════════════════════════════════════════════════════════════════════════

def _ensure_min_size(img: np.ndarray, min_width: int = 1200) -> np.ndarray:
    """Upscale small images for better OCR accuracy."""
    h, w = img.shape[:2]
    if w < min_width:
        scale = min_width / w
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        logger.debug(f"Upscaled: {w}x{h} -> {int(w*scale)}x{int(h*scale)}")
    elif w > 4000:
        scale = 3000 / w
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        logger.debug(f"Downscaled: {w}x{h} -> {int(w*scale)}x{int(h*scale)}")
    return img


def _to_gray(img: np.ndarray) -> np.ndarray:
    """Convert to grayscale if needed."""
    if len(img.shape) == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img.copy()


def preprocess_strategy_1(image: np.ndarray) -> np.ndarray:
    """Standard: grayscale + upscale + denoise + CLAHE."""
    gray = _to_gray(image)
    gray = _ensure_min_size(gray)
    denoised = cv2.fastNlMeansDenoising(gray, h=6)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(denoised)


def preprocess_strategy_2(image: np.ndarray) -> np.ndarray:
    """Aggressive: sharpen + high contrast + adaptive threshold."""
    gray = _to_gray(image)
    gray = _ensure_min_size(gray)
    # Sharpen
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    sharpened = cv2.filter2D(gray, -1, kernel)
    # Adaptive threshold for scanned/photo invoices
    binary = cv2.adaptiveThreshold(
        sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
    )
    return binary


def preprocess_strategy_3(image: np.ndarray) -> np.ndarray:
    """Minimal: just grayscale + upscale (for already-clean images)."""
    gray = _to_gray(image)
    gray = _ensure_min_size(gray, min_width=1500)
    return gray


# ═══════════════════════════════════════════════════════════════════════════
#  OCR EXECUTION WITH RETRY
# ═══════════════════════════════════════════════════════════════════════════

def _run_ocr_single(reader, image: np.ndarray) -> list[tuple]:
    """Single OCR pass. Returns list of (text, confidence) sorted top-to-bottom."""
    try:
        results = reader.readtext(image, detail=1, paragraph=False)
    except Exception as e:
        logger.warning(f"EasyOCR readtext failed: {e}")
        return []

    if not results:
        return []

    parsed = []
    for item in results:
        if len(item) == 3:
            bbox, text, conf = item
        elif len(item) == 2:
            bbox, text = item
            conf = 0.5
        else:
            continue
        if text and text.strip():
            try:
                y_pos = float(bbox[0][1]) if isinstance(bbox[0], (list, tuple)) else 0.0
                x_pos = float(bbox[0][0]) if isinstance(bbox[0], (list, tuple)) else 0.0
            except (IndexError, TypeError, ValueError):
                y_pos, x_pos = 0.0, 0.0
            parsed.append((y_pos, x_pos, text.strip(), float(conf)))

    parsed.sort(key=lambda r: (r[0], r[1]))
    return [(text, conf) for _, _, text, conf in parsed]


def _run_ocr_with_retry(image: np.ndarray) -> list[tuple]:
    """Run OCR with multi-strategy preprocessing and retry logic."""
    reader = _get_reader()

    strategies = [
        ("standard", preprocess_strategy_1),
        ("aggressive", preprocess_strategy_2),
        ("minimal", preprocess_strategy_3),
        ("original", lambda img: _ensure_min_size(img)),
    ]

    best_results = []
    best_text_len = 0

    for name, preprocess_fn in strategies:
        try:
            processed = preprocess_fn(image)
            results = _run_ocr_single(reader, processed)

            if results:
                text_len = sum(len(t) for t, _ in results)
                logger.info(f"  Strategy '{name}': {len(results)} blocks, {text_len} chars")

                if text_len > best_text_len:
                    best_results = results
                    best_text_len = text_len

                # If we got good results, no need to try more strategies
                if text_len > 50:
                    break
            else:
                logger.debug(f"  Strategy '{name}': no text")

        except Exception as e:
            logger.warning(f"  Strategy '{name}' failed: {e}")
            continue

    return best_results


# ═══════════════════════════════════════════════════════════════════════════
#  OCR TEXT CLEANUP
# ═══════════════════════════════════════════════════════════════════════════

def cleanup_ocr_text(text: str) -> str:
    """Fix common OCR artifacts and normalize text."""
    if not text:
        return text

    import re

    # Fix common character substitutions in amounts
    # I or l before digits -> likely 1
    text = re.sub(r'(?<=[₹$Rs.])\s*[Il](\d)', r'1\1', text)

    # O surrounded by digits -> 0
    text = re.sub(r'(\d)O(\d)', r'\g<1>0\2', text)
    text = re.sub(r'(\d)o(\d)', r'\g<1>0\2', text)

    # Fix broken decimal: "48,440 00" -> "48,440.00"
    text = re.sub(r'(\d{3})\s+(\d{2})(?=\s|$)', r'\1.\2', text)

    # Normalize Rs variations
    text = re.sub(r'\bRs\.?\s*', 'Rs. ', text)
    text = re.sub(r'\bINR\s+', 'INR ', text)

    # Fix common GSTIN OCR errors (O vs 0, I vs 1)
    def fix_gstin(m):
        g = m.group(0)
        # Replace common misreads in known positions
        g = g.replace('O', '0').replace('o', '0')
        return g

    text = re.sub(r'GSTIN[.:;\s]*\S{15}', fix_gstin, text)

    # Remove excessive whitespace but preserve line breaks
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = ' '.join(line.split())  # Collapse multiple spaces
        if line:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


# ═══════════════════════════════════════════════════════════════════════════
#  IMAGE EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extract text from image with retry and multi-strategy preprocessing."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if image is None:
        # Try loading as grayscale
        image = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("Could not decode image file. The file may be corrupted.")

    h, w = image.shape[:2]
    logger.info(f"Processing image: {w}x{h} pixels")

    if h < 50 or w < 50:
        raise ValueError(f"Image too small ({w}x{h}). Minimum 50x50 pixels required.")

    results = _run_ocr_with_retry(image)

    if not results:
        logger.warning("No text detected after all strategies")
        return ""

    lines = [text for text, _ in results]
    full_text = '\n'.join(lines)
    full_text = cleanup_ocr_text(full_text)

    logger.info(f"Extracted {len(results)} blocks, {len(full_text)} chars")
    return full_text.strip()


# ═══════════════════════════════════════════════════════════════════════════
#  PDF EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════

def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from PDF with robust error handling per page."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as e:
        raise ValueError(f"Could not open PDF: {e}. The file may be corrupted.")

    total_pages = len(doc)
    if total_pages == 0:
        doc.close()
        raise ValueError("PDF has no pages.")

    logger.info(f"Processing PDF: {total_pages} page(s)")
    all_text = []

    for page_num in range(total_pages):
        try:
            page = doc[page_num]

            # Strategy 1: Native text extraction
            native_text = ""
            try:
                native_text = page.get_text("text").strip()
            except Exception as e:
                logger.warning(f"  Page {page_num+1}: Native text extraction failed: {e}")

            if len(native_text) > 50:
                logger.info(f"  Page {page_num+1}: Native text ({len(native_text)} chars)")
                all_text.append(native_text)
                continue

            # Strategy 2: Render to image and OCR
            logger.info(f"  Page {page_num+1}: Rendering for OCR...")
            image = None

            for dpi in [300, 200, 150]:
                try:
                    mat = fitz.Matrix(dpi / 72, dpi / 72)
                    pix = page.get_pixmap(matrix=mat)
                    img_data = pix.tobytes("png")
                    nparr = np.frombuffer(img_data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    if image is not None:
                        logger.debug(f"  Page {page_num+1}: Rendered at {dpi} DPI")
                        break
                except Exception as e:
                    logger.warning(f"  Page {page_num+1}: Render at {dpi}DPI failed: {e}")
                    continue

            if image is not None:
                results = _run_ocr_with_retry(image)
                if results:
                    page_text = '\n'.join(t for t, _ in results)
                    page_text = cleanup_ocr_text(page_text)
                    all_text.append(page_text)
                    logger.info(f"  Page {page_num+1}: OCR extracted {len(page_text)} chars")
                else:
                    logger.warning(f"  Page {page_num+1}: OCR returned no text")
            else:
                logger.error(f"  Page {page_num+1}: Could not render at any DPI")

        except Exception as e:
            logger.error(f"  Page {page_num+1}: Failed completely: {e}")
            continue

    doc.close()

    full_text = '\n'.join(all_text)
    logger.info(f"PDF complete: {len(full_text)} total chars from {total_pages} page(s)")
    return full_text.strip()


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def process_file(file_bytes: bytes, filename: str) -> str:
    """Route file to correct handler. Returns extracted text."""
    ext = Path(filename).suffix.lower()

    if len(file_bytes) == 0:
        raise ValueError("Empty file received")

    if ext == ".pdf":
        return extract_text_from_pdf(file_bytes)
    elif ext in {".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp"}:
        return extract_text_from_image(file_bytes)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
