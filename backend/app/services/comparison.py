"""
Deterministic comparison of two reports from the same person.

Numbers are compared only when both values exist and the units are compatible.
A change is reported as a number; it is never labelled as improvement or deterioration.
"""
import re
from datetime import date
from typing import Dict, List, Optional, Tuple

from app.models.report import ComparisonRow, ExtractedParameter

# Units that are numerically identical even though they are written differently
_EQUIVALENT_UNITS = [
    {"x10^3/ul", "10^3/ul", "x10³/ul", "10³/ul", "k/ul", "thou/ul", "x10^9/l", "10^9/l", "x10e3/ul", "10*3/ul", "/nl"},
    {"x10^6/ul", "10^6/ul", "x10⁶/ul", "10⁶/ul", "m/ul", "mill/ul", "x10^12/l", "10^12/l", "million/ul", "10*6/ul"},
    {"mg/dl", "mg%"},
    {"g/dl", "gm/dl", "gms/dl", "g%", "gm%"},
    {"u/l", "iu/l"},
    {"fl", "femtolitre", "femtoliter", "cu.micron", "µm3", "um3"},
    {"pg", "picogram", "picograms"},
    {"%", "percent"},
]


def normalize_unit(unit: Optional[str]) -> Optional[str]:
    if not unit:
        return None
    u = unit.strip().lower().replace("μ", "u").replace("µ", "u").replace(" ", "")
    return u or None


# mEq/L equals mmol/L only for ions with a single charge
_MONOVALENT_IONS = {"Sodium", "Potassium", "Chloride", "Bicarbonate"}


def units_compatible(a: Optional[str], b: Optional[str], name: Optional[str] = None) -> bool:
    na, nb = normalize_unit(a), normalize_unit(b)
    if na is None or nb is None:
        return False
    if na == nb:
        return True
    if name in _MONOVALENT_IONS and {na, nb} <= {"meq/l", "mmol/l"}:
        return True
    return any(na in group and nb in group for group in _EQUIVALENT_UNITS)


def compare_parameters(previous: List[ExtractedParameter], current: List[ExtractedParameter]) -> List[ComparisonRow]:
    prev_by_name: Dict[str, ExtractedParameter] = {p.name: p for p in previous}
    cur_by_name: Dict[str, ExtractedParameter] = {p.name: p for p in current}
    rows: List[ComparisonRow] = []

    for name, cur in cur_by_name.items():
        prev = prev_by_name.get(name)
        if prev is None:
            rows.append(ComparisonRow(name=name, status="only_in_current", currentValue=cur.value,
                                      currentUnit=cur.unit, currentEvaluation=cur.evaluation))
            continue
        base = dict(name=name, previousValue=prev.value, currentValue=cur.value, previousUnit=prev.unit,
                    currentUnit=cur.unit, previousEvaluation=prev.evaluation, currentEvaluation=cur.evaluation)
        if prev.value is None or cur.value is None:
            rows.append(ComparisonRow(status="missing_value", **base))
            continue
        if not units_compatible(prev.unit, cur.unit, name):
            rows.append(ComparisonRow(status="incompatible_units", **base))
            continue
        diff = round(cur.value - prev.value, 6)
        pct = round(diff / prev.value * 100, 1) if prev.value != 0 else None
        direction = "unchanged" if diff == 0 else ("increased" if diff > 0 else "decreased")
        rows.append(ComparisonRow(status="compared", difference=diff, percentChange=pct, direction=direction, **base))

    for name, prev in prev_by_name.items():
        if name not in cur_by_name:
            rows.append(ComparisonRow(name=name, status="only_in_previous", previousValue=prev.value,
                                      previousUnit=prev.unit, previousEvaluation=prev.evaluation))
    order = {"compared": 0, "incompatible_units": 1, "missing_value": 2, "only_in_current": 3, "only_in_previous": 4}
    rows.sort(key=lambda r: order[r.status])
    return rows


# ---------------- report date extraction ----------------

_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}
_DATE_LABEL = re.compile(
    r"(report(?:ed)?\s*(?:date|on)|date\s*of\s*report|collect(?:ed|ion)\s*(?:date|on)?|sample\s*(?:date|collected(?:\s*on)?)|"
    r"registered\s*on|received\s*on|test\s*date|date)\s*[:\-]?\s*(.{0,40})",
    re.IGNORECASE,
)
_NUMERIC_DATE = re.compile(r"\b(\d{1,4})[./-](\d{1,2})[./-](\d{2,4})\b")
_TEXT_DATE = re.compile(r"\b(\d{1,2})[\s-]*([A-Za-z]{3,9})[\s,-]*(\d{4})\b")


def _parse_date(text: str) -> Optional[Tuple[str, str]]:
    m = _NUMERIC_DATE.search(text)
    if m:
        a, b, c = m.groups()
        try:
            if len(a) == 4:            # yyyy-mm-dd
                d = date(int(a), int(b), int(c))
            else:                      # dd/mm/yyyy (common on Indian and UK reports)
                year = int(c) + (2000 if len(c) == 2 else 0)
                d = date(year, int(b), int(a))
            return d.isoformat(), m.group(0)
        except ValueError:
            return None
    m = _TEXT_DATE.search(text)
    if m:
        day, month, year = m.groups()
        month_num = _MONTHS.get(month[:3].lower())
        if month_num:
            try:
                return date(int(year), month_num, int(day)).isoformat(), m.group(0)
            except ValueError:
                return None
    return None


def extract_report_date(text: str) -> Tuple[Optional[str], Optional[str]]:
    """Returns (iso_date, raw_text) for the first labelled date found in the report, else (None, None)."""
    if not text:
        return None, None
    # Prefer explicit report/collection labels over a bare "Date"
    candidates = []
    for line in text.splitlines()[:80]:
        for m in _DATE_LABEL.finditer(line):
            parsed = _parse_date(m.group(2))
            if parsed:
                priority = 1 if m.group(1).strip().lower() == "date" else 0
                candidates.append((priority, parsed))
    if not candidates:
        return None, None
    candidates.sort(key=lambda c: c[0])
    return candidates[0][1]