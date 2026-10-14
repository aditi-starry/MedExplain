"""
Deterministic report reasoning: value formatting, explainable rationales,
multi-parameter relationship insights (from the knowledge graph) and
doctor-question suggestions. No AI is used here, so every output can be checked.
"""
from typing import Dict, List, Optional, Sequence

from app.models.report import ExtractedParameter, InsightParameter, Rationale, RelationshipInsight
from app.services.i18n import status_label, t
from app.services.knowledge_base import get_knowledge_base

ABNORMAL = {"Above Range", "Below Range"}


def format_number(v: Optional[float]) -> str:
    if v is None:
        return "-"
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.6f}".rstrip("0").rstrip(".")


def format_value(p: ExtractedParameter) -> str:
    if p.value is None:
        return "-"
    return f"{format_number(p.value)} {p.unit or ''}".strip()


def range_text(p: ExtractedParameter, language: str = "en") -> str:
    if p.referenceRaw:
        raw = " ".join(p.referenceRaw.split())
        if p.unit and p.unit not in raw and not any(ch.isalpha() for ch in raw):
            return f"{raw} {p.unit}"
        return raw
    unit = f" {p.unit}" if p.unit else ""
    if p.referenceLow is not None and p.referenceHigh is not None:
        return f"{format_number(p.referenceLow)} - {format_number(p.referenceHigh)}{unit}"
    if p.referenceHigh is not None:
        return f"< {format_number(p.referenceHigh)}{unit}"
    if p.referenceLow is not None:
        return f"> {format_number(p.referenceLow)}{unit}"
    return t(language, "range.not_stated")


def comparison_text(p: ExtractedParameter) -> str:
    """Language-neutral arithmetic statement of how the value relates to the stated bounds."""
    v, lo, hi = p.value, p.referenceLow, p.referenceHigh
    ev = p.evaluation or "Not Evaluated"
    if v is None or ev == "Not Evaluated":
        return "-"
    fv = format_number(v)
    if ev == "Within Range":
        if lo is not None and hi is not None:
            return f"{format_number(lo)} ≤ {fv} ≤ {format_number(hi)}"
        if hi is not None:
            return f"{fv} < {format_number(hi)}" if v < hi else f"{fv} ≤ {format_number(hi)}"
        if lo is not None:
            return f"{fv} > {format_number(lo)}" if v > lo else f"{fv} ≥ {format_number(lo)}"
    if ev == "Above Range":
        if hi is not None:
            return f"{fv} > {format_number(hi)}" if v > hi else f"{fv} ≥ {format_number(hi)}"
        if lo is not None:
            return f"{fv} ≥ {format_number(lo)}"
    if ev == "Below Range":
        if lo is not None:
            return f"{fv} < {format_number(lo)}" if v < lo else f"{fv} ≤ {format_number(lo)}"
        if hi is not None:
            return f"{fv} < {format_number(hi)}"
    return "-"


def build_rationale(
    p: ExtractedParameter,
    evidence_ids: Sequence[str],
    language: str,
    extraction_method: str = "pymupdf",
) -> Rationale:
    ev = p.evaluation or "Not Evaluated"
    reason_key = {
        "Within Range": "reason.within",
        "Above Range": "reason.above",
        "Below Range": "reason.below",
    }.get(ev, "reason.not_evaluated")
    uncertainty = []
    if ev == "Not Evaluated":
        uncertainty.append(t(language, "unc.no_range"))
    else:
        uncertainty.append(t(language, "unc.lab_range"))
    if extraction_method == "paddleocr":
        uncertainty.append(t(language, "unc.ocr"))
    if not evidence_ids:
        uncertainty.append(t(language, "unc.no_evidence"))
    if ev in ABNORMAL:
        uncertainty.append(t(language, "unc.context"))
    return Rationale(
        valueConsidered=f"{p.name}: {format_value(p)}",
        rangeUsed=range_text(p, language),
        comparison=comparison_text(p),
        reason=t(language, reason_key),
        evidenceIds=list(evidence_ids),
        uncertainty=uncertainty,
    )


def find_relationships(params: Sequence[ExtractedParameter], language: str) -> List[RelationshipInsight]:
    """
    Returns documented relationships where at least two related results are present
    and at least one of them is outside its stated range. Relationships come only
    from the curated knowledge graph; nothing is inferred from the numbers alone.
    """
    kb = get_knowledge_base()
    by_canonical: Dict[str, ExtractedParameter] = {}
    for p in params:
        canonical = kb.canonical_name(p.name) or p.name
        by_canonical.setdefault(canonical, p)

    insights = []
    for rel in kb.relationships:
        present = [by_canonical[m] for m in rel.members if m in by_canonical]
        if len(present) < 2 or not any((p.evaluation or "") in ABNORMAL for p in present):
            continue
        pattern = "; ".join(
            t(language, "insight.pattern", name=p.name, status=status_label(language, p.evaluation or "Not Evaluated"), value=format_value(p))
            for p in present
        )
        insights.append(RelationshipInsight(
            id=rel.id,
            type=rel.type,
            parameters=[InsightParameter(name=p.name, value=p.value, unit=p.unit, evaluation=p.evaluation) for p in present],
            observedPattern=pattern,
            description=rel.description,
            evidence=list(rel.evidence),
            missingRelated=[m for m in rel.members if m not in by_canonical],
            caution=t(language, "insight.caution"),
        ))
    return insights


_FASTING_RELEVANT = {"Fasting Glucose", "Triglycerides", "Total Cholesterol", "LDL Cholesterol", "HDL Cholesterol"}


def doctor_questions(
    params: Sequence[ExtractedParameter],
    relationships: Sequence[RelationshipInsight],
    language: str,
    limit: int = 6,
) -> List[str]:
    """Report-specific discussion prompts built from templates (no AI, no invented history)."""
    abnormal = [p for p in params if (p.evaluation or "") in ABNORMAL]
    not_evaluated = [p for p in params if (p.evaluation or "Not Evaluated") == "Not Evaluated" and p.value is not None]
    questions: List[str] = []
    for p in abnormal[:3]:
        questions.append(t(language, "q.abnormal", name=p.name, value=format_value(p), status=status_label(language, p.evaluation)))
    if abnormal:
        questions.append(t(language, "q.retest", name=abnormal[0].name))
    if relationships:
        members = relationships[0].parameters
        questions.append(t(language, "q.related", a=members[0].name, b=members[1].name))
    if not_evaluated:
        p = not_evaluated[0]
        questions.append(t(language, "q.not_evaluated", name=p.name, value=format_value(p)))
    if not abnormal:
        questions.append(t(language, "q.all_within"))
    else:
        questions.append(t(language, "q.symptoms"))
    if any(p.name in _FASTING_RELEVANT for p in params):
        questions.append(t(language, "q.prep"))
    return questions[:limit]