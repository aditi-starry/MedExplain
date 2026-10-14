import re
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import fitz  # PyMuPDF

from app.config import MAX_PDF_PAGES
from app.services.ocr_service import ocr_available, run_paddle_ocr_on_bytes, run_paddle_ocr_on_file

logger = logging.getLogger(__name__)

OCR_UNAVAILABLE_MESSAGE = (
    "This looks like a scanned document or photo, but OCR is not available on this server. "
    "Please upload a digital (text-based) PDF report."
)

# Minimum non-whitespace characters required to classify a PDF as digital text-based
DIGITAL_TEXT_THRESHOLD = 50


def clean_raw_text(text: str) -> str:
    """
    Performs basic whitespace cleanup on extracted text while preserving page structure
    and line breaks.
    """
    if not text:
        return ""

    # Replace windows line endings
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # Remove excessive blank lines (more than 2 consecutive newlines)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Trim leading/trailing whitespace of each line
    lines = [line.strip() for line in text.split('\n')]
    cleaned = "\n".join(lines).strip()

    return cleaned


def extract_from_digital_pdf(doc: fitz.Document) -> Tuple[str, int]:
    """
    Extracts text page by page from a digital PDF using PyMuPDF.

    Returns:
        Tuple of (extracted_text, page_count)
    """
    page_count = len(doc)
    page_texts = []

    for idx, page in enumerate(doc):
        page_str = page.get_text("text") or ""
        page_str_cleaned = page_str.strip()
        if page_str_cleaned:
            if page_count > 1:
                page_texts.append(f"--- Page {idx + 1} ---\n{page_str_cleaned}")
            else:
                page_texts.append(page_str_cleaned)

    full_text = "\n\n".join(page_texts)
    return clean_raw_text(full_text), page_count


def extract_from_scanned_pdf(doc: fitz.Document) -> Tuple[str, int]:
    """
    Renders pages of a scanned PDF into image pixmaps and extracts text via PaddleOCR.

    Returns:
        Tuple of (extracted_ocr_text, page_count)
    """
    page_count = len(doc)
    ocr_page_texts = []

    for idx, page in enumerate(doc):
        # Render PDF page to pixmap at 150 DPI for accurate OCR readability
        pix = page.get_pixmap(dpi=150)
        img_bytes = pix.tobytes("png")

        try:
            page_text = run_paddle_ocr_on_bytes(img_bytes)
            page_text_cleaned = page_text.strip()
            if page_text_cleaned:
                if page_count > 1:
                    ocr_page_texts.append(f"--- Page {idx + 1} ---\n{page_text_cleaned}")
                else:
                    ocr_page_texts.append(page_text_cleaned)
        except Exception as e:
            logger.warning(f"OCR failed for page {idx + 1} of PDF: {e}")

    full_text = "\n\n".join(ocr_page_texts)
    return clean_raw_text(full_text), page_count


def extract_from_image(file_path: Path) -> Tuple[str, int]:
    """
    Extracts text from an image file (PNG, JPG, JPEG) using PaddleOCR.

    Returns:
        Tuple of (extracted_ocr_text, page_count=1)
    """
    try:
        raw_text = run_paddle_ocr_on_file(file_path)
        return clean_raw_text(raw_text), 1
    except Exception as e:
        logger.error(f"Image OCR failed for file {file_path.name}: {e}")
        raise ValueError(f"Failed to read image document: {str(e)}") from e


def extract_document_text(file_path: Path, report_id: str) -> Dict[str, Any]:
    """
    Main document classification and text extraction pipeline for Sprint 3.

    Flow:
    1. Detect file type (PDF vs Image).
    2. For PDF: Try PyMuPDF -> count non-whitespace text.
       If >= 50 non-whitespace chars -> return PyMuPDF text (digital PDF).
       Else -> rasterize pages and run PaddleOCR (scanned PDF).
    3. For Image: Run PaddleOCR directly.

    Returns:
        Dict matching ReportExtractionResponse:
        {
            "reportId": report_id,
            "status": "completed",
            "extractionMethod": "pymupdf" | "paddleocr",
            "pageCount": int,
            "text": str
        }
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Report file not found for report ID '{report_id}'.")

    extension = file_path.suffix.lower().lstrip('.')

    if extension == 'pdf':
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            logger.error(f"Failed to open PDF document {file_path.name}: {e}")
            raise ValueError("Corrupted or invalid PDF document.") from e

        try:
            if len(doc) == 0:
                raise ValueError("PDF document contains no pages.")
            if len(doc) > MAX_PDF_PAGES:
                raise ValueError(f"PDF has {len(doc)} pages; the maximum supported is {MAX_PDF_PAGES}.")

            # 1. Attempt digital text extraction via PyMuPDF
            digital_text, page_count = extract_from_digital_pdf(doc)
            non_whitespace_count = len(re.sub(r'\s+', '', digital_text))

            # 2. Check if text meets digital PDF threshold
            if non_whitespace_count >= DIGITAL_TEXT_THRESHOLD:
                logger.info(
                    f"Report {report_id}: Digital PDF detected ({non_whitespace_count} text chars)."
                )
                return {
                    "reportId": report_id,
                    "status": "completed",
                    "extractionMethod": "pymupdf",
                    "pageCount": page_count,
                    "text": digital_text
                }

            # 3. Fallback to scanned PDF OCR extraction
            if not ocr_available():
                raise ValueError(OCR_UNAVAILABLE_MESSAGE)
            logger.info(
                f"Report {report_id}: Scanned PDF detected ({non_whitespace_count} digital chars). Triggering PaddleOCR."
            )
            ocr_text, page_count = extract_from_scanned_pdf(doc)

            if not ocr_text:
                raise ValueError("No readable text could be extracted from scanned PDF report.")

            return {
                "reportId": report_id,
                "status": "completed",
                "extractionMethod": "paddleocr",
                "pageCount": page_count,
                "text": ocr_text
            }
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Extraction error processing PDF {file_path.name}: {e}")
            raise ValueError(f"Document text extraction failed: {str(e)}") from e
        finally:
            if 'doc' in locals() and doc and not doc.is_closed:
                doc.close()

    elif extension in {'png', 'jpg', 'jpeg'}:
        if not ocr_available():
            raise ValueError(OCR_UNAVAILABLE_MESSAGE)
        ocr_text, page_count = extract_from_image(file_path)
        if not ocr_text:
            raise ValueError("No readable text could be extracted from image report.")

        return {
            "reportId": report_id,
            "status": "completed",
            "extractionMethod": "paddleocr",
            "pageCount": page_count,
            "text": ocr_text
        }

    else:
        raise ValueError(f"Unsupported file format '.{extension}'.")
