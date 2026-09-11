import os
import re
from typing import List, Dict, Tuple, Any
import pymupdf as fitz
from PIL import Image
import pytesseract
from app.config import settings

class PDFValidationError(Exception):
    pass

def setup_tesseract() -> bool:
    """Configures Tesseract executable path if specified via environment variable or standard paths."""
    tess_env = os.getenv("TESSERACT_CMD")
    if tess_env and os.path.exists(tess_env):
        pytesseract.pytesseract.tesseract_cmd = tess_env
        return True

    # Standard Windows install locations
    std_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.path.expanduser(r"~\AppData\Local\Programs\Tesseract-OCR\tesseract.exe")
    ]
    for p in std_paths:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            return True

    return False

def clean_ocr_text(raw_text: str) -> str:
    """Cleans OCR output while preserving paragraphs and mathematical notation."""
    if not raw_text:
        return ""
    # Replace non-printable characters
    cleaned = "".join(c for c in raw_text if c.printable or c in ['\n', '\t'])
    # Normalize excessive newlines (3+ -> 2)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    # Normalize spaces within lines
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in cleaned.split('\n')]
    return "\n".join(lines).strip()

def evaluate_text_quality(text: str, min_chars: int = 30) -> bool:
    """Evaluates whether extracted text contains meaningful readable characters."""
    if not text:
        return False
    stripped = re.sub(r'\s+', '', text)
    if len(stripped) < min_chars:
        return False
    # Check ratio of alpha-numeric characters vs total non-whitespace chars
    alnum_count = sum(1 for c in stripped if c.isalnum())
    if len(stripped) > 0 and (alnum_count / len(stripped)) < 0.3:
        return False  # Garbage OCR or binary stream symbols
    return True

def validate_and_extract_pdf(
    file_path: str,
    max_size_mb: int = settings.MAX_UPLOAD_SIZE_MB
) -> Tuple[int, List[Dict[str, Any]], str]:
    """
    Validates PDF file size, integrity, and extracts page-by-page text with OCR fallback for scanned pages.
    Returns (total_pages, extracted_pages, overall_extraction_method).
    """
    if not os.path.exists(file_path):
        raise PDFValidationError("Uploaded file could not be found on server storage.")

    file_size_bytes = os.path.getsize(file_path)
    file_size_mb = file_size_bytes / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise PDFValidationError(f"File size ({file_size_mb:.1f} MB) exceeds maximum allowed limit of {max_size_mb} MB.")

    if file_size_bytes == 0:
        raise PDFValidationError("The uploaded file is empty (0 bytes).")

    setup_tesseract()

    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise PDFValidationError(f"Invalid or corrupted PDF file: {str(e)}")

    if doc.is_encrypted:
        raise PDFValidationError("Password-protected PDF files are not supported. Please remove the password and try again.")

    total_pages = len(doc)
    if total_pages == 0:
        raise PDFValidationError("The uploaded PDF has 0 pages.")

    extracted_pages = []
    text_page_count = 0
    ocr_page_count = 0
    ocr_unavailable_warned = False

    for idx, page in enumerate(doc):
        page_num = idx + 1
        raw_text = page.get_text() or ""
        cleaned_text = re.sub(r'\s+', ' ', raw_text).strip()

        if evaluate_text_quality(cleaned_text):
            extracted_pages.append({
                "page": page_num,
                "text": cleaned_text,
                "extraction_method": "text"
            })
            text_page_count += 1
        else:
            # Fallback to OCR for this scanned/image page
            print(f"[PDF] Scanned/image page detected on page {page_num}. Triggering OCR...")
            try:
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                ocr_raw = pytesseract.image_to_string(img)
                ocr_cleaned = clean_ocr_text(ocr_raw)

                if evaluate_text_quality(ocr_cleaned, min_chars=15):
                    extracted_pages.append({
                        "page": page_num,
                        "text": ocr_cleaned,
                        "extraction_method": "ocr"
                    })
                    ocr_page_count += 1
                else:
                    print(f"[PDF] Page {page_num}: OCR yielded insufficient text.")
            except (pytesseract.TesseractNotFoundError, FileNotFoundError):
                if not ocr_unavailable_warned:
                    ocr_unavailable_warned = True
                    print(f"[PDF] Tesseract OCR engine not found on server for page {page_num}.")
            except Exception as ocr_err:
                print(f"[PDF] OCR failed for page {page_num}: {str(ocr_err)}")

    doc.close()

    if not extracted_pages:
        if ocr_unavailable_warned:
            raise PDFValidationError(
                "This PDF appears to be scanned, but the OCR engine (Tesseract) is not installed on the server. "
                "Please install Tesseract OCR or upload a text-based PDF."
            )
        raise PDFValidationError("Could not extract readable text from PDF. It may contain blank or unreadable scanned pages.")

    if ocr_page_count == 0:
        overall_method = "text"
    elif text_page_count == 0:
        overall_method = "ocr"
    else:
        overall_method = "mixed"

    print(f"[PDF] Processing complete. Total pages: {total_pages}, Extracted pages: {len(extracted_pages)}, Method: {overall_method}")
    return total_pages, extracted_pages, overall_method
