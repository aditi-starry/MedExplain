"""PDF summary and report comparison tests."""
import pymupdf
import pytest

from app.models.report import ExtractedParameter
from app.services.comparison import compare_parameters, extract_report_date, units_compatible
from conftest import SAMPLE_PREVIOUS


@pytest.mark.parametrize("language", ["en", "hi", "mr"])
def test_pdf_summary_downloads(client, upload, language):
    report_id, headers = upload()
    resp = client.get(f"/api/reports/{report_id}/summary.pdf?language={language}", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content.startswith(b"%PDF")
    doc = pymupdf.open(stream=resp.content, filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    assert "MedExplain AI" in text
    for value in ("Hemoglobin", "11.2 g/dL", "Ferritin", "medlineplus.gov"):
        assert value in text, value
    assert "Demo Patient" not in text  # patient identifiers are not copied into the summary
    if language != "en":
        assert any("\u0900" <= ch <= "\u097f" for ch in text)


def test_pdf_uses_cached_ai_explanations(client, upload, mock_llm):
    from test_sprint6 import good_ai_response
    mock_llm.response = good_ai_response
    report_id, headers = upload()
    client.post(f"/api/reports/{report_id}/explain", json={"language": "en"}, headers=headers)
    resp = client.get(f"/api/reports/{report_id}/summary.pdf?language=en", headers=headers)
    text = "".join(p.get_text() for p in pymupdf.open(stream=resp.content, filetype="pdf"))
    assert "Gemini AI" in text
    assert "Should my Hemoglobin be checked again?" in text


def test_compare_reports_end_to_end(client, upload):
    prev_id, prev_headers = upload(SAMPLE_PREVIOUS, "previous.pdf")
    cur_id, cur_headers = upload()
    body = {"previousReportId": prev_id, "previousToken": prev_headers["X-Report-Token"]}
    resp = client.post(f"/api/reports/{cur_id}/compare", json=body, headers=cur_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["previousDate"] == "2026-04-02" and data["currentDate"] == "2026-10-08"
    rows = {r["name"]: r for r in data["rows"]}
    hb = rows["Hemoglobin"]
    assert hb["status"] == "compared" and hb["difference"] == pytest.approx(-1.2) and hb["direction"] == "decreased"
    assert hb["percentChange"] == pytest.approx(-9.7)
    assert rows["Vitamin D"]["status"] == "incompatible_units"  # nmol/L vs ng/mL
    assert rows["Vitamin D"]["difference"] is None
    assert rows["Ferritin"]["status"] == "only_in_current"
    # Neutral wording only: no improvement/worsening labels anywhere
    assert "improv" not in resp.text.lower() and "worse" not in resp.text.lower()


def test_compare_requires_previous_report_token(client, upload):
    prev_id, _ = upload(SAMPLE_PREVIOUS, "previous.pdf")
    cur_id, cur_headers = upload()
    body = {"previousReportId": prev_id, "previousToken": "not-the-right-token"}
    assert client.post(f"/api/reports/{cur_id}/compare", json=body, headers=cur_headers).status_code == 404


def test_unit_compatibility():
    assert units_compatible("mg/dL", "mg/dl")
    assert units_compatible("x10^3/uL", "10^9/L")
    assert units_compatible("mEq/L", "mmol/L", "Sodium")
    assert not units_compatible("mEq/L", "mmol/L", "Calcium")
    assert not units_compatible("ng/mL", "nmol/L")
    assert not units_compatible(None, "mg/dL")


def test_compare_handles_missing_values_and_zero():
    prev = [ExtractedParameter(name="CRP", value=0.0, unit="mg/L"), ExtractedParameter(name="ESR", value=None, unit="mm/hr")]
    cur = [ExtractedParameter(name="CRP", value=2.0, unit="mg/L"), ExtractedParameter(name="ESR", value=10, unit="mm/hr")]
    rows = {r.name: r for r in compare_parameters(prev, cur)}
    assert rows["CRP"].difference == 2.0 and rows["CRP"].percentChange is None
    assert rows["ESR"].status == "missing_value"


def test_report_date_extraction():
    assert extract_report_date("Report Date: 08/10/2026") == ("2026-10-08", "08/10/2026")
    assert extract_report_date("Collected On : 20-Feb-2023 11:09")[0] == "2023-02-20"
    assert extract_report_date("Sample date 2025-01-31")[0] == "2025-01-31"
    assert extract_report_date("Hemoglobin 14.2 12.0 - 15.5") == (None, None)