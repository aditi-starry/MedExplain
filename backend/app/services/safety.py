"""
Checks applied to every AI-generated sentence before it is shown to a patient.

These are deliberately conservative: when a check fails, the caller replaces the AI
text with deterministic content and says so, instead of showing unverified text.
"""
import re
from typing import Iterable, Optional, Set

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Phrases that assert a diagnosis or give treatment/medication instructions
_UNSAFE_PATTERNS = [
    r"\byou (?:have|are suffering from|definitely have|likely have|probably have|clearly have)\s+(?:a |an )?(?:diabetes|prediabetes|anemia|anaemia|cancer|leukemia|kidney (?:disease|failure)|liver (?:disease|damage|failure)|hypothyroidism|hyperthyroidism|thalassemia|cirrhosis|hepatitis|gout|infection|heart disease)",
    r"\byou are (?:diabetic|anemic|anaemic|prediabetic)\b",
    r"\b(?:this|it|these results?|your results?) (?:confirms?|proves?|means you have|shows you have|indicates you have)\b",
    r"\byou (?:are|have been) diagnosed\b",
    r"\b(?:start|stop|begin|increase|decrease|reduce|double|change|adjust|skip)\s+(?:taking\s+)?(?:your\s+|any\s+)?(?:medication|medicines?|dose|dosage|tablets?|pills?|insulin|metformin|statins?|supplements?|treatment)\b",
    r"\byou should (?:take|use)\s+(?:a |an |some )?(?:medication|medicine|tablets?|pills?|insulin|metformin|statins?|iron|vitamin|supplements?|antibiotics?)\b",
    r"\b\d+(?:\.\d+)?\s?(?:mg|mcg|µg|iu|units)\b(?!\s*/)",
    r"\bno need to (?:see|consult|talk to) (?:a |your )?(?:doctor|physician|healthcare)",
    r"आपको\s+(?:मधुमेह|डायबिटीज|एनीमिया|कैंसर)\s+है",
    r"तुम्हाला\s+(?:मधुमेह|डायबिटीज|अ‍ॅनिमिया|अॅनिमिया|कर्करोग)\s+आहे",
    r"(?:दवा|गोली|दवाई)\s+(?:लें|लेना शुरू|बंद करें)",
    r"(?:औषध|गोळी|गोळ्या)\s+(?:घ्या|सुरू करा|बंद करा)",
]
_UNSAFE_RE = [re.compile(p, re.IGNORECASE) for p in _UNSAFE_PATTERNS]

_DIRECTION_WORDS = {
    "en": {
        "Above Range": ["above", "higher", "high", "exceed", "over", "elevated", "more than"],
        "Below Range": ["below", "lower", "low", "under", "less than"],
        "Within Range": ["within", "inside", "in range", "between", "in the range", "normal range"],
    },
    "hi": {
        "Above Range": ["अधिक", "ज़्यादा", "ज्यादा", "ऊपर", "ऊँचा", "बढ़ा"],
        "Below Range": ["कम", "नीचे"],
        "Within Range": ["भीतर", "अंदर", "बीच", "सामान्य"],
    },
    "mr": {
        "Above Range": ["जास्त", "अधिक", "वर", "वाढ"],
        "Below Range": ["कमी", "खाली"],
        "Within Range": ["मर्यादेत", "आत", "दरम्यान", "मध्ये", "सामान्य"],
    },
}


def normalize_digits(text: str) -> str:
    return (text or "").translate(_DEVANAGARI_DIGITS)


def has_unsafe_claim(text: str) -> bool:
    t = normalize_digits(text)
    return any(p.search(t) for p in _UNSAFE_RE)


def script_matches(text: str, language: str) -> bool:
    """Checks the answer is written in the requested script (avoids silently mixed languages)."""
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return False
    deva = sum(1 for ch in letters if "\u0900" <= ch <= "\u097f")
    ratio = deva / len(letters)
    if language in ("hi", "mr"):
        # Parameter names and units stay in English, so require a clear Devanagari majority only
        return ratio >= 0.45
    return ratio < 0.05


def numbers_in_text(text: str) -> Set[float]:
    t = normalize_digits(text)
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)  # 1,200 -> 1200
    out: Set[float] = set()
    for m in re.findall(r"\d+(?:\.\d+)?", t):
        try:
            out.add(round(float(m), 4))
        except ValueError:
            pass
    return out


def numbers_are_grounded(text: str, allowed: Iterable[float], small_int_limit: int = 3) -> bool:
    """Every number in the text must come from the report or the cited evidence."""
    allowed_set = {round(float(a), 4) for a in allowed}
    for n in numbers_in_text(text):
        if n in allowed_set:
            continue
        if n == int(n) and n <= small_int_limit:
            continue
        return False
    return True


def direction_consistent(text: str, evaluation: Optional[str], language: str) -> bool:
    """The text must describe the result in the same direction as the deterministic evaluation."""
    words = _DIRECTION_WORDS.get(language, {}).get(evaluation or "")
    if not words:
        return True  # Not Evaluated: nothing to check
    low = text.lower()
    return any(w in low for w in words)