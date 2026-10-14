import sys
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.services.parameter_extractor import extract_parameters

client = TestClient(app)


def test_columnar_and_tabular_extraction():
    """Tests whitespace columnar digital PDF report formats."""
    text = (
        "METROPOLITAN CLINICAL LABORATORY\n"
        "Patient: Jane Doe | Age: 34 | Sex: Female\n"
        "Test Name              Result    Reference Unit\n"
        "Hemoglobin             14.2      12.0 - 15.5 g/dL\n"
        "White Blood Cells      6.8       4.5 - 11.0  x10^3/uL\n"
        "Platelet Count         250       150 - 450   x10^3/uL\n"
        "Fasting Glucose        92        70 - 99     mg/dL\n"
    )
    params = extract_parameters(text)
    assert len(params) == 4, f"Expected 4 parameters, got {len(params)}"

    param_map = {p.name: p for p in params}

    # Hemoglobin
    assert "Hemoglobin" in param_map
    hgb = param_map["Hemoglobin"]
    assert hgb.value == 14.2
    assert "g/dL" in (hgb.unit or "")
    assert hgb.referenceLow == 12.0
    assert hgb.referenceHigh == 15.5
    assert "12.0 - 15.5" in (hgb.referenceRaw or "")

    # White Blood Cells
    assert "White Blood Cells" in param_map
    wbc = param_map["White Blood Cells"]
    assert wbc.value == 6.8
    assert wbc.referenceLow == 4.5
    assert wbc.referenceHigh == 11.0

    # Platelet Count
    assert "Platelet Count" in param_map
    plt = param_map["Platelet Count"]
    assert plt.value == 250.0
    assert plt.referenceLow == 150.0
    assert plt.referenceHigh == 450.0

    # Fasting Glucose
    assert "Fasting Glucose" in param_map
    glu = param_map["Fasting Glucose"]
    assert glu.value == 92.0
    assert glu.referenceLow == 70.0
    assert glu.referenceHigh == 99.0
    print("  [PASS] Columnar/tabular text extraction verified.")


def test_pipe_delimited_extraction():
    """Tests pipe-separated table formats e.g. WBC | 7200 | /µL | 4000 - 11000."""
    text = (
        "WBC | 7200 | /µL | 4000 - 11000\n"
        "Hemoglobin | 13.8 | g/dL | 12.0 - 16.0\n"
        "Serum Creatinine | 0.9 | mg/dL | 0.6 - 1.2\n"
    )
    params = extract_parameters(text)
    assert len(params) == 3, f"Expected 3 parameters, got {len(params)}"

    param_map = {p.name: p for p in params}
    wbc = param_map["White Blood Cells"]
    assert wbc.value == 7200.0
    assert wbc.referenceLow == 4000.0
    assert wbc.referenceHigh == 11000.0

    creat = param_map["Serum Creatinine"]
    assert creat.value == 0.9
    assert creat.referenceLow == 0.6
    assert creat.referenceHigh == 1.2
    print("  [PASS] Pipe-delimited extraction verified.")


def test_key_value_and_inequality_ranges():
    """Tests key-value lines and one-sided (< 150, > 40, <= 4.0, >= 20.0) reference ranges and explicit Reference Range."""
    text = (
        "Hemoglobin: 13.8 g/dL\n"
        "Total Cholesterol: 195 mg/dL (< 200)\n"
        "HDL Cholesterol: 55 mg/dL (> 40)\n"
        "Triglycerides: 140 mg/dL (less than 150)\n"
        "TSH: 2.1 uIU/mL [0.4 - 4.0]\n"
        "Total PSA: 2.5 ng/mL (<= 4.0)\n"
        "Ferritin: 35.0 ng/mL (>= 20.0)\n"
        "Serum Albumin: 4.2 g/dL (Reference Range: 3.5 - 5.0 g/dL)\n"
    )
    params = extract_parameters(text)
    assert len(params) == 8, f"Expected 8 parameters, got {len(params)}"

    param_map = {p.name: p for p in params}

    # Hemoglobin has NO reference range in this line -> must be None!
    hgb = param_map["Hemoglobin"]
    assert hgb.value == 13.8
    assert hgb.referenceLow is None, "Expected referenceLow to be None when omitted"
    assert hgb.referenceHigh is None, "Expected referenceHigh to be None when omitted"
    assert hgb.referenceRaw is None

    # Cholesterol has upper bound (< 200)
    chol = param_map["Total Cholesterol"]
    assert chol.value == 195.0
    assert chol.referenceLow is None
    assert chol.referenceHigh == 200.0

    # HDL has lower bound (> 40)
    hdl = param_map["HDL Cholesterol"]
    assert hdl.value == 55.0
    assert hdl.referenceLow == 40.0
    assert hdl.referenceHigh is None

    # Triglycerides (less than 150)
    tg = param_map["Triglycerides"]
    assert tg.value == 140.0
    assert tg.referenceLow is None
    assert tg.referenceHigh == 150.0

    # TSH bracketed range [0.4 - 4.0]
    tsh = param_map["TSH"]
    assert tsh.value == 2.1
    assert tsh.referenceLow == 0.4
    assert tsh.referenceHigh == 4.0

    # Total PSA (<= 4.0)
    psa = param_map["Total PSA"]
    assert psa.value == 2.5
    assert psa.referenceLow is None
    assert psa.referenceHigh == 4.0

    # Ferritin (>= 20.0)
    ferr = param_map["Ferritin"]
    assert ferr.value == 35.0
    assert ferr.referenceLow == 20.0
    assert ferr.referenceHigh is None

    # Serum Albumin with explicit Reference Range
    alb = param_map["Albumin"]
    assert alb.value == 4.2
    assert alb.referenceLow == 3.5
    assert alb.referenceHigh == 5.0
    assert "Reference Range: 3.5 - 5.0" in (alb.referenceRaw or "")
    print("  [PASS] Key-value and inequality reference ranges verified.")


def test_missing_and_ambiguous_data_preserved_as_none():
    """
    Confirms requirement 3: Do NOT invent reference ranges or guess missing values.
    If a value cannot be reliably extracted, preserve it as None rather than fabricating data.
    """
    text = (
        "Hemoglobin: pending\n"  # Non-numeric value -> should not extract invalid number
        "Platelet Count: 280 x10^3/uL\n"  # Valid value, missing reference range
        "Random Noise Text Line with No Test\n"
    )
    params = extract_parameters(text)
    # Only Platelet Count has a valid numeric value
    assert len(params) == 1
    plt = params[0]
    assert plt.name == "Platelet Count"
    assert plt.value == 280.0
    assert plt.referenceLow is None
    assert plt.referenceHigh is None
    assert plt.referenceRaw is None
    print("  [PASS] Missing and ambiguous data preserved as None (no fabricated data).")


def test_full_api_extraction_endpoint():
    """Tests the FastAPI extraction endpoint returning structured parameters."""
    scratch_dir = backend_dir / "scratch_test_files"
    digital_pdf = scratch_dir / "sample_digital_report.pdf"

    with open(digital_pdf, "rb") as f:
        resp = client.post("/api/reports/upload", files={"file": ("report.pdf", f, "application/pdf")})
    assert resp.status_code == 201
    report_id = resp.json()["reportId"]
    headers = {"X-Report-Token": resp.json()["accessToken"]}

    # Call extraction endpoint
    extract_resp = client.post(f"/api/reports/{report_id}/extract", headers=headers)
    assert extract_resp.status_code == 200
    data = extract_resp.json()

    assert "parameters" in data
    params = data["parameters"]
    assert len(params) >= 4, f"Expected at least 4 parameters, got {len(params)}"

    param_names = [p["name"] for p in params]
    assert "Hemoglobin" in param_names
    assert "White Blood Cells" in param_names
    assert "Platelet Count" in param_names
    assert "Fasting Glucose" in param_names

    # Also test dedicated GET /{report_id}/parameters
    param_resp = client.get(f"/api/reports/{report_id}/parameters", headers=headers)
    assert param_resp.status_code == 200
    param_data = param_resp.json()
    assert len(param_data) == len(params)
    print("  [PASS] Full API extraction endpoint verified with structured parameters.")


def test_unfamiliar_parameter_extraction():
    """
    Tests extraction of valid laboratory parameters not present in the hardcoded catalog.
    Verifies that parameter extraction is not restricted to a hardcoded whitelist.
    """
    text = (
        "Serum Ceruloplasmin: 28.5 mg/dL (20.0 - 60.0)\n"
        "Troponin I             0.02      < 0.04      ng/mL\n"
        "Zinc | 85.0 | ug/dL | 60.0 - 120.0\n"
        "D-Dimer: 0.35 ug/mL (< 0.50)\n"
    )
    params = extract_parameters(text)
    assert len(params) == 4, f"Expected 4 parameters, got {len(params)}"

    param_map = {p.name: p for p in params}

    # Unfamiliar Key-Value parameter
    assert "Serum Ceruloplasmin" in param_map
    cerulo = param_map["Serum Ceruloplasmin"]
    assert cerulo.value == 28.5
    assert cerulo.referenceLow == 20.0
    assert cerulo.referenceHigh == 60.0

    # Unfamiliar Columnar parameter with one-sided range
    assert "Troponin I" in param_map
    trop = param_map["Troponin I"]
    assert trop.value == 0.02
    assert trop.referenceLow is None
    assert trop.referenceHigh == 0.04

    # Unfamiliar Pipe-delimited parameter
    assert "Zinc" in param_map
    zinc = param_map["Zinc"]
    assert zinc.value == 85.0
    assert zinc.referenceLow == 60.0
    assert zinc.referenceHigh == 120.0

    # Unfamiliar parameter with novel clinical unit (ug/mL)
    assert "D-Dimer" in param_map
    ddimer = param_map["D-Dimer"]
    assert ddimer.value == 0.35
    assert ddimer.unit == "ug/mL"
    assert ddimer.referenceHigh == 0.50
    assert ddimer.referenceLow is None
    print("  [PASS] Unfamiliar valid parameter extraction verified (not whitelist-restricted).")


def test_ocr_whitespace_variations():
    """Tests handling of common PDF and OCR whitespace variations in units and values."""
    text = (
        "Hemoglobin : 14.5 g / dL (12.0 - 16.0)\n"
        "White Blood Cells : 7.5 x 10^3 / uL (4.0 - 11.0)\n"
        "Blood Sugar : 95.0 mg / dL ( 70.0 - 99.0 )\n"
    )
    params = extract_parameters(text)
    assert len(params) == 3, f"Expected 3 parameters, got {len(params)}"

    param_map = {p.name: p for p in params}
    assert "Hemoglobin" in param_map
    hgb = param_map["Hemoglobin"]
    assert hgb.value == 14.5
    assert "g" in (hgb.unit or "") and "dL" in (hgb.unit or "")

    assert "White Blood Cells" in param_map
    wbc = param_map["White Blood Cells"]
    assert wbc.value == 7.5

    assert "Fasting Glucose" in param_map
    glu = param_map["Fasting Glucose"]
    assert glu.value == 95.0
    assert glu.referenceLow == 70.0
    assert glu.referenceHigh == 99.0
    print("  [PASS] OCR whitespace variations verified.")


def test_uploaded_sample_report_regression():
    """
    Regression test for Sprint 4 parameter extraction using the uploaded sample report layout.
    Verifies:
    - Actual test parameters map correctly:
        Hemoglobin 14.5 g/dL (13.0 - 16.5)
        Cholesterol 189.0 mg/dL (<200)
        Triglyceride 168.0 mg/dL (<150)
        Fasting Blood Sugar 141.0 mg/dL (74 - 106)
    - Metadata ("Registration on : 20-Feb-2023 09:10", "Collected on", etc.) is NOT emitted as lab parameters.
    - Category labels ("Desirable : <200", "Borderline High : 200-239", "Very High : >500") are NOT emitted as separate parameters.
    - Missing or ambiguous values/ranges remain None without fabrication.
    """
    sample_text = (
        "Hemoglobin\n"
        "g/dL\n"
        "13.0 - 16.5\n"
        "Colorimetric\n"
        "14.5\n"
        "Cholesterol\n"
        "mg/dL\n"
        "Desirable : <200\n"
        "Borderline High : 200-239\n"
        "High : >240\n"
        "Cholesterol oxidase - Peroxidase method\n"
        "189.0\n"
        "Triglyceride\n"
        "H\n"
        "mg/dL\n"
        "Normal : <150\n"
        "Borderline : 150-199\n"
        "High : 200-499\n"
        "Very High : >500\n"
        "Ezymatic (Lipase/GK/GPO/POD)\n"
        "168.0\n"
        "Fasting Blood Sugar\n"
        "H\n"
        "mg/dL\n"
        "74 - 106\n"
        "GOD-POD\n"
        "141.0\n"
        "Registration on  : 20-Feb-2023 09:10\n"
        "Collected on : 20-Feb-2023 08:53\n"
        "Approved on : 20-Feb-2023 11:29\n"
        "Printed On : 28-Feb-2023 10:26\n"
        "Lab Id : 02232160XXXX\n"
        "Status : Final\n"
    )

    params = extract_parameters(sample_text)
    param_map = {p.name: p for p in params}

    # 1. Hemoglobin: 14.5 g/dL
    assert "Hemoglobin" in param_map, "Expected Hemoglobin in extracted parameters"
    hgb = param_map["Hemoglobin"]
    assert hgb.value == 14.5
    assert "g/dL" in (hgb.unit or "")
    assert hgb.referenceLow == 13.0
    assert hgb.referenceHigh == 16.5
    assert "13.0 - 16.5" in (hgb.referenceRaw or "")

    # 2. Cholesterol: 189.0 mg/dL
    chol = param_map.get("Cholesterol") or param_map.get("Total Cholesterol")
    assert chol is not None, "Expected Cholesterol/Total Cholesterol in extracted parameters"
    assert chol.value == 189.0
    assert "mg/dL" in (chol.unit or "")
    assert chol.referenceHigh == 200.0
    assert chol.referenceLow is None

    # 3. Triglyceride: 168.0 mg/dL
    tg = param_map.get("Triglyceride") or param_map.get("Triglycerides")
    assert tg is not None, "Expected Triglyceride/Triglycerides in extracted parameters"
    assert tg.value == 168.0
    assert "mg/dL" in (tg.unit or "")
    assert tg.referenceHigh == 150.0
    assert tg.referenceLow is None

    # 4. Fasting Blood Sugar: 141.0 mg/dL
    fbs = param_map.get("Fasting Blood Sugar") or param_map.get("Fasting Glucose")
    assert fbs is not None, "Expected Fasting Blood Sugar/Fasting Glucose in extracted parameters"
    assert fbs.value == 141.0
    assert "mg/dL" in (fbs.unit or "")
    assert fbs.referenceLow == 74.0
    assert fbs.referenceHigh == 106.0
    assert "74 - 106" in (fbs.referenceRaw or "")

    # 5. Metadata and category labels must NOT be emitted as test parameters
    disallowed_names = [
        "Registration on", "Collected on", "Approved on", "Printed On",
        "Lab Id", "Status", "Desirable", "Borderline High", "Borderline",
        "Very High", "High", "Normal"
    ]
    for disallowed in disallowed_names:
        assert disallowed not in param_map, f"Disallowed label '{disallowed}' emitted as laboratory parameter"

    # Also test on actual uploaded sample report PDF if available in uploads/
    sample_pdf_candidates = list((backend_dir / "uploads").glob("*sample_lab_report.pdf"))
    if sample_pdf_candidates:
        from app.services.document_extractor import extract_document_text
        pdf_path = sample_pdf_candidates[0]
        extracted_doc = extract_document_text(pdf_path, "test_rep")
        pdf_params = extract_parameters(extracted_doc.get("text", ""))
        pdf_map = {p.name: p for p in pdf_params}

        assert "Hemoglobin" in pdf_map
        assert pdf_map["Hemoglobin"].value == 14.5

        pdf_chol = pdf_map.get("Cholesterol") or pdf_map.get("Total Cholesterol")
        assert pdf_chol is not None
        assert pdf_chol.value == 189.0

        pdf_tg = pdf_map.get("Triglyceride") or pdf_map.get("Triglycerides")
        assert pdf_tg is not None
        assert pdf_tg.value == 168.0

        pdf_fbs = pdf_map.get("Fasting Blood Sugar") or pdf_map.get("Fasting Glucose")
        assert pdf_fbs is not None
        assert pdf_fbs.value == 141.0

        for disallowed in disallowed_names:
            assert disallowed not in pdf_map, f"Disallowed label '{disallowed}' was emitted in PDF extraction!"

    print("  [PASS] Uploaded sample report regression verified (Hemoglobin, Cholesterol, Triglyceride, Fasting Blood Sugar).")


def run_all_tests():
    print("=" * 60)
    print("RUNNING SPRINT 4 STRUCTURED PARAMETER EXTRACTION TESTS")
    print("=" * 60)

    test_columnar_and_tabular_extraction()
    test_pipe_delimited_extraction()
    test_key_value_and_inequality_ranges()
    test_missing_and_ambiguous_data_preserved_as_none()
    test_unfamiliar_parameter_extraction()
    test_ocr_whitespace_variations()
    test_uploaded_sample_report_regression()
    test_full_api_extraction_endpoint()

    print("\n" + "=" * 60)
    print("ALL SPRINT 4 TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
