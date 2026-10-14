import sys
import time
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from fastapi.testclient import TestClient

# Add backend root to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.services.ocr_service import ocr_available

client = TestClient(app)


def create_digital_pdf(file_path: Path):
    """Creates a sample digital text-based PDF report."""
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 500, 700)
    text = (
        "METROPOLITAN LABORATORY REPORT\n"
        "Patient: Jane Doe | Age: 34 | Sex: Female\n"
        "Test Name              Result    Reference Unit\n"
        "Hemoglobin             14.2      12.0 - 15.5 g/dL\n"
        "White Blood Cells      6.8       4.5 - 11.0  x10^3/uL\n"
        "Platelet Count         250       150 - 450   x10^3/uL\n"
        "Fasting Glucose        92        70 - 99     mg/dL\n"
    )
    page.insert_textbox(rect, text, fontsize=12)
    doc.save(str(file_path))
    doc.close()


def create_sample_image(file_path: Path):
    """Creates a sample image report containing drawn text."""
    img = Image.new('RGB', (600, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 30), "LAB RESULT REPORT", fill=(0, 0, 0))
    draw.text((30, 70), "Hemoglobin: 13.8 g/dL", fill=(0, 0, 0))
    draw.text((30, 110), "WBC: 7.2 x10^3/uL", fill=(0, 0, 0))
    draw.text((30, 150), "Platelets: 280 x10^3/uL", fill=(0, 0, 0))
    img.save(str(file_path))


def create_scanned_pdf(pdf_path: Path, img_path: Path):
    """Creates a scanned PDF containing an image instead of selectable text."""
    doc = fitz.open()
    page = doc.new_page(width=600, height=400)
    page.insert_image(fitz.Rect(0, 0, 600, 400), filename=str(img_path))
    doc.save(str(pdf_path))
    doc.close()


SCRATCH = backend_dir / "scratch_test_files"


def _paths():
    SCRATCH.mkdir(exist_ok=True)
    digital = SCRATCH / "sample_digital_report.pdf"
    image = SCRATCH / "sample_scanned_image.png"
    scanned = SCRATCH / "sample_scanned_report.pdf"
    corrupt = SCRATCH / "corrupted_report.pdf"
    if not digital.exists():
        create_digital_pdf(digital)
    if not image.exists():
        create_sample_image(image)
    if not scanned.exists():
        create_scanned_pdf(scanned, image)
    corrupt.write_bytes(b"%PDF-1.4 BROKEN INVALID CORRUPTED CONTENT")
    return digital, image, scanned, corrupt


def _upload(path, name, mime):
    with open(path, "rb") as f:
        resp = client.post("/api/reports/upload", files={"file": (name, f, mime)})
    assert resp.status_code == 201, f"Upload failed: {resp.text}"
    body = resp.json()
    return body["reportId"], {"X-Report-Token": body["accessToken"]}


def test_digital_pdf_extraction():
    digital, _, _, _ = _paths()
    report_id, headers = _upload(digital, "report.pdf", "application/pdf")
    resp = client.post(f"/api/reports/{report_id}/extract", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["reportId"] == report_id
    assert data["status"] == "completed"
    assert data["extractionMethod"] == "pymupdf"
    assert data["pageCount"] == 1
    assert "Hemoglobin" in data["text"]
    assert "METROPOLITAN" in data["text"]


def test_scanned_pdf_extraction():
    _, _, scanned, _ = _paths()
    report_id, headers = _upload(scanned, "scanned_report.pdf", "application/pdf")
    resp = client.post(f"/api/reports/{report_id}/extract", headers=headers)
    if ocr_available():
        assert resp.status_code == 200, resp.text
        assert resp.json()["extractionMethod"] == "paddleocr"
        assert len(resp.json()["text"]) > 0
    else:
        # Without PaddleOCR the API must explain clearly instead of failing silently
        assert resp.status_code == 400
        assert "OCR is not available" in resp.json()["detail"]


def test_image_extraction():
    _, image, _, _ = _paths()
    report_id, headers = _upload(image, "lab_image.png", "image/png")
    resp = client.post(f"/api/reports/{report_id}/extract", headers=headers)
    if ocr_available():
        assert resp.status_code == 200, resp.text
        assert resp.json()["extractionMethod"] == "paddleocr"
    else:
        assert resp.status_code == 400
        assert "OCR is not available" in resp.json()["detail"]


def test_corrupted_pdf_returns_400():
    _, _, _, corrupt = _paths()
    report_id, headers = _upload(corrupt, "corrupt.pdf", "application/pdf")
    resp = client.post(f"/api/reports/{report_id}/extract", headers=headers)
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "Corrupted" in detail or "invalid" in detail or "failed" in detail


def test_unknown_report_returns_404():
    resp = client.post("/api/reports/rep_invalid_99999/extract")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"]
