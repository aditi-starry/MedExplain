import importlib.util
import io
import logging
from pathlib import Path
from typing import Optional, List
import numpy as np
from PIL import Image, ImageOps

from app.config import ENABLE_OCR

logger = logging.getLogger(__name__)

# Module-level singleton for PaddleOCR engine
_ocr_engine = None


def ocr_available() -> bool:
    """True when OCR is enabled and PaddleOCR is installed (does not load the model)."""
    return ENABLE_OCR and importlib.util.find_spec("paddleocr") is not None


def get_ocr_engine():
    """
    Lazy loads and returns the global PaddleOCR engine instance.
    """
    global _ocr_engine
    if not ocr_available():
        return None
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            # Initialize PaddleOCR with ONNX Runtime inference engine
            _ocr_engine = PaddleOCR(engine='onnxruntime', lang='en')
            logger.info("PaddleOCR engine successfully initialized.")
        except Exception as e:
            logger.warning(f"Failed to initialize PaddleOCR engine: {e}")
            _ocr_engine = False
    return _ocr_engine if _ocr_engine is not False else None


def _parse_ocr_result(result) -> str:
    """
    Extracts text lines from PaddleOCR output structure.
    Supports both PaddleOCR 3.x format (list of dict-like OCRResult with 'rec_texts')
    and legacy PaddleOCR 2.x nested list format.
    """
    if not result:
        return ""

    extracted_lines: List[str] = []

    for page_res in result:
        if page_res is None:
            continue

        # PaddleOCR 3.x result structure (dict-like with 'rec_texts' key)
        if isinstance(page_res, dict) or hasattr(page_res, 'get'):
            rec_texts = page_res.get('rec_texts')
            if rec_texts and isinstance(rec_texts, list):
                for text_item in rec_texts:
                    line_text = str(text_item).strip()
                    if line_text:
                        extracted_lines.append(line_text)
                continue

        # Legacy PaddleOCR 2.x structure: [ [box, (text, conf)], ... ]
        if isinstance(page_res, list):
            for line_item in page_res:
                if not line_item:
                    continue
                # Line item structure: [box, (text, confidence)]
                if isinstance(line_item, (list, tuple)) and len(line_item) >= 2:
                    text_info = line_item[1]
                    if isinstance(text_info, (list, tuple)) and len(text_info) > 0:
                        line_text = str(text_info[0]).strip()
                        if line_text:
                            extracted_lines.append(line_text)
                    elif isinstance(text_info, str):
                        line_text = text_info.strip()
                        if line_text:
                            extracted_lines.append(line_text)

    return "\n".join(extracted_lines)


def run_paddle_ocr_on_bytes(image_bytes: bytes) -> str:
    """
    Performs OCR on raw image bytes using PaddleOCR.

    Returns:
        Extracted raw text string.
    """
    engine = get_ocr_engine()
    if engine is None:
        raise RuntimeError("PaddleOCR engine is unavailable on this system environment.")

    try:
        # Load image via Pillow and ensure RGB format
        pil_img = Image.open(io.BytesIO(image_bytes))
        pil_img = ImageOps.exif_transpose(pil_img)
        if pil_img.mode != 'RGB':
            pil_img = pil_img.convert('RGB')

        img_np = np.array(pil_img)
        if hasattr(engine, 'predict'):
            ocr_res = engine.predict(img_np)
        else:
            ocr_res = engine.ocr(img_np)
        return _parse_ocr_result(ocr_res)
    except Exception as e:
        logger.error(f"OCR execution failed on image bytes: {str(e)}")
        raise RuntimeError(f"OCR processing failed: {str(e)}") from e


def run_paddle_ocr_on_file(image_path: Path) -> str:
    """
    Performs OCR on an image file path using PaddleOCR.

    Returns:
        Extracted raw text string.
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        return run_paddle_ocr_on_bytes(image_bytes)
    except Exception as e:
        logger.error(f"OCR execution failed on file {image_path.name}: {str(e)}")
        raise
