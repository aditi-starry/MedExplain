"""
Report-aware chatbot (RAG).

Each answer is grounded in (1) the selected report's extracted, deterministically
evaluated results and (2) passages retrieved from the curated knowledge base.
The conversation history is supplied by the client for the current session only;
the server stores no chat transcripts.
"""
import json
import logging
import re
from typing import List, Optional, Sequence

from app.models.report import ChatMessage, ChatResponse, ExtractedParameter
from app.services import llm_client
from app.services.i18n import LANGUAGE_NAMES, status_label, t
from app.services.insights import ABNORMAL, format_value, range_text
from app.services.knowledge_base import Evidence, get_knowledge_base, numbers_in, resolve_sources
from app.services.safety import has_unsafe_claim, numbers_are_grounded, script_matches

logger = logging.getLogger(__name__)

MAX_HISTORY_TURNS = 8
MAX_ANSWER_CHARS = 1200

# Messages describing possible emergencies get a fixed safety reply without calling the AI
_EMERGENCY_PATTERNS = [
    r"chest pain", r"can'?t breathe", r"cannot breathe", r"difficulty breathing", r"short(ness)? of breath",
    r"unconscious", r"passed out", r"faint(ed|ing)", r"seizure", r"stroke", r"heart attack",
    r"severe bleeding", r"bleeding (heavily|a lot)", r"suicid", r"kill myself", r"overdose",
    r"सीने में दर्द", r"छाती में दर्द", r"सांस (नहीं|लेने में)", r"बेहोश", r"आत्महत्या",
    r"छातीत दुखत", r"श्वास घेण्यास", r"बेशुद्ध", r"आत्महत्य",
]
_EMERGENCY_RE = re.compile("|".join(_EMERGENCY_PATTERNS), re.IGNORECASE)

SYSTEM_INSTRUCTION = """You are MedExplain AI's report assistant. You help a patient understand THEIR OWN lab report.
Rules:
- Use only (a) the report results given, whose "status" was computed by software and is final, and (b) the evidence passages given. Cite the ids of passages you rely on in "citations".
- Answer the question asked, briefly (normally 2-5 short sentences). Do not repeat the whole report; mention only the results that matter for the question.
- Never diagnose, never say the patient has a condition, never claim certainty about causes, never recommend or change medicines, supplements, doses or treatment, and do not give individualized clinical advice. General educational context is fine when the evidence supports it.
- The patient's age and sex are not provided: do not apply age- or sex-specific thresholds.
- If the question is unclear, ask one short clarifying question. If the report or evidence is not enough to answer, say so plainly.
- If asked which results to discuss with a doctor, point to the results outside their report range, without implying urgency.
- Write the answer only in the requested language. Keep test names, numbers and units exactly as given. Use Western digits (0-9).
- Return JSON: {"answer": string, "citations": [passage ids], "usedResults": [test names], "insufficientEvidence": boolean}."""


def is_emergency(text: str) -> bool:
    return bool(_EMERGENCY_RE.search(text or ""))


def _relevant_parameters(message: str, history: Sequence[ChatMessage], params: Sequence[ExtractedParameter]) -> List[ExtractedParameter]:
    kb = get_knowledge_base()
    names = [p.name for p in params]
    mentioned = kb.mentioned_parameters(message, names)
    if not mentioned:
        # Follow-up questions ("what about that one?") refer back to the previous user turn
        for turn in reversed(history):
            if turn.role == "user":
                mentioned = kb.mentioned_parameters(turn.content, names)
                if mentioned:
                    break
    return [p for p in params if p.name in mentioned]


def _evidence(message: str, focus: Sequence[ExtractedParameter], params: Sequence[ExtractedParameter]) -> List[Evidence]:
    kb = get_knowledge_base()
    targets = list(focus) or [p for p in params if (p.evaluation or "") in ABNORMAL][:4]
    found: List[Evidence] = []
    seen = set()
    for p in targets:
        for e in kb.evidence_for_parameter(p.name, p.evaluation, k=2):
            if e.passage.id not in seen:
                seen.add(e.passage.id)
                found.append(e)
    for e in kb.retrieve(message, parameters=[p.name for p in targets], k=3, min_score=2.0):
        if e.passage.id not in seen:
            seen.add(e.passage.id)
            found.append(e)
    # Documented relationships between the focused results
    if len(targets) >= 2:
        for rel in kb.relationships_for([p.name for p in targets]):
            for pid in rel.evidence[:1]:
                if pid not in seen and pid in kb.passages:
                    seen.add(pid)
                    found.append(Evidence(kb.passages[pid], 0.0))
    return found[:8]


def _fallback_answer(message: str, focus: Sequence[ExtractedParameter], params: Sequence[ExtractedParameter], language: str) -> str:
    if focus:
        lines = []
        for p in focus[:4]:
            key = {"Within Range": "fallback.within", "Above Range": "fallback.above",
                   "Below Range": "fallback.below"}.get(p.evaluation or "", "fallback.not_evaluated")
            lines.append(t(language, key, name=p.name, value=format_value(p), range=range_text(p, language)))
        return " ".join(lines)
    abnormal = [p for p in params if (p.evaluation or "") in ABNORMAL]
    if abnormal:
        items = ", ".join(f"{p.name} {format_value(p)} ({status_label(language, p.evaluation)})" for p in abnormal)
        return t(language, "chat.fallback_outside", items=items)
    if params:
        return t(language, "chat.fallback_all_within")
    return t(language, "chat.fallback_unknown", example="Hemoglobin")


async def answer_question(
    message: str,
    history: Sequence[ChatMessage],
    params: Sequence[ExtractedParameter],
    language: str = "en",
) -> ChatResponse:
    language = language if language in LANGUAGE_NAMES else "en"

    if is_emergency(message):
        return ChatResponse(answer=t(language, "chat.emergency"), source="safety")

    focus = _relevant_parameters(message, history, params)
    evidence = _evidence(message, focus, params)
    evidence_ids = {e.passage.id for e in evidence}

    report_rows = [
        {"test": p.name, "value": format_value(p), "reportRange": range_text(p), "status": p.evaluation or "Not Evaluated"}
        for p in params
    ]
    turns = [{"role": h.role, "content": h.content[:1500]} for h in list(history)[-MAX_HISTORY_TURNS:]]
    prompt = json.dumps({
        "language": LANGUAGE_NAMES[language],
        "reportResults": report_rows,
        "resultsMentionedInQuestion": [p.name for p in focus],
        "evidence": [{"id": e.passage.id, "source": e.passage.document.title, "text": e.passage.text} for e in evidence],
        "conversationSoFar": turns,
        "question": message,
    }, ensure_ascii=False)

    def fallback(notice: Optional[str]) -> ChatResponse:
        return ChatResponse(
            answer=_fallback_answer(message, focus, params, language),
            source="fallback",
            notice=notice,
            citations=[],
            usedParameters=[p.name for p in focus],
            evidenceStatus="none",
        )

    try:
        result, _model = await llm_client.generate_json(SYSTEM_INSTRUCTION, prompt, temperature=0.3, max_output_tokens=2048)
    except llm_client.LLMUnavailable:
        return fallback(t(language, "chat.fallback_notice"))

    answer = result.get("answer")
    if not isinstance(answer, str) or not answer.strip() or len(answer) > MAX_ANSWER_CHARS or not script_matches(answer, language):
        return fallback(t(language, "chat.fallback_notice"))
    if has_unsafe_claim(answer):
        return ChatResponse(answer=t(language, "chat.blocked"), source="safety")

    allowed_numbers = numbers_in([json.dumps(report_rows)] + [e.passage.text for e in evidence])
    allowed_numbers |= {float(len(params))}
    if not numbers_are_grounded(answer, allowed_numbers):
        return fallback(t(language, "chat.fallback_notice"))

    citations = [c for c in (result.get("citations") or []) if isinstance(c, str) and c in evidence_ids]
    names = {p.name for p in params}
    used = [n for n in (result.get("usedResults") or []) if isinstance(n, str) and n in names] or [p.name for p in focus]
    insufficient = bool(result.get("insufficientEvidence"))
    return ChatResponse(
        answer=answer.strip(),
        source="ai",
        citations=resolve_sources(citations),
        usedParameters=used,
        evidenceStatus="supported" if citations else ("none" if insufficient or not evidence else "limited"),
    )