"""
Evidence-grounded report explanations.

Pipeline:
  validated report data -> knowledge retrieval (per result + relationships)
  -> one batched Gemini call -> per-item validation -> patient-facing output.

Anything the model returns that fails validation is replaced by deterministic
content, and the response says so (`source`, per-item `source`, `notice`).
"""
import json
import logging
import time
from typing import Dict, List, Optional, Sequence, Set, Tuple

from app.models.report import (
    ExtractedParameter,
    ParameterExplanation,
    RelationshipInsight,
    ReportExplanationResponse,
)
from app.services import llm_client
from app.services.i18n import LANGUAGE_NAMES, t
from app.services.insights import (
    ABNORMAL,
    build_rationale,
    doctor_questions,
    find_relationships,
    format_value,
    range_text,
)
from app.services.knowledge_base import Evidence, get_knowledge_base, numbers_in, resolve_sources
from app.services.safety import (
    direction_consistent,
    has_unsafe_claim,
    numbers_are_grounded,
    script_matches,
)

logger = logging.getLogger(__name__)

STANDARD_DISCLAIMER = {
    "en": "MedExplain AI is an educational tool, not a medical diagnosis or treatment plan. Please review your results with a qualified healthcare professional.",
    "hi": "MedExplain AI एक शैक्षिक साधन है, यह चिकित्सा निदान या उपचार योजना नहीं है। कृपया अपने परिणाम किसी योग्य स्वास्थ्य विशेषज्ञ के साथ देखें।",
    "mr": "MedExplain AI हे एक शैक्षणिक साधन आहे, वैद्यकीय निदान किंवा उपचार योजना नाही. कृपया तुमचे निकाल पात्र आरोग्य तज्ज्ञांसोबत पाहा.",
}

MAX_SUMMARY_CHARS = 450
MAX_NEXT_STEP_CHARS = 220

SYSTEM_INSTRUCTION = """You are MedExplain AI, which explains a patient's own laboratory results in plain language.
Hard rules:
- Explain the patient's ACTUAL result: refer to the value and whether it is within, above or below the range printed on the report. Do not give textbook definitions; at most one short clause on what the test measures, only if it helps.
- The "status" field is computed by software from the report and is final. Never contradict it, never change any value, unit or range, and never state a range that is not given.
- Use general medical information ONLY from the evidence passages provided, and list the ids of the passages you used in "citations". If no passage supports a statement, do not make it.
- Never diagnose, never say the patient has a disease, never name a cause as certain, never recommend, start, stop or change medicines, supplements, doses or treatment.
- Results within range: one short sentence, no advice, no invented concerns.
- Results outside range: up to three short sentences with cautious context from the evidence (e.g. "can be associated with"), and a short neutral nextStep such as discussing it with a healthcare professional. Do not be alarmist.
- For one-sided limits such as "< 200" or "> 40", say "above the report's limit of 200" or "below the report's minimum of 40".
- The patient's age and sex are not provided: do not apply age- or sex-specific thresholds from the evidence.
- If the evidence is missing or insufficient, say only what the report itself shows.
- Write every text field in the requested language only. Keep test names, numbers and units exactly as given. Use Western digits (0-9).
- Return only JSON matching the requested schema."""


def _param_record(p: ExtractedParameter, pid: str, evidence: Sequence[Evidence]) -> Dict:
    return {
        "id": pid,
        "test": p.name,
        "value": format_value(p),
        "reportRange": range_text(p),
        "status": p.evaluation or "Not Evaluated",
        "evidence": [{"id": e.passage.id, "text": e.passage.text} for e in evidence],
    }


def _counts(params: Sequence[ExtractedParameter]) -> Dict[str, int]:
    within = sum(1 for p in params if p.evaluation == "Within Range")
    outside = sum(1 for p in params if (p.evaluation or "") in ABNORMAL)
    return {"total": len(params), "withinRange": within, "outsideRange": outside, "notEvaluated": len(params) - within - outside}


def _build_prompt(language: str, items: List[Dict], relationships: List[Dict], counts: Dict[str, int]) -> str:
    request = {
        "language": LANGUAGE_NAMES[language],
        "resultCounts": counts,
        "results": items,
        "documentedRelationships": relationships,
        "outputSchema": {
            "narrativeSummary": "2-3 sentences: overall picture of THIS report (use resultCounts exactly if you mention how many results; name which tests are outside range), no advice beyond suggesting a discussion with a healthcare professional when results are outside range",
            "explanations": [{"id": "result id", "summary": "text", "nextStep": "text or null (null for within-range results)", "citations": ["passage ids used"]}],
            "relationships": [{"id": "relationship id", "explanation": "1-2 sentences explaining why these results are usually looked at together, as an observed pattern not a diagnosis", "citations": ["passage ids used"]}],
            "doctorQuestions": ["3-6 specific questions the patient could ask a healthcare professional about THESE results; no symptoms or history that are not given; no medicines"],
        },
    }
    return json.dumps(request, ensure_ascii=False)


def _fallback_summary(p: ExtractedParameter, language: str) -> str:
    key = {
        "Within Range": "fallback.within",
        "Above Range": "fallback.above",
        "Below Range": "fallback.below",
    }.get(p.evaluation or "", "fallback.not_evaluated")
    return t(language, key, name=p.name, value=format_value(p), range=range_text(p, language))


def _fallback_explanation(p: ExtractedParameter, evidence_ids: List[str], language: str, method: str) -> ParameterExplanation:
    return ParameterExplanation(
        name=p.name,
        summary=_fallback_summary(p, language),
        nextStep=t(language, "fallback.next_step") if (p.evaluation or "") in ABNORMAL else None,
        source="fallback",
        evidenceStatus="limited" if evidence_ids else "none",
        citations=[],
        rationale=build_rationale(p, evidence_ids, language, method),
    )


def _fallback_narrative(params: Sequence[ExtractedParameter], language: str) -> str:
    within = sum(1 for p in params if p.evaluation == "Within Range")
    outside = sum(1 for p in params if (p.evaluation or "") in ABNORMAL)
    return t(language, "fallback.narrative", total=len(params), within=within, outside=outside,
             unevaluated=len(params) - within - outside)


def _report_numbers(params: Sequence[ExtractedParameter]) -> Set[float]:
    nums: Set[float] = {float(len(params))}
    for p in params:
        for v in (p.value, p.referenceLow, p.referenceHigh):
            if v is not None:
                nums.add(round(float(v), 4))
        nums |= numbers_in([p.referenceRaw or "", p.unit or "", p.name])
    within = sum(1 for p in params if p.evaluation == "Within Range")
    outside = sum(1 for p in params if (p.evaluation or "") in ABNORMAL)
    nums |= {float(within), float(outside), float(len(params) - within - outside)}
    return nums


def _text_ok(text: str, language: str, allowed_numbers: Set[float], max_chars: int) -> bool:
    return (
        isinstance(text, str)
        and 0 < len(text.strip()) <= max_chars
        and script_matches(text, language)
        and not has_unsafe_claim(text)
        and numbers_are_grounded(text, allowed_numbers)
    )


def _valid_citations(raw, allowed_ids: Set[str]) -> List[str]:
    if not isinstance(raw, list):
        return []
    out = []
    for c in raw:
        if isinstance(c, str) and c in allowed_ids and c not in out:
            out.append(c)
    return out


async def generate_report_explanations(
    report_id: str,
    parameters: List[ExtractedParameter],
    language: str = "en",
    extraction_method: str = "pymupdf",
    use_ai: bool = True,
) -> ReportExplanationResponse:
    kb = get_knowledge_base()
    language = language if language in LANGUAGE_NAMES else "en"
    disclaimer = STANDARD_DISCLAIMER[language]

    if not parameters:
        return ReportExplanationResponse(
            reportId=report_id, language=language, source="fallback", generatedAt=time.time(),
            narrativeSummary=_fallback_narrative([], language), disclaimer=disclaimer,
        )

    # 1. Retrieval: evidence for every result, plus documented relationships
    evidence_by_param: Dict[str, List[Evidence]] = {}
    items = []
    for i, p in enumerate(parameters):
        pid = f"r{i + 1}"
        ev = kb.evidence_for_parameter(p.name, p.evaluation, k=3)
        evidence_by_param[pid] = ev
        items.append(_param_record(p, pid, ev))

    relationships = find_relationships(parameters, language)
    rel_items = []
    for rel in relationships:
        rel_items.append({
            "id": rel.id,
            "results": [f"{rp.name} {format_value(ExtractedParameter(name=rp.name, value=rp.value, unit=rp.unit))} ({rp.evaluation})" for rp in rel.parameters],
            "documentedRelationship": rel.description,
            "evidence": [{"id": e, "text": kb.passages[e].text} for e in rel.evidence if e in kb.passages],
        })

    fallback_doctor_questions = doctor_questions(parameters, relationships, language)
    fallback_explanations = [
        _fallback_explanation(p, [e.passage.id for e in evidence_by_param[f"r{i + 1}"]], language, extraction_method)
        for i, p in enumerate(parameters)
    ]

    def fallback_response(notice_key: Optional[str]) -> ReportExplanationResponse:
        source_ids = [eid for e in fallback_explanations for eid in e.rationale.evidenceIds]
        source_ids += [eid for r in relationships for eid in r.evidence]
        return ReportExplanationResponse(
            reportId=report_id, language=language, source="fallback", model=None,
            notice=t(language, notice_key) if notice_key else None, generatedAt=time.time(),
            narrativeSummary=_fallback_narrative(parameters, language), disclaimer=disclaimer,
            parameters=parameters, explanations=fallback_explanations, relationships=relationships,
            doctorQuestions=fallback_doctor_questions, doctorQuestionsSource="fallback",
            sources=resolve_sources(source_ids),
        )

    if not use_ai:
        return fallback_response(None)

    # 2. Generation
    try:
        result, model = await llm_client.generate_json(
            SYSTEM_INSTRUCTION, _build_prompt(language, items, rel_items, _counts(parameters)), temperature=0.2, max_output_tokens=8192,
        )
    except llm_client.LLMUnavailable as exc:
        logger.info("Explanations for a report fell back to deterministic content (%s)", exc.reason)
        return fallback_response("notice.unconfigured" if exc.reason == "unconfigured" else "notice.error")

    # 3. Validation, item by item
    report_numbers = _report_numbers(parameters)
    raw_by_id = {}
    for e in result.get("explanations") or []:
        if isinstance(e, dict) and isinstance(e.get("id"), str):
            raw_by_id[e["id"]] = e

    final: List[ParameterExplanation] = []
    replaced = 0
    for i, p in enumerate(parameters):
        pid = f"r{i + 1}"
        ev = evidence_by_param[pid]
        ev_ids = {e.passage.id for e in ev}
        allowed_numbers = report_numbers | numbers_in(e.passage.text for e in ev)
        raw = raw_by_id.get(pid)
        explanation: Optional[ParameterExplanation] = None
        if raw:
            summary = raw.get("summary")
            next_step = raw.get("nextStep") if (p.evaluation or "") in ABNORMAL else None
            citations = _valid_citations(raw.get("citations"), ev_ids)
            ok = _text_ok(summary, language, allowed_numbers, MAX_SUMMARY_CHARS) and direction_consistent(summary, p.evaluation, language)
            if next_step is not None and not _text_ok(next_step, language, allowed_numbers, MAX_NEXT_STEP_CHARS):
                next_step = t(language, "fallback.next_step")
            if ok:
                explanation = ParameterExplanation(
                    name=p.name,
                    summary=summary.strip(),
                    nextStep=next_step.strip() if isinstance(next_step, str) and next_step.strip() else None,
                    source="ai",
                    evidenceStatus="supported" if citations else ("limited" if ev_ids else "none"),
                    citations=citations,
                    rationale=build_rationale(p, citations or [e.passage.id for e in ev], language, extraction_method),
                )
        if explanation is None:
            replaced += 1
            explanation = fallback_explanations[i]
        final.append(explanation)

    if replaced == len(parameters):
        return fallback_response("notice.error")

    # Relationship explanations (optional, validated against that relationship's evidence)
    rel_raw = {r.get("id"): r for r in (result.get("relationships") or []) if isinstance(r, dict)}
    for rel in relationships:
        raw = rel_raw.get(rel.id)
        if not raw:
            continue
        rel_ids = set(rel.evidence)
        allowed = report_numbers | numbers_in(kb.passages[e].text for e in rel.evidence if e in kb.passages)
        text = raw.get("explanation")
        if _text_ok(text, language, allowed, MAX_SUMMARY_CHARS) and _valid_citations(raw.get("citations"), rel_ids):
            rel.explanation = text.strip()

    # The narrative may only state the deterministic counts, so a miscount cannot slip through
    narrative = result.get("narrativeSummary")
    count_numbers = {float(v) for v in _counts(parameters).values()}
    if not _text_ok(narrative, language, count_numbers, 600):
        narrative = _fallback_narrative(parameters, language)

    questions = [q.strip() for q in (result.get("doctorQuestions") or []) if isinstance(q, str)]
    questions = [q for q in questions if _text_ok(q, language, report_numbers, 260)][:6]
    questions_source = "ai"
    if len(questions) < 2:
        questions, questions_source = fallback_doctor_questions, "fallback"

    source_ids = []
    for e in final:
        source_ids += e.citations or e.rationale.evidenceIds
    for rel in relationships:
        source_ids += rel.evidence

    return ReportExplanationResponse(
        reportId=report_id,
        language=language,
        source="mixed" if replaced else "ai",
        model=model,
        notice=t(language, "notice.partial") if replaced else None,
        generatedAt=time.time(),
        narrativeSummary=narrative.strip(),
        disclaimer=disclaimer,
        parameters=parameters,
        explanations=final,
        relationships=relationships,
        doctorQuestions=questions,
        doctorQuestionsSource=questions_source,
        sources=resolve_sources(source_ids),
    )