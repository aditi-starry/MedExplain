"""
Explanation tests (Sprint 6, reworked): evidence-grounded Gemini explanations,
validation of AI output, clearly labelled fallbacks and multilingual handling.
All AI calls are mocked; no API key or network is needed.
"""
import re

DIRECTION = {"Above Range": "above", "Below Range": "below", "Within Range": "within", "Not Evaluated": ""}


def good_ai_response(prompt):
    """A well-behaved model answer built from the prompt (uses only given numbers and evidence ids)."""
    exps = []
    for r in prompt["results"]:
        word = DIRECTION[r["status"]]
        exps.append({
            "id": r["id"],
            "summary": f"Your {r['test']} of {r['value']} is {word} the report range of {r['reportRange']}.",
            "nextStep": "Discuss this result with a healthcare professional." if r["status"] in ("Above Range", "Below Range") else None,
            "citations": [e["id"] for e in r["evidence"][:1]],
        })
    rels = [{"id": rel["id"], "explanation": "These results are often looked at together by a healthcare professional.",
             "citations": [rel["evidence"][0]["id"]]} for rel in prompt["documentedRelationships"]]
    return {
        "narrativeSummary": "Several results on this report are outside the printed ranges; a healthcare professional can review them with you.",
        "explanations": exps,
        "relationships": rels,
        "doctorQuestions": [
            "Should my Hemoglobin be checked again?",
            "How should I read my Fasting Glucose together with my HbA1c?",
            "Do my cholesterol results need follow-up?",
        ],
    }


def explain(client, report_id, headers, **body):
    return client.post(f"/api/reports/{report_id}/explain", json=body or {"language": "en"}, headers=headers)


def test_fallback_when_ai_not_configured(client, upload):
    report_id, headers = upload()
    resp = explain(client, report_id, headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["source"] == "fallback"
    assert "not configured" in data["notice"]
    assert data["model"] is None
    by_name = {e["name"]: e for e in data["explanations"]}
    hb = by_name["Hemoglobin"]
    # Explains the actual result, not a textbook definition
    assert "11.2 g/dL" in hb["summary"] and "below" in hb["summary"]
    assert hb["source"] == "fallback"
    assert hb["nextStep"]
    assert hb["rationale"]["comparison"] == "11.2 < 12"
    assert "definition" not in hb and "educationalNotes" not in hb
    # Within-range results get no next step or invented concerns
    assert by_name["White Blood Cells"]["nextStep"] is None
    assert data["doctorQuestionsSource"] == "fallback" and len(data["doctorQuestions"]) >= 3


def test_ai_explanations_are_grounded_and_cited(client, upload, mock_llm):
    mock_llm.response = good_ai_response
    report_id, headers = upload()
    data = explain(client, report_id, headers).json()
    assert data["source"] == "ai" and data["model"] == "mock-model" and data["notice"] is None
    prompt = mock_llm.calls[0]
    # Retrieval happened before generation, and only report-derived values were sent
    hb_item = next(r for r in prompt["results"] if r["test"] == "Hemoglobin")
    assert hb_item["evidence"] and hb_item["status"] == "Below Range" and hb_item["value"] == "11.2 g/dL"
    assert "Demo Patient" not in str(prompt)  # identifying text from the report is never sent
    source_ids = {s["id"] for s in data["sources"]}
    for e in data["explanations"]:
        assert e["source"] == "ai"
        assert set(e["citations"]) <= source_ids
    assert all(s["url"].startswith("https://medlineplus.gov/") for s in data["sources"])
    assert data["doctorQuestionsSource"] == "ai"
    assert any(r["explanation"] for r in data["relationships"])


def test_invalid_ai_items_are_replaced_and_flagged(client, upload, mock_llm):
    def faulty(prompt):
        resp = good_ai_response(prompt)
        exps = {e["id"]: e for e in resp["explanations"]}
        exps["r1"]["summary"] = "Your Hemoglobin of 11.2 g/dL is within the report range."        # contradicts status
        exps["r7"]["summary"] = "Your Fasting Glucose of 112 mg/dL is above range; normal is 65."  # invented number
        exps["r9"]["summary"] = "Your Total Cholesterol is above range, so you have heart disease." # diagnosis
        exps["r10"]["citations"] = ["made-up-source-1"]                                             # fake citation
        return resp
    mock_llm.response = faulty
    report_id, headers = upload()
    data = explain(client, report_id, headers).json()
    assert data["source"] == "mixed"
    assert "safety checks" in data["notice"]
    by_name = {e["name"]: e for e in data["explanations"]}
    for name in ("Hemoglobin", "Fasting Glucose", "Total Cholesterol"):
        assert by_name[name]["source"] == "fallback", name
    ldl = by_name["LDL Cholesterol"]
    assert ldl["source"] == "ai" and "made-up-source-1" not in ldl["citations"]
    assert all(s["id"] != "made-up-source-1" for s in data["sources"])


def test_ai_error_falls_back_with_notice(client, upload, mock_llm):
    mock_llm.error = "error"
    report_id, headers = upload()
    data = explain(client, report_id, headers).json()
    assert data["source"] == "fallback"
    assert "could not be reached" in data["notice"]


def test_results_are_cached_per_language(client, upload, mock_llm):
    mock_llm.response = good_ai_response
    report_id, headers = upload()
    explain(client, report_id, headers, language="en")
    explain(client, report_id, headers, language="en")
    assert len(mock_llm.calls) == 1
    explain(client, report_id, headers, language="en", refresh=True)
    assert len(mock_llm.calls) == 2


def test_hindi_request_rejects_english_ai_text(client, upload, mock_llm):
    mock_llm.response = good_ai_response  # English text although Hindi was requested
    report_id, headers = upload()
    data = explain(client, report_id, headers, language="hi").json()
    assert mock_llm.calls[0]["language"] == "Hindi"
    assert data["source"] == "fallback" and data["language"] == "hi"
    hb = next(e for e in data["explanations"] if e["name"] == "Hemoglobin")
    assert re.search(r"[\u0900-\u097f]", hb["summary"])  # Devanagari
    assert "Hemoglobin" in hb["summary"] and "11.2 g/dL" in hb["summary"]  # name and value preserved


def test_marathi_ai_text_is_accepted(client, upload, mock_llm):
    def marathi(prompt):
        resp = good_ai_response(prompt)
        for e in resp["explanations"]:
            r = next(x for x in prompt["results"] if x["id"] == e["id"])
            word = {"Above Range": "जास्त", "Below Range": "कमी", "Within Range": "मर्यादेत"}.get(r["status"], "")
            e["summary"] = f"तुमचा {r['test']} निकाल {r['value']} आहे, जो अहवालातील मर्यादेपेक्षा {word} आहे."
            e["nextStep"] = "याबद्दल आरोग्य तज्ज्ञांशी बोला." if e["nextStep"] else None
        resp["narrativeSummary"] = "या अहवालातील काही निकाल मर्यादेबाहेर आहेत."
        resp["relationships"] = []
        resp["doctorQuestions"] = ["माझे Hemoglobin पुन्हा तपासावे का?", "माझ्या Ferritin बद्दल काय समजावे?"]
        return resp
    mock_llm.response = marathi
    report_id, headers = upload()
    data = explain(client, report_id, headers, language="mr").json()
    assert data["source"] == "ai" and data["language"] == "mr"
    assert data["doctorQuestionsSource"] == "ai"


def test_client_cannot_supply_or_alter_values(client, upload):
    report_id, headers = upload()
    fake = [{"name": "Hemoglobin", "value": 99, "unit": "g/dL", "evaluation": "Within Range"}]
    resp = client.post(f"/api/reports/{report_id}/explain", json=fake, headers=headers)
    assert resp.status_code == 422
    data = explain(client, report_id, headers).json()
    hb = next(p for p in data["parameters"] if p["name"] == "Hemoglobin")
    assert hb["value"] == 11.2 and hb["evaluation"] == "Below Range"


def test_unknown_test_reports_missing_evidence(client, tmp_path):
    from app.models.report import ExtractedParameter
    from app.services.explanation_service import generate_report_explanations
    import asyncio
    p = ExtractedParameter(name="Serum Ceruloplasmin", value=28.5, unit="mg/dL", referenceLow=20, referenceHigh=60,
                           referenceRaw="20 - 60", evaluation="Within Range")
    data = asyncio.run(generate_report_explanations("rep_" + "a" * 24, [p], "en", use_ai=False))
    exp = data.explanations[0]
    assert exp.evidenceStatus == "none" and exp.rationale.evidenceIds == []
    assert any("knowledge base" in u for u in exp.rationale.uncertainty)

def test_narrative_with_wrong_count_is_replaced(client, upload, mock_llm):
    def miscount(prompt):
        resp = good_ai_response(prompt)
        assert prompt["resultCounts"]["outsideRange"] == 12
        resp["narrativeSummary"] = "9 of 16 results are outside the printed ranges."  # 9 is a value on the report, not the count
        return resp
    mock_llm.response = miscount
    report_id, headers = upload()
    data = explain(client, report_id, headers).json()
    assert "9 of 16" not in data["narrativeSummary"]
    assert "12 outside" in data["narrativeSummary"]
