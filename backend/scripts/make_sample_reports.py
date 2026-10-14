"""
Generates two FICTIONAL lab reports for demos and tests (no real patient data):
  ../public/sample_lab_report.pdf           current report (several results outside range)
  ../public/sample_lab_report_previous.pdf  earlier report from the same fictional person

Usage:  python scripts/make_sample_reports.py
"""
from pathlib import Path

import pymupdf

PUBLIC = Path(__file__).resolve().parents[2] / "public"

HEADER = [
    "CITY DEMO DIAGNOSTICS - SAMPLE REPORT (FICTIONAL DATA)",
    "Patient: Demo Patient | Age: 45 | Sex: Female",
    "Report Date: {date}",
    "",
    "Test Name                Result    Reference Range   Unit",
]

CURRENT = [
    ("Hemoglobin", "11.2", "12.0 - 15.5", "g/dL"),
    ("Hematocrit", "34.1", "36 - 46", "%"),
    ("RBC Count", "3.9", "4.0 - 5.2", "x10^6/uL"),
    ("MCV", "76", "80 - 100", "fL"),
    ("White Blood Cells", "7.1", "4.5 - 11.0", "x10^3/uL"),
    ("Platelet Count", "265", "150 - 450", "x10^3/uL"),
    ("Fasting Glucose", "112", "70 - 99", "mg/dL"),
    ("HbA1c", "6.1", "4.0 - 5.6", "%"),
    ("Total Cholesterol", "228", "< 200", "mg/dL"),
    ("LDL Cholesterol", "152", "< 100", "mg/dL"),
    ("HDL Cholesterol", "38", "> 40", "mg/dL"),
    ("Triglycerides", "182", "< 150", "mg/dL"),
    ("Serum Creatinine", "0.9", "0.6 - 1.1", "mg/dL"),
    ("TSH", "2.1", "0.4 - 4.0", "uIU/mL"),
    ("Ferritin", "9", "13 - 150", "ng/mL"),
    ("Vitamin D", "18", "30 - 100", "ng/mL"),
]

PREVIOUS = [
    ("Hemoglobin", "12.4", "12.0 - 15.5", "g/dL"),
    ("Hematocrit", "37.0", "36 - 46", "%"),
    ("MCV", "81", "80 - 100", "fL"),
    ("White Blood Cells", "6.4", "4.5 - 11.0", "x10^3/uL"),
    ("Fasting Glucose", "104", "70 - 99", "mg/dL"),
    ("HbA1c", "5.8", "4.0 - 5.6", "%"),
    ("Total Cholesterol", "241", "< 200", "mg/dL"),
    ("LDL Cholesterol", "160", "< 100", "mg/dL"),
    ("HDL Cholesterol", "41", "> 40", "mg/dL"),
    ("Triglycerides", "199", "< 150", "mg/dL"),
    ("Serum Creatinine", "0.8", "0.6 - 1.1", "mg/dL"),
    ("Vitamin D", "52", "75 - 250", "nmol/L"),
]


def build(path: Path, date: str, rows) -> None:
    lines = [h.format(date=date) for h in HEADER]
    lines += [f"{name:<25}{value:<10}{ref:<18}{unit}" for name, value, ref, unit in rows]
    lines += ["", "This is a computer-generated FICTIONAL report for demonstration only."]
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(pymupdf.Rect(40, 40, 570, 800), "\n".join(lines), fontsize=10, fontname="cour")
    doc.save(str(path))
    doc.close()


def build_all(target_dir: Path = PUBLIC) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    build(target_dir / "sample_lab_report.pdf", "08/10/2026", CURRENT)
    build(target_dir / "sample_lab_report_previous.pdf", "02/04/2026", PREVIOUS)


if __name__ == "__main__":
    build_all()
    print(f"Wrote sample reports to {PUBLIC}")
