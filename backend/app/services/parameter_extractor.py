import re
import logging
from typing import List, Optional, Tuple, Dict, Any
from app.models.report import ExtractedParameter

logger = logging.getLogger(__name__)

# Curated catalog of canonical laboratory test definitions and aliases.
# Ordered by priority / specificity (longer/more specific names first).
LAB_TEST_CATALOG = [
    # Complete Blood Count (CBC)
    {
        "canonical": "Hemoglobin",
        "patterns": [
            r"\bhemoglobin\b", r"\bhgb\b", r"\bhb\b", r"\bhaemoglobin\b"
        ],
        "default_unit": "g/dL"
    },
    {
        "canonical": "White Blood Cells",
        "patterns": [
            r"\bwhite blood cells?\b", r"\bwhite blood cell count\b", r"\bwbc count\b",
            r"\bwbc\b", r"\btotal leukocyte count\b", r"\btotal leucocyte count\b",
            r"\bleukocytes?\b", r"\btlc\b"
        ],
        "default_unit": "x10^3/uL"
    },
    {
        "canonical": "Red Blood Cells",
        "patterns": [
            r"\bred blood cells?\b", r"\bred blood cell count\b", r"\brbc count\b",
            r"\brbc\b", r"\berythrocytes?\b"
        ],
        "default_unit": "x10^6/uL"
    },
    {
        "canonical": "Platelet Count",
        "patterns": [
            r"\bplatelet count\b", r"\bplatelets?\b", r"\bplt\b", r"\bthrombocytes?\b"
        ],
        "default_unit": "x10^3/uL"
    },
    {
        "canonical": "Hematocrit",
        "patterns": [
            r"\bhematocrit\b", r"\bhaematocrit\b", r"\bhct\b", r"\bpcv\b",
            r"\bpacked cell volume\b"
        ],
        "default_unit": "%"
    },
    {
        "canonical": "Mean Corpuscular Volume",
        "patterns": [r"\bmean corpuscular volume\b", r"\bmcv\b"],
        "default_unit": "fL"
    },
    {
        "canonical": "Mean Corpuscular Hemoglobin",
        "patterns": [r"\bmean corpuscular hemoglobin\b", r"\bmean corpuscular haemoglobin\b", r"\bmch\b"],
        "default_unit": "pg"
    },
    {
        "canonical": "MCHC",
        "patterns": [
            r"\bmean corpuscular hemoglobin concentration\b",
            r"\bmean corpuscular haemoglobin concentration\b",
            r"\bmchc\b"
        ],
        "default_unit": "g/dL"
    },
    {
        "canonical": "Red Cell Distribution Width",
        "patterns": [r"\bred cell distribution width\b", r"\brdw-cv\b", r"\brdw-sd\b", r"\brdw\b"],
        "default_unit": "%"
    },
    {
        "canonical": "Neutrophils",
        "patterns": [r"\bneutrophils?\b", r"\bneutrophil count\b", r"\bpolymorphs?\b", r"\banc\b"],
        "default_unit": "%"
    },
    {
        "canonical": "Lymphocytes",
        "patterns": [r"\blymphocytes?\b", r"\blymphocyte count\b", r"\balc\b"],
        "default_unit": "%"
    },
    {
        "canonical": "Monocytes",
        "patterns": [r"\bmonocytes?\b", r"\bmonocyte count\b"],
        "default_unit": "%"
    },
    {
        "canonical": "Eosinophils",
        "patterns": [r"\beosinophils?\b", r"\beosinophil count\b"],
        "default_unit": "%"
    },
    {
        "canonical": "Basophils",
        "patterns": [r"\bbasophils?\b", r"\bbasophil count\b"],
        "default_unit": "%"
    },
    # Metabolic & Renal
    {
        "canonical": "Fasting Glucose",
        "patterns": [
            r"\bfasting blood sugar\b", r"\bfasting blood glucose\b", r"\bfasting glucose\b",
            r"\bblood glucose\b", r"\bblood sugar\b", r"\bglucose fasting\b",
            r"\bglucose\b", r"\bfbs\b", r"\brbs\b"
        ],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "Blood Urea Nitrogen",
        "patterns": [r"\bblood urea nitrogen\b", r"\burea nitrogen\b", r"\bbun\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "Serum Urea",
        "patterns": [r"\bserum urea\b", r"\burea\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "Serum Creatinine",
        "patterns": [r"\bserum creatinine\b", r"\bcreatinine\b", r"\bcreat\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "eGFR",
        "patterns": [r"\bestimated gfr\b", r"\begfr\b", r"\bgfr\b"],
        "default_unit": "mL/min/1.73m2"
    },
    {
        "canonical": "Sodium",
        "patterns": [r"\bserum sodium\b", r"\bsodium\b", r"\bna\+?\b"],
        "default_unit": "mmol/L"
    },
    {
        "canonical": "Potassium",
        "patterns": [r"\bserum potassium\b", r"\bpotassium\b", r"\bk\+?\b"],
        "default_unit": "mmol/L"
    },
    {
        "canonical": "Chloride",
        "patterns": [r"\bserum chloride\b", r"\bchloride\b", r"\bcl-?\b"],
        "default_unit": "mmol/L"
    },
    {
        "canonical": "Calcium",
        "patterns": [r"\bserum calcium\b", r"\btotal calcium\b", r"\bcalcium\b", r"\bca\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "Bicarbonate",
        "patterns": [r"\bbicarbonate\b", r"\bcarbon dioxide\b", r"\bco2\b", r"\bhco3\b"],
        "default_unit": "mmol/L"
    },
    # Liver Function (LFT)
    {
        "canonical": "Total Bilirubin",
        "patterns": [r"\btotal bilirubin\b", r"\bbilirubin total\b", r"\bbilirubin\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "Direct Bilirubin",
        "patterns": [r"\bdirect bilirubin\b", r"\bconjugated bilirubin\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "Indirect Bilirubin",
        "patterns": [r"\bindirect bilirubin\b", r"\bunconjugated bilirubin\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "ALT (SGPT)",
        "patterns": [
            r"\balanine aminotransferase\b", r"\balt \(sgpt\)\b", r"\bsgpt\b", r"\balt\b"
        ],
        "default_unit": "U/L"
    },
    {
        "canonical": "AST (SGOT)",
        "patterns": [
            r"\baspartate aminotransferase\b", r"\bast \(sgot\)\b", r"\bsgot\b", r"\bast\b"
        ],
        "default_unit": "U/L"
    },
    {
        "canonical": "Alkaline Phosphatase",
        "patterns": [r"\balkaline phosphatase\b", r"\balk phos\b", r"\balp\b"],
        "default_unit": "U/L"
    },
    {
        "canonical": "Total Protein",
        "patterns": [r"\bserum total protein\b", r"\btotal protein\b", r"\bprotein total\b"],
        "default_unit": "g/dL"
    },
    {
        "canonical": "Albumin",
        "patterns": [r"\bserum albumin\b", r"\balbumin\b", r"\balb\b"],
        "default_unit": "g/dL"
    },
    {
        "canonical": "Globulin",
        "patterns": [r"\bserum globulin\b", r"\bglobulin\b"],
        "default_unit": "g/dL"
    },
    {
        "canonical": "A/G Ratio",
        "patterns": [r"\balbumin/globulin ratio\b", r"\ba/g ratio\b", r"\bag ratio\b"],
        "default_unit": "ratio"
    },
    # Lipid Panel
    {
        "canonical": "Total Cholesterol",
        "patterns": [r"\btotal cholesterol\b", r"\bserum cholesterol\b", r"\bcholesterol\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "Triglycerides",
        "patterns": [r"\btriglycerides?\b", r"\btg\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "HDL Cholesterol",
        "patterns": [r"\bhdl cholesterol\b", r"\bhdl-c\b", r"\bhdl\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "LDL Cholesterol",
        "patterns": [r"\bldl cholesterol\b", r"\bldl-c\b", r"\bldl\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "VLDL Cholesterol",
        "patterns": [r"\bvldl cholesterol\b", r"\bvldl-c\b", r"\bvldl\b"],
        "default_unit": "mg/dL"
    },
    # Glycemic & Others
    {
        "canonical": "HbA1c",
        "patterns": [r"\bglycated hemoglobin\b", r"\bglycohemoglobin\b", r"\bhba1c\b", r"\ba1c\b"],
        "default_unit": "%"
    },
    {
        "canonical": "Uric Acid",
        "patterns": [r"\bserum uric acid\b", r"\buric acid\b"],
        "default_unit": "mg/dL"
    },
    {
        "canonical": "ESR",
        "patterns": [r"\berythrocyte sedimentation rate\b", r"\besr\b"],
        "default_unit": "mm/hr"
    },
    {
        "canonical": "CRP",
        "patterns": [r"\bc-reactive protein\b", r"\bhs-crp\b", r"\bcrp\b"],
        "default_unit": "mg/L"
    },
    {
        "canonical": "TSH",
        "patterns": [r"\bthyroid stimulating hormone\b", r"\btsh\b"],
        "default_unit": "uIU/mL"
    },
    {
        "canonical": "Free T3",
        "patterns": [r"\bfree triiodothyronine\b", r"\bfree t3\b", r"\bft3\b"],
        "default_unit": "pg/mL"
    },
    {
        "canonical": "Free T4",
        "patterns": [r"\bfree thyroxine\b", r"\bfree t4\b", r"\bft4\b"],
        "default_unit": "ng/dL"
    },
    {
        "canonical": "Vitamin D",
        "patterns": [r"\b25-oh vitamin d\b", r"\b25-hydroxyvitamin d\b", r"\bvitamin d3?\b", r"\bvit d\b"],
        "default_unit": "ng/mL"
    },
    {
        "canonical": "Vitamin B12",
        "patterns": [r"\bvitamin b-?12\b", r"\bcobalamin\b", r"\bvit b12\b"],
        "default_unit": "pg/mL"
    },
    {
        "canonical": "Ferritin",
        "patterns": [r"\bserum ferritin\b", r"\bferritin\b"],
        "default_unit": "ng/mL"
    },
    {
        "canonical": "Serum Iron",
        "patterns": [r"\bserum iron\b", r"\biron\b", r"\bfe\b"],
        "default_unit": "micro g/dL"
    },
    {
        "canonical": "pH",
        "patterns": [r"\burine ph\b", r"\bph\b"],
        "default_unit": ""
    }
]

# Common unit regex patterns (with tolerance for OCR whitespace around slashes)
UNIT_PATTERN = (
    r"(?:x\s*10\^?[0-9]+\s*/\s*[a-zA-Zµu]+|10\^[0-9]+\s*/\s*[a-zA-Zµu]+|10\*[0-9]+\s*/\s*[a-zA-Zµu]+|"
    r"[xX]\s*10\^?[0-9]+\s*/\s*uL|[xX]\s*10\^?[0-9]+\s*/\s*µL|k\s*/\s*cumm|k\s*/\s*uL|cells\s*/\s*[a-zA-Zµu]+|cells\s*/\s*mm3|/\s*mm3|/\s*µL|/\s*uL|"
    r"micro\s*g\s*/\s*dL|micro\s*g\s*/\s*mL|micro\s*g\s*/\s*L|microIU\s*/\s*mL|micromol\s*/\s*L|million\s*/\s*cmm|"
    r"g\s*/\s*dL|g\s*/\s*L|mg\s*/\s*dL|mg\s*/\s*L|mg\s*/\s*mL|ug\s*/\s*dL|ug\s*/\s*mL|ug\s*/\s*L|mcg\s*/\s*dL|mcg\s*/\s*mL|mcg\s*/\s*L|"
    r"ng\s*/\s*mL|ng\s*/\s*dL|ng\s*/\s*L|pg\s*/\s*mL|pg\s*/\s*dL|pmol\s*/\s*L|nmol\s*/\s*L|mmol\s*/\s*L|umol\s*/\s*L|µmol\s*/\s*L|mEq\s*/\s*L|"
    r"uIU\s*/\s*mL|µIU\s*/\s*mL|mIU\s*/\s*mL|mIU\s*/\s*L|IU\s*/\s*mL|IU\s*/\s*L|U\s*/\s*L|mm\s*/\s*hr|fL|pg|%|mL\s*/\s*min\s*/\s*1\.73m2)"
)

# Reference range patterns (support two-sided, one-sided, parenthetical/bracketed, and explicit labels)
RANGE_TWO_SIDED = re.compile(
    r"(?:(?:ref(?:erence)?|bio(?:logical)?\.?\s*ref(?:\.?\s*interval)?)\s*(?:range|interval)?[:\s]*)?"
    r"(?:[\(\[])?\s*(\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*(\d+(?:\.\d+)?)\s*(?:[\)\]])?(?:\s*" + UNIT_PATTERN + r")?",
    re.IGNORECASE
)

RANGE_ONE_SIDED_LESS = re.compile(
    r"(?:(?:ref(?:erence)?|bio(?:logical)?\.?\s*ref(?:\.?\s*interval)?)\s*(?:range|interval)?[:\s]*)?"
    r"(?:[\(\[])?\s*(?:<|<=|less\s+than|up\s+to|under|below)\s*(\d+(?:\.\d+)?)\s*(?:[\)\]])?(?:\s*" + UNIT_PATTERN + r")?",
    re.IGNORECASE
)

RANGE_ONE_SIDED_GREATER = re.compile(
    r"(?:(?:ref(?:erence)?|bio(?:logical)?\.?\s*ref(?:\.?\s*interval)?)\s*(?:range|interval)?[:\s]*)?"
    r"(?:[\(\[])?\s*(?:>|>=|greater\s+than|more\s+than|above)\s*(\d+(?:\.\d+)?)\s*(?:[\)\]])?(?:\s*" + UNIT_PATTERN + r")?",
    re.IGNORECASE
)

# Reference-range category labels and subpopulation boundaries that must NEVER be emitted as test parameters
DISALLOWED_CATEGORY_LABELS = {
    "desirable", "borderline", "borderline high", "borderline low",
    "high", "very high", "extremely high",
    "low", "very low", "extremely low",
    "optimal", "near optimal", "above optimal", "near to above optimal",
    "normal", "abnormal", "critical", "alert",
    "deficiency", "deficient", "insufficiency", "insufficient",
    "sufficiency", "sufficient", "toxicity", "toxic",
    "poor control", "good control", "fair control", "adequate control",
    "diabetes", "pre-diabetes", "prediabetes", "non-diabetes",
    "reactive", "non reactive", "non-reactive", "weakly reactive",
    "positive", "negative", "indeterminate", "equivocal",
    "adult", "adults", "children", "child", "pediatric", "infant", "infants",
    "male", "males", "female", "females", "men", "women",
    "for screening", "screening", "for diagnosis", "diagnosis",
    "for diabetic patient", "diabetic patient",
    "clear", "clearity", "clarity", "colour", "color", "pale yellow", "yellow",
    "straw", "amber", "absent", "present", "total area", "total area:",
    "f concentration =", "f concentration", "a2 concentration =", "a2 concentration",
    "time (min.)", "time (min)", "retention", "peak", "p2 peak", "p3 peak"
}

# Metadata, headers, and document structural tokens that must NEVER be emitted as lab parameters
DISALLOWED_METADATA_WORDS = {
    "test", "tests", "parameter", "parameters", "investigation", "investigations",
    "result", "results", "unit", "units", "reference", "ref", "interval",
    "biological", "method", "flag", "flags", "status", "page", "date", "time",
    "patient", "name", "dr", "doctor", "hospital", "clinic", "laboratory",
    "address", "phone", "email", "age", "sex", "gender", "specimen", "sample",
    "collected", "reported", "registered", "verified", "signature", "authorized",
    "registration", "collection", "approval", "approved", "printed",
    "interpretation", "notes", "note", "comment", "comments", "disclaimer",
    "explanation", "conclusion", "summary", "end of report", "client", "location",
    "passport", "barcode", "qr", "uhid", "mrn", "ipd", "opd", "bill", "receipt",
    "accession", "id", "no", "num", "number", "on", "at", "by", "for", "with", "type",
    "differential count", "absolute count", "examination", "profile", "panel",
    "area", "retention", "peak"
}

DATE_OR_TIME_PATTERN = re.compile(
    r"(?:^\s*\d{1,4}[-/\.](?:[A-Za-z]{3,}|\d{1,2})[-/\.]\d{1,4}"
    r"|^\s*\d{1,2}:\d{2}(?::\d{2})?"
    r"|^\s*[A-Za-z]{3,}\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE
)

SECTION_PANEL_HEADERS = {
    "complete blood count", "differential count", "absolute count",
    "lipid profile", "thyroid profile", "thyroid function test",
    "renal function test", "liver function test", "biochemistry",
    "hematology", "serology", "immunology", "peripheral smear examination",
    "physical & chemical (dip strip) examination", "dip strip examination",
    "examination", "iron studies", "electrolytes", "electrolyte panel",
    "serum electrolytes", "total wbc and differential count",
    "sample information", "patient information", "client/location information",
    "client information", "explanation:-", "explanation", "interpretation:",
    "interpretation", "limitations:", "limitations", "bio-rad cdm system",
    "patient report", "patient data", "v2_bthal"
}


def _is_valid_parameter_name(candidate: str) -> bool:
    """
    Validates whether a candidate text segment represents a plausible laboratory parameter name.
    Ensures unfamiliar valid parameters are extractable without hardcoded whitelist restriction,
    while strictly rejecting reference-range category labels, metadata, dates, patient info,
    narrative fragments, and document boilerplate.
    """
    if not candidate:
        return False
    cand = candidate.strip()
    if len(cand) < 2 or len(cand) > 60:
        return False
    # Must contain at least 2 alphabetic characters
    if len(re.findall(r"[A-Za-z]", cand)) < 2:
        return False
    # Must start with letter
    if not cand[0].isalpha():
        return False

    cand_lower = cand.lower().strip()

    # Reject reference-range category labels and qualitative descriptors
    if cand_lower in DISALLOWED_CATEGORY_LABELS:
        return False

    # Clean candidate by stripping trailing punctuation, ranges, digits (e.g. 'Pre-Diabetes: 5.7% -' -> 'pre-diabetes')
    cand_base = re.sub(r"[:=0-9%<>\-–—\.\s]+$", "", cand_lower).strip()
    if cand_base in DISALLOWED_CATEGORY_LABELS:
        return False

    # Reject narrative phrase starters (e.g. 'A ratio of albumin')
    if any(cand_lower.startswith(p) for p in [
        "a ", "an ", "the ", "of ", "in ", "on ", "at ", "to ", "for ", "by ", "with ", "without ", "due to ", "when "
    ]):
        return False

    # Reject unbalanced closing parenthesis (e.g. 'antiepileptics), vegetarians without')
    if ")" in cand and "(" not in cand:
        return False

    # Reject narrative sentence and commentary words
    if any(nw in cand_lower for nw in [
        "without", "vegetarians", "indicative", "defined", "higher", "lower",
        "patients", "medications", "recommended", "interfere", "associated",
        "unexplained", "neuropathy", "coronary", "malabsorption"
    ]):
        return False

    # Reject metadata prefixes (dates, registration, samples, barcodes, etc.)
    metadata_prefixes = (
        "registration", "registered", "collected", "collection", "approved",
        "approval", "printed", "reported", "reporting", "received", "patient",
        "doctor", "dr.", "dr ", "sample", "specimen", "lab id", "passport",
        "status", "page", "client", "location", "process at", "sample type",
        "ref. id", "ref. by", "ref id", "ref by", "bill", "invoice", "barcode",
        "for screening", "for diabetic", "explanation", "interpretation",
        "disclaimer", "comments", "comment", "notes", "note", "method",
        "clear", "pale yellow", "total area", "retention", "time (min"
    )
    if any(cand_lower.startswith(p) for p in metadata_prefixes):
        return False

    # Check words against disallowed sets
    words = set(re.findall(r"[a-z]+", cand_lower))
    if words and words.issubset(DISALLOWED_METADATA_WORDS | DISALLOWED_CATEGORY_LABELS):
        return False

    # Reject short random token fragments (e.g. 'a d', 'pu a', 'ea s', 'a e', 'So')
    tokens = [t for t in re.findall(r"[a-z]+", cand_lower)]
    if len(tokens) >= 2 and all(len(t) <= 2 for t in tokens):
        return False

    return True


def _parse_reference_range(text_segment: str) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """
    Extracts (referenceLow, referenceHigh, referenceRaw) from a text segment.
    Returns (None, None, None) if no valid reference range is found.
    """
    if not text_segment:
        return None, None, None

    clean_segment = text_segment.strip()

    # 1. Check two-sided range: e.g. 12.0 - 15.5 or 4000 - 11000
    m_two = RANGE_TWO_SIDED.search(clean_segment)
    if m_two:
        try:
            low = float(m_two.group(1))
            high = float(m_two.group(2))
            raw = m_two.group(0).strip()
            return low, high, raw
        except ValueError:
            pass

    # 2. Check upper bound only: e.g. < 150
    m_less = RANGE_ONE_SIDED_LESS.search(clean_segment)
    if m_less:
        try:
            high = float(m_less.group(1))
            raw = m_less.group(0).strip()
            return None, high, raw
        except ValueError:
            pass

    # 3. Check lower bound only: e.g. > 40
    m_greater = RANGE_ONE_SIDED_GREATER.search(clean_segment)
    if m_greater:
        try:
            low = float(m_greater.group(1))
            raw = m_greater.group(0).strip()
            return low, None, raw
        except ValueError:
            pass

    return None, None, None


def evaluate_parameter(
    value: Optional[float],
    ref_low: Optional[float],
    ref_high: Optional[float],
    ref_raw: Optional[str] = None,
    param_name: Optional[str] = None
) -> str:
    """
    Deterministically evaluates an extracted numeric value against the stated reference range
    from the same report.

    Evaluation outcomes:
    - 'Within Range': value is between stated bounds, or satisfies one-sided threshold
    - 'Below Range': value is strictly below stated lower bound
    - 'Above Range': value is strictly above stated upper bound
    - 'Not Evaluated': value or reference bounds are missing/unparseable

    Strict Rule: Never infers medical thresholds or invents missing ranges.
    """
    if value is None:
        return "Not Evaluated"

    raw = (ref_raw or "").strip().lower()

    # 1. Two-sided reference range: [ref_low, ref_high]
    if ref_low is not None and ref_high is not None:
        if value < ref_low:
            return "Below Range"
        elif value > ref_high:
            return "Above Range"
        else:
            return "Within Range"

    # 2. Upper-bound only (e.g. < 200, <= 150, less than 100, up to 50)
    if ref_high is not None and ref_low is None:
        if any(w in raw for w in ["deficiency", "deficient", "insufficiency"]):
            return "Below Range" if value < ref_high else "Within Range"
        if "<=" in raw or "up to" in raw:
            return "Within Range" if value <= ref_high else "Above Range"
        else:
            return "Within Range" if value < ref_high else "Above Range"

    # 3. Lower-bound only (e.g. > 40, >= 50, greater than 30, more than 20)
    if ref_low is not None and ref_high is None:
        # Check if lower bound represents an adverse disease/elevation cutoff
        # e.g., HbA1c Diabetes: >6.5%, Poor Control: >7.0%, High: >240, Toxicity: >50
        is_adverse_threshold = any(w in raw for w in [
            "diabetes", "diabetic", "poor control", "high", "very high",
            "abnormal", "critical", "alert", "toxicity", "toxic", "elevated"
        ])
        if param_name and any(h in param_name.lower() for h in ["hba1c", "glycated", "glycosylated"]):
            if ref_low >= 6.0:
                is_adverse_threshold = True
        elif "%" in raw and ref_low == 6.5:
            is_adverse_threshold = True

        if is_adverse_threshold:
            return "Above Range" if value >= ref_low else "Within Range"

        if ">=" in raw:
            return "Within Range" if value >= ref_low else "Below Range"
        else:
            return "Within Range" if value > ref_low else "Below Range"

    # 4. Neither bound is present
    return "Not Evaluated"


def _clean_numeric_value(val_str: str) -> Optional[float]:
    """Cleans and converts a string to float, handling commas in numbers like 7,200."""
    if not val_str:
        return None
    cleaned = val_str.replace(',', '').strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _match_catalog_test(line: str) -> Optional[Dict[str, Any]]:
    """
    Searches for known medical tests in a line.
    Finds all matches and returns the most specific (longest matched pattern) test.
    """
    line_lower = line.lower()
    best_match = None
    max_len = 0

    for item in LAB_TEST_CATALOG:
        for pat in item["patterns"]:
            m = re.search(pat, line_lower)
            if m:
                match_len = m.end() - m.start()
                if match_len > max_len:
                    max_len = match_len
                    best_match = {
                        "canonical": item["canonical"],
                        "match_start": m.start(),
                        "match_end": m.end(),
                        "default_unit": item["default_unit"],
                        "matched_text": line[m.start():m.end()]
                    }
    return best_match


def _parse_pipe_line(line: str) -> Optional[ExtractedParameter]:
    """
    Parses pipe-separated format:
    e.g. WBC | 7200 | /µL | 4000 - 11000
         Hemoglobin | 14.2 | g/dL | 12.0 - 15.5
         Serum Zinc | 85.0 | ug/dL | 60.0 - 120.0
    """
    parts = [p.strip() for p in line.split('|')]
    if len(parts) < 2:
        return None

    # Check first column: prioritize catalog match, fallback to valid candidate name
    test_info = _match_catalog_test(parts[0])
    name: Optional[str] = None
    default_unit: Optional[str] = None

    if test_info:
        name = test_info["canonical"]
        default_unit = test_info["default_unit"]
    elif _is_valid_parameter_name(parts[0]):
        name = parts[0].strip()
    else:
        return None

    value = None
    unit = None
    ref_low = None
    ref_high = None
    ref_raw = None

    # Column 1 is usually value
    if len(parts) >= 2:
        val_match = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", parts[1])
        if val_match:
            value = _clean_numeric_value(val_match.group(0))

    # Column 2 might be unit or reference range
    if len(parts) == 3:
        low, high, raw = _parse_reference_range(parts[2])
        if raw:
            ref_low, ref_high, ref_raw = low, high, raw
        else:
            unit_match = re.search(UNIT_PATTERN, parts[2], re.IGNORECASE)
            if unit_match:
                unit = unit_match.group(0)
    elif len(parts) >= 4:
        unit_match = re.search(UNIT_PATTERN, parts[2], re.IGNORECASE)
        if unit_match:
            unit = unit_match.group(0)
        else:
            low_check, high_check, raw_check = _parse_reference_range(parts[2])
            if raw_check:
                ref_low, ref_high, ref_raw = low_check, high_check, raw_check
            else:
                unit = parts[2]

        low, high, raw = _parse_reference_range(parts[3])
        if raw:
            ref_low, ref_high, ref_raw = low, high, raw
        elif not ref_raw:
            low_alt, high_alt, raw_alt = _parse_reference_range(parts[2])
            if raw_alt:
                ref_low, ref_high, ref_raw = low_alt, high_alt, raw_alt

    evaluation = evaluate_parameter(value, ref_low, ref_high, ref_raw)

    return ExtractedParameter(
        name=name,
        value=value,
        unit=unit or default_unit,
        referenceLow=ref_low,
        referenceHigh=ref_high,
        referenceRaw=ref_raw,
        rawLine=line,
        evaluation=evaluation
    )


def _parse_columnar_line(line: str) -> Optional[ExtractedParameter]:
    """
    Parses whitespace columnar lines:
    e.g. Hemoglobin             14.2      12.0 - 15.5 g/dL
         White Blood Cells      6.8       4.5 - 11.0  x10^3/uL
         Troponin I             0.02      < 0.04      ng/mL
    """
    # Disallow long prose commentary or narrative sentences
    if len(line.split()) > 15:
        return None

    test_info = _match_catalog_test(line)
    name: Optional[str] = None
    default_unit: Optional[str] = None
    after_test = ""

    if test_info:
        # Match must start at or near the beginning of the line (not embedded in sentence)
        if test_info["match_start"] > 3:
            return None
        name = test_info["canonical"]
        default_unit = test_info["default_unit"]
        after_test = line[test_info["match_end"]:].strip()
    else:
        cols = [c.strip() for c in re.split(r"\s{2,}", line) if c.strip()]
        if len(cols) >= 2 and _is_valid_parameter_name(cols[0]):
            val_test = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", cols[1])
            if val_test:
                name = cols[0]
                idx = line.find(cols[1])
                if idx != -1:
                    after_test = line[idx:].strip()
        if not name or not after_test:
            return None

    # Do not treat dates or timestamps as lab values
    if DATE_OR_TIME_PATTERN.search(after_test):
        return None

    val_match = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", after_test)
    if not val_match:
        return None

    value = _clean_numeric_value(val_match.group(0))
    after_value = after_test[val_match.end():].strip()

    ref_low, ref_high, ref_raw = _parse_reference_range(after_value)

    unit = None
    unit_match = re.search(UNIT_PATTERN, after_value, re.IGNORECASE)
    if unit_match:
        unit = unit_match.group(0)
    elif ref_raw:
        idx = after_value.find(ref_raw)
        if idx > 0:
            prefix = after_value[:idx].strip()
            prefix = re.sub(r"^[\s:=,\-\]]+|[\s:=,\-\[]+$", "", prefix).strip()
            if 0 < len(prefix) <= 20 and not any(ch in prefix for ch in "()[]<>"):
                unit = prefix
        elif idx == 0:
            suffix = after_value[len(ref_raw):].strip()
            suffix = re.sub(r"^[\s:=,\-\]]+|[\s:=,\-\[]+$", "", suffix).strip()
            if 0 < len(suffix) <= 20 and not any(ch in suffix for ch in "()[]<>"):
                unit = suffix

    evaluation = evaluate_parameter(value, ref_low, ref_high, ref_raw)

    return ExtractedParameter(
        name=name,
        value=value,
        unit=unit or default_unit,
        referenceLow=ref_low,
        referenceHigh=ref_high,
        referenceRaw=ref_raw,
        rawLine=line,
        evaluation=evaluation
    )


def _parse_key_value_line(line: str) -> Optional[ExtractedParameter]:
    """
    Parses key-value formats:
    e.g. Hemoglobin: 13.8 g/dL
         WBC: 7.2 x10^3/uL
         Serum Ceruloplasmin: 28.5 mg/dL (20.0 - 60.0)
         Calcium: 9.4 mg/dL [8.5 - 10.5]
    """
    # Disallow long prose commentary or narrative sentences
    if len(line.split()) > 15:
        return None

    test_info = _match_catalog_test(line)
    name: Optional[str] = None
    default_unit: Optional[str] = None
    after_test = ""

    if test_info and test_info["match_start"] <= 3:
        name = test_info["canonical"]
        default_unit = test_info["default_unit"]
        after_test = line[test_info["match_end"]:].strip()
        after_test = re.sub(r"^[:|\-—]\s*", "", after_test).strip()
    else:
        kv_match = re.match(r"^([A-Za-z][A-Za-z0-9\s\-/'\(\),.]{1,50}?)\s*[:=]\s*(.*)$", line)
        if kv_match:
            candidate_name = kv_match.group(1).strip()
            if _is_valid_parameter_name(candidate_name):
                name = candidate_name
                after_test = kv_match.group(2).strip()
        if not name or not after_test:
            return None

    # Do not treat dates or timestamps as lab values
    if DATE_OR_TIME_PATTERN.search(after_test):
        return None

    # If after_test is ONLY a range comparison without an observed result (e.g. Desirable : <200)
    if re.match(r"^\s*(?:<|<=|>|>=|less\s+than|greater\s+than)\s*\d+(?:\.\d+)?\s*(?:[A-Za-z/%µ]+)?$", after_test, re.IGNORECASE):
        return None
    if re.match(r"^\s*\d+(?:\.\d+)?\s*(?:-|–|—|to)\s*\d+(?:\.\d+)?\s*(?:[A-Za-z/%µ]+)?$", after_test, re.IGNORECASE):
        return None

    val_match = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", after_test)
    if not val_match:
        return None

    value = _clean_numeric_value(val_match.group(0))
    after_val = after_test[val_match.end():].strip()

    ref_low, ref_high, ref_raw = _parse_reference_range(after_val)

    unit = None
    unit_match = re.search(UNIT_PATTERN, after_val, re.IGNORECASE)
    if unit_match:
        unit = unit_match.group(0)
    elif ref_raw:
        idx = after_val.find(ref_raw)
        if idx > 0:
            prefix = after_val[:idx].strip()
            prefix = re.sub(r"^[\s:=,\-\]]+|[\s:=,\-\[]+$", "", prefix).strip()
            if 0 < len(prefix) <= 20 and not any(ch in prefix for ch in "()[]<>"):
                unit = prefix
    elif after_val:
        cand = re.sub(r"^[\s:=,\-\]]+|[\s:=,\-\[]+$", "", after_val).strip()
        if 0 < len(cand) <= 20 and not any(ch in cand for ch in "()[]<>"):
            unit = cand

    evaluation = evaluate_parameter(value, ref_low, ref_high, ref_raw)

    return ExtractedParameter(
        name=name,
        value=value,
        unit=unit or default_unit,
        referenceLow=ref_low,
        referenceHigh=ref_high,
        referenceRaw=ref_raw,
        rawLine=line,
        evaluation=evaluation
    )


def _parse_multi_line_block(lines: List[str], i: int) -> Tuple[Optional[ExtractedParameter], int]:
    """
    Parses multi-line vertical layout blocks from PDF tables where columns are rendered
    across consecutive lines:
    e.g.
        Hemoglobin
        g/dL
        13.0 - 16.5
        Colorimetric
        14.5
    or
        Cholesterol
        mg/dL
        Desirable : <200
        Borderline High : 200-239
        High : >240
        Cholesterol oxidase ...
        189.0
    """
    line = lines[i].strip()
    if not line:
        return None, i

    test_info = _match_catalog_test(line)
    name: Optional[str] = None
    default_unit: Optional[str] = None

    if test_info and test_info["match_start"] <= 3:
        name = test_info["canonical"]
        default_unit = test_info["default_unit"]
    elif _is_valid_parameter_name(line):
        name = line
    else:
        return None, i

    line_lower = line.lower()
    if line_lower in SECTION_PANEL_HEADERS:
        return None, i

    # Verify line i is followed within 1-3 lines by a unit, flag, or reference range
    found_unit_or_range = False
    for k in range(i + 1, min(i + 4, len(lines))):
        sub_k = lines[k].strip()
        if re.search(UNIT_PATTERN, sub_k, re.IGNORECASE) or sub_k in [
            "million/cmm", "/cmm", "fL", "pg", "%", "g/dL", "mg/dL", "ng/mL",
            "microIU/mL", "IU/mL", "mm/1hr", "micro g/dL", "micromol/L", "S/Co",
            "U/L", "mmol/L", "ratio"
        ]:
            found_unit_or_range = True
            break
        if _parse_reference_range(sub_k)[2] is not None:
            found_unit_or_range = True
            break
        if any(cat in sub_k.lower() for cat in ["desirable", "normal", "optimal", "borderline", "sufficiency"]):
            found_unit_or_range = True
            break

    if not found_unit_or_range:
        return None, i

    unit = None
    ref_low = None
    ref_high = None
    ref_raw = None
    val = None
    val_idx = -1

    category_entries = []

    for j in range(i + 1, min(i + 15, len(lines))):
        sub = lines[j].strip()
        sub_lower = sub.lower()

        # Stop lookahead if section header or report footer is reached
        if any(h in sub_lower for h in [
            "patient information", "client information", "laboratory test report",
            "dr. ", "dr.", "explanation:-", "explanation", "interpretation:",
            "interpretation", "limitations:", "limitations", "end of report"
        ]):
            break

        # Stop if we hit a different test candidate that has its own unit
        if j > i + 1:
            next_test = _match_catalog_test(sub)
            if next_test and next_test["match_start"] <= 3:
                if j + 1 < len(lines) and (
                    re.search(UNIT_PATTERN, lines[j + 1]) or
                    lines[j + 1].strip() in ["H", "L", "%", "g/dL", "mg/dL"]
                ):
                    break

        # Unit detection
        u_match = re.search(UNIT_PATTERN, sub, re.IGNORECASE)
        if u_match and not unit:
            unit = u_match.group(0)
            continue
        elif sub in [
            "million/cmm", "/cmm", "fL", "pg", "%", "g/dL", "mg/dL", "ng/mL",
            "microIU/mL", "IU/mL", "mm/1hr", "micro g/dL", "micromol/L", "S/Co",
            "U/L", "mmol/L", "ratio"
        ] and not unit:
            unit = sub
            continue

        # Collect candidate reference range categories
        low_c, high_c, raw_c = _parse_reference_range(sub)
        if raw_c:
            category_entries.append((sub, low_c, high_c, raw_c))
            continue

        # Observed numeric value
        if re.match(r"^[-+]?\d+(?:,\d{3})*(?:\.\d+)?$", sub):
            val = float(sub.replace(',', ''))
            val_idx = j
            break
        elif re.match(r"^[-+]?\d+(?:,\d{3})*(?:\.\d+)?\s*(?:H|L|\*)$", sub):
            num_part = re.match(r"^[-+]?\d+(?:,\d{3})*(?:\.\d+)?", sub).group(0)
            val = float(num_part.replace(',', ''))
            val_idx = j
            break

    # Process collected reference categories
    if category_entries:
        # Check if both Low (<X) and High (>Y) boundaries are present (e.g. HDL Cholesterol)
        low_entry = next((e for e in category_entries if "low" in e[0].lower()), None)
        high_entry = next((e for e in category_entries if "high" in e[0].lower() and not "borderline" in e[0].lower() and not "very" in e[0].lower()), None)
        if low_entry and high_entry and low_entry != high_entry:
            ref_low = low_entry[1] or low_entry[2]
            ref_high = high_entry[1] or high_entry[2]
            ref_raw = f"{low_entry[0].strip()}, {high_entry[0].strip()}"
        else:
            # Look for normal/desirable/optimal/non-diabetes healthy target category
            healthy_entry = next((
                e for e in category_entries
                if any(k in e[0].lower() for k in ["non-diabetes", "desirable", "normal", "optimal", "sufficiency", "target", "adult"])
            ), None)
            if healthy_entry:
                ref_low, ref_high, ref_raw = healthy_entry[1], healthy_entry[2], healthy_entry[3]
            else:
                first_e = category_entries[0]
                ref_low, ref_high, ref_raw = first_e[1], first_e[2], first_e[3]

    if val is not None and val_idx != -1:
        evaluation = evaluate_parameter(val, ref_low, ref_high, ref_raw, param_name=name)
        return ExtractedParameter(
            name=name,
            value=val,
            unit=unit or default_unit,
            referenceLow=ref_low,
            referenceHigh=ref_high,
            referenceRaw=ref_raw,
            rawLine=line,
            evaluation=evaluation
        ), val_idx

    return None, i


def extract_parameters(raw_text: str) -> List[ExtractedParameter]:
    """
    Deterministic rule-based extractor for clinical laboratory blood reports.
    Takes raw document text and extracts a structured list of medical parameters.

    Guarantee:
    - Never fabricates reference ranges or guesses values. Missing items are None.
    - Deterministic execution without LLMs or non-deterministic heuristics.
    """
    if not raw_text or not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.split('\n')]
    extracted: List[ExtractedParameter] = []
    seen_names = set()

    in_narrative_section = False
    idx = 0
    while idx < len(lines):
        line_clean = lines[idx]
        if not line_clean:
            idx += 1
            continue

        lower = line_clean.lower()

        # Reset narrative flag on page markers or panel headers
        if (
            line_clean.startswith("--- Page") or
            re.match(r"^Page \d+", line_clean, re.IGNORECASE) or
            lower in SECTION_PANEL_HEADERS or
            any(h in lower for h in ["test name", "parameter name", "investigation"])
        ):
            in_narrative_section = False

        # Detect narrative section starters
        if any(lower.startswith(ns) for ns in [
            "explanation:-", "explanation", "interpretation:", "interpretation",
            "limitations:", "limitations", "summary and uses:", "summary and uses",
            "clinical significance:", "clinical significance", "comments:-", "comments:",
            "reference :", "references :"
        ]):
            in_narrative_section = True
            idx += 1
            continue

        if in_narrative_section:
            idx += 1
            continue

        # Skip typical header rows
        if any(h in lower for h in [
            "test name", "parameter name", "investigation", "result unit", "reference interval"
        ]):
            idx += 1
            continue

        # Skip patient profile / lab meta rows
        if any(p in lower for p in ["patient:", "patient name:", "doctor:", "specimen:"]):
            idx += 1
            continue

        param: Optional[ExtractedParameter] = None

        # Strategy 1: Pipe-delimited table line
        if '|' in line_clean:
            param = _parse_pipe_line(line_clean)

        # Strategy 2: Whitespace columnar table line (2+ spaces between tokens)
        if not param and re.search(r"\s{2,}", line_clean):
            param = _parse_columnar_line(line_clean)

        # Strategy 3: Key-value line (with colon or single space)
        if not param:
            param = _parse_key_value_line(line_clean)

        if param and param.value is not None:
            # Avoid duplicate extractions of the exact same test name
            if param.name not in seen_names:
                seen_names.add(param.name)
                extracted.append(param)
                logger.debug(f"Extracted parameter: {param.name} = {param.value} {param.unit} (Ref: {param.referenceRaw})")
            idx += 1
            continue

        # Strategy 4: Multi-line vertical layout test block
        param_multi, next_idx = _parse_multi_line_block(lines, idx)
        if param_multi and param_multi.value is not None:
            if param_multi.name not in seen_names:
                seen_names.add(param_multi.name)
                extracted.append(param_multi)
                logger.debug(f"Extracted multi-line parameter: {param_multi.name} = {param_multi.value} {param_multi.unit} (Ref: {param_multi.referenceRaw})")
            idx = next_idx + 1
            continue

        idx += 1

    return extracted
