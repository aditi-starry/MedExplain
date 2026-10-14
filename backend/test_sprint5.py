import sys
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.services.parameter_extractor import extract_parameters, evaluate_parameter

client = TestClient(app)


def test_two_sided_range_evaluation():
    """Tests two-sided range evaluation: within, below, above, and exact boundary values."""
    # Within Range
    assert evaluate_parameter(14.2, 12.0, 15.5, "12.0 - 15.5") == "Within Range"
    assert evaluate_parameter(12.0, 12.0, 15.5, "12.0 - 15.5") == "Within Range"  # Exact lower bound
    assert evaluate_parameter(15.5, 12.0, 15.5, "12.0 - 15.5") == "Within Range"  # Exact upper bound

    # Below Range
    assert evaluate_parameter(10.5, 12.0, 15.5, "12.0 - 15.5") == "Below Range"
    assert evaluate_parameter(11.9, 12.0, 15.5, "12.0 - 15.5") == "Below Range"

    # Above Range
    assert evaluate_parameter(17.0, 12.0, 15.5, "12.0 - 15.5") == "Above Range"
    assert evaluate_parameter(15.6, 12.0, 15.5, "12.0 - 15.5") == "Above Range"
    print("  [PASS] Two-sided range evaluation verified.")


def test_one_sided_range_evaluation():
    """Tests one-sided upper bound (<, <=) and lower bound (>, >=) evaluations."""
    # Upper bound with '<' (strict)
    assert evaluate_parameter(180.0, None, 200.0, "< 200") == "Within Range"
    assert evaluate_parameter(200.0, None, 200.0, "< 200") == "Above Range"
    assert evaluate_parameter(240.0, None, 200.0, "< 200") == "Above Range"

    # Upper bound with '<=' (inclusive)
    assert evaluate_parameter(150.0, None, 150.0, "<= 150") == "Within Range"
    assert evaluate_parameter(150.1, None, 150.0, "<= 150") == "Above Range"

    # Lower bound with '>' (strict)
    assert evaluate_parameter(55.0, 40.0, None, "> 40") == "Within Range"
    assert evaluate_parameter(40.0, 40.0, None, "> 40") == "Below Range"
    assert evaluate_parameter(32.0, 40.0, None, "> 40") == "Below Range"

    # Lower bound with '>=' (inclusive)
    assert evaluate_parameter(20.0, 20.0, None, ">= 20") == "Within Range"
    assert evaluate_parameter(19.9, 20.0, None, ">= 20") == "Below Range"
    print("  [PASS] One-sided range evaluation (<, <=, >, >=) verified.")


def test_missing_and_unparseable_evaluation():
    """Tests that missing ranges or values deterministically yield 'Not Evaluated'."""
    # Missing value
    assert evaluate_parameter(None, 12.0, 15.5, "12.0 - 15.5") == "Not Evaluated"
    # Missing both bounds
    assert evaluate_parameter(14.2, None, None, None) == "Not Evaluated"
    # Empty reference raw
    assert evaluate_parameter(14.2, None, None, "") == "Not Evaluated"
    print("  [PASS] Missing and unparseable data yields 'Not Evaluated' verified.")


def test_end_to_end_parameter_evaluation():
    """Tests full document text parsing with deterministic Sprint 5 evaluations."""
    text = (
        "Hemoglobin: 11.5 g/dL (12.0 - 15.5)\n"       # Below Range
        "White Blood Cells: 6.8 x10^3/uL (4.5 - 11.0)\n" # Within Range
        "Platelet Count: 500 x10^3/uL (150 - 450)\n"   # Above Range
        "Total Cholesterol: 185 mg/dL (< 200)\n"       # Within Range (< 200)
        "Triglycerides: 220 mg/dL (< 150)\n"          # Above Range (< 150)
        "HDL Cholesterol: 35 mg/dL (> 40)\n"          # Below Range (> 40)
        "Serum Ferritin: 18.0 ng/mL (>= 20.0)\n"       # Below Range (>= 20.0)
        "Fasting Glucose: 95 mg/dL\n"                 # Not Evaluated (no range stated)
    )
    params = extract_parameters(text)
    assert len(params) == 8, f"Expected 8 parameters, got {len(params)}"

    param_map = {p.name: p for p in params}

    # Hemoglobin: 11.5 in [12.0, 15.5] -> Below Range
    assert param_map["Hemoglobin"].evaluation == "Below Range"

    # White Blood Cells: 6.8 in [4.5, 11.0] -> Within Range
    assert param_map["White Blood Cells"].evaluation == "Within Range"

    # Platelet Count: 500 in [150, 450] -> Above Range
    assert param_map["Platelet Count"].evaluation == "Above Range"

    # Total Cholesterol: 185 with (< 200) -> Within Range
    assert param_map["Total Cholesterol"].evaluation == "Within Range"

    # Triglycerides: 220 with (< 150) -> Above Range
    assert param_map["Triglycerides"].evaluation == "Above Range"

    # HDL Cholesterol: 35 with (> 40) -> Below Range
    assert param_map["HDL Cholesterol"].evaluation == "Below Range"

    # Ferritin: 18.0 with (>= 20.0) -> Below Range
    assert param_map["Ferritin"].evaluation == "Below Range"

    # Fasting Glucose: no reference range -> Not Evaluated
    assert param_map["Fasting Glucose"].evaluation == "Not Evaluated"
    print("  [PASS] End-to-end report parameter evaluation verified.")


def test_api_extraction_endpoint_with_evaluations():
    """Tests that the API returns the evaluated parameters."""
    scratch_dir = backend_dir / "scratch_test_files"
    digital_pdf = scratch_dir / "sample_digital_report.pdf"

    with open(digital_pdf, "rb") as f:
        resp = client.post("/api/reports/upload", files={"file": ("report.pdf", f, "application/pdf")})
    assert resp.status_code == 201
    report_id = resp.json()["reportId"]
    headers = {"X-Report-Token": resp.json()["accessToken"]}

    extract_resp = client.post(f"/api/reports/{report_id}/extract", headers=headers)
    assert extract_resp.status_code == 200
    data = extract_resp.json()

    assert "parameters" in data
    params = data["parameters"]
    assert len(params) >= 4

    for p in params:
        assert "evaluation" in p
        assert p["evaluation"] in ["Within Range", "Below Range", "Above Range", "Not Evaluated"]

    param_map = {p["name"]: p for p in params}
    # In sample_digital_report.pdf:
    # Hemoglobin: 14.2 (12.0 - 15.5) -> Within Range
    # WBC: 6.8 (4.5 - 11.0) -> Within Range
    # Platelets: 250 (150 - 450) -> Within Range
    # Fasting Glucose: 92 (70 - 99) -> Within Range
    assert param_map["Hemoglobin"]["evaluation"] == "Within Range"
    assert param_map["White Blood Cells"]["evaluation"] == "Within Range"
    assert param_map["Platelet Count"]["evaluation"] == "Within Range"
    assert param_map["Fasting Glucose"]["evaluation"] == "Within Range"
    print("  [PASS] API extraction endpoint with Sprint 5 evaluations verified.")


def run_all_tests():
    print("=" * 60)
    print("RUNNING SPRINT 5 REFERENCE RANGE EVALUATION TESTS")
    print("=" * 60)

    test_two_sided_range_evaluation()
    test_one_sided_range_evaluation()
    test_missing_and_unparseable_evaluation()
    test_end_to_end_parameter_evaluation()
    test_api_extraction_endpoint_with_evaluations()

    print("\n" + "=" * 60)
    print("ALL SPRINT 5 TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
