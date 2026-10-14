"""RAG knowledge base, retrieval, source metadata and knowledge-graph tests."""
from app.models.report import ExtractedParameter
from app.services.insights import doctor_questions, find_relationships
from app.services.knowledge_base import get_knowledge_base, resolve_sources


def P(name, value, evaluation, unit="", low=None, high=None):
    return ExtractedParameter(name=name, value=value, unit=unit, referenceLow=low, referenceHigh=high, evaluation=evaluation)


def test_knowledge_base_is_consistent_and_attributed():
    kb = get_knowledge_base()
    assert kb.validate() == []
    assert len(kb.passages) >= 60
    for p in kb.passages.values():
        doc = p.document
        assert doc.url.startswith("https://medlineplus.gov/lab-tests/")
        assert doc.title and doc.publisher and doc.retrieved and doc.last_updated
        assert "public domain" in doc.license


def test_every_relationship_cites_existing_evidence():
    kb = get_knowledge_base()
    assert kb.relationships
    for rel in kb.relationships:
        assert rel.evidence and all(e in kb.passages for e in rel.evidence)
        assert len(rel.members) >= 2


def test_retrieval_prefers_direction_specific_passages():
    kb = get_knowledge_base()
    low = [e.passage.id for e in kb.evidence_for_parameter("Hemoglobin", "Below Range")]
    high = [e.passage.id for e in kb.evidence_for_parameter("Hemoglobin", "Above Range")]
    assert low[0] == "mlp-hemoglobin-2"
    assert high[0] == "mlp-hemoglobin-3"
    assert all(e.startswith("mlp-hemoglobin") for e in low)


def test_retrieval_uses_synonyms():
    kb = get_knowledge_base()
    ids = [e.passage.id for e in kb.retrieve("what does my SGPT mean", parameters=["sgpt"])]
    assert ids and ids[0].startswith("mlp-alt")


def test_missing_evidence_returns_nothing():
    kb = get_knowledge_base()
    assert kb.evidence_for_parameter("pH", "Within Range") == []
    assert kb.evidence_for_parameter("Serum Ceruloplasmin", "Within Range") == []
    assert kb.retrieve("is it safe to drive a car", min_score=2.0) == []


def test_resolve_sources_ignores_unknown_ids():
    sources = resolve_sources(["mlp-hemoglobin-1", "not-a-real-id", "mlp-hemoglobin-1"])
    assert [s["id"] for s in sources] == ["mlp-hemoglobin-1"]
    assert sources[0]["url"] == "https://medlineplus.gov/lab-tests/hemoglobin-test/"


def test_mentioned_parameters_handles_aliases_and_hindi():
    kb = get_knowledge_base()
    names = ["Hemoglobin", "Potassium", "Fasting Glucose"]
    assert kb.mentioned_parameters("मेरा हीमोग्लोबिन कम क्यों है?", names) == ["Hemoglobin"]
    assert kb.mentioned_parameters("Is my K ok?", names) == ["Potassium"]
    assert kb.mentioned_parameters("I am ok", names) == []


def test_relationships_need_two_present_and_one_abnormal():
    params = [P("Hemoglobin", 11.2, "Below Range"), P("Hematocrit", 34, "Below Range"), P("Sodium", 140, "Within Range")]
    rels = find_relationships(params, "en")
    ids = [r.id for r in rels]
    assert "rel-hb-hct-rbc" in ids
    hb_rel = next(r for r in rels if r.id == "rel-hb-hct-rbc")
    assert hb_rel.missingRelated == ["Red Blood Cells"]
    assert "not a diagnosis" in hb_rel.caution
    # All within range -> no relationship insights are forced
    assert find_relationships([P("Hemoglobin", 13, "Within Range"), P("Hematocrit", 40, "Within Range")], "en") == []
    # Unrelated abnormal results are not linked
    assert find_relationships([P("TSH", 6, "Above Range"), P("Ferritin", 5, "Below Range")], "en") == []


def test_doctor_questions_are_specific_and_safe():
    params = [P("Ferritin", 9, "Below Range", "ng/mL"), P("Triglycerides", 182, "Above Range", "mg/dL"), P("TSH", 2, "Within Range")]
    qs = doctor_questions(params, [], "en")
    assert any("Ferritin" in q and "9 ng/mL" in q for q in qs)
    assert any("fasting" in q.lower() for q in qs)
    joined = " ".join(qs).lower()
    for banned in ("urgent", "emergency", "take ", "mg of"):
        assert banned not in joined
    all_ok = doctor_questions([P("TSH", 2, "Within Range")], [], "hi")
    assert any("सीमा के भीतर" in q for q in all_ok)