"""Report-aware chatbot tests: grounding, safety, follow-ups, fallbacks and access control."""


def ask(client, report_id, headers, message, history=None, language="en"):
    return client.post(f"/api/reports/{report_id}/chat",
                       json={"message": message, "history": history or [], "language": language}, headers=headers)


def test_emergency_message_gets_safety_reply_without_ai(client, upload, mock_llm):
    report_id, headers = upload()
    data = ask(client, report_id, headers, "I have chest pain right now, is it my cholesterol?").json()
    assert data["source"] == "safety"
    assert "emergency" in data["answer"].lower()
    assert mock_llm.calls == []


def test_fallback_lists_out_of_range_results(client, upload):
    report_id, headers = upload()
    data = ask(client, report_id, headers, "Which results should I discuss with my doctor?").json()
    assert data["source"] == "fallback" and data["notice"]
    assert "Ferritin" in data["answer"] and "White Blood Cells" not in data["answer"]


def test_ai_answer_with_valid_citations(client, upload, mock_llm):
    def respond(prompt):
        ev = prompt["evidence"]
        return {"answer": "Your Ferritin of 9 ng/mL is below the report range of 13 - 150 ng/mL. Ferritin reflects stored iron.",
                "citations": [ev[0]["id"], "invented-citation"], "usedResults": ["Ferritin", "Unknown"], "insufficientEvidence": False}
    mock_llm.response = respond
    report_id, headers = upload()
    data = ask(client, report_id, headers, "What does my ferritin mean?").json()
    prompt = mock_llm.calls[0]
    assert prompt["resultsMentionedInQuestion"] == ["Ferritin"]
    assert any(e["id"].startswith("mlp-ferritin") for e in prompt["evidence"])
    assert data["source"] == "ai" and data["evidenceStatus"] == "supported"
    assert [c["id"] for c in data["citations"]] == [prompt["evidence"][0]["id"]]
    assert data["usedParameters"] == ["Ferritin"]


def test_follow_up_question_keeps_context(client, upload, mock_llm):
    mock_llm.response = {"answer": "It is below the range on your report.", "citations": [], "usedResults": [], "insufficientEvidence": True}
    report_id, headers = upload()
    history = [{"role": "user", "content": "Tell me about my Vitamin D"},
               {"role": "assistant", "content": "Your Vitamin D is 18 ng/mL, below the report range."}]
    ask(client, report_id, headers, "Why could that be?", history=history)
    prompt = mock_llm.calls[0]
    assert prompt["resultsMentionedInQuestion"] == ["Vitamin D"]
    assert prompt["conversationSoFar"][0]["content"] == "Tell me about my Vitamin D"


def test_unsafe_ai_answer_is_blocked(client, upload, mock_llm):
    mock_llm.response = {"answer": "You have diabetes. Start taking metformin.", "citations": [], "usedResults": []}
    report_id, headers = upload()
    data = ask(client, report_id, headers, "Do I have diabetes?").json()
    assert data["source"] == "safety"
    assert "metformin" not in data["answer"]


def test_ungrounded_numbers_trigger_fallback(client, upload, mock_llm):
    mock_llm.response = {"answer": "Your glucose should be under 85 mg/dL.", "citations": [], "usedResults": []}
    report_id, headers = upload()
    data = ask(client, report_id, headers, "What should my glucose be?").json()
    assert data["source"] == "fallback"


def test_chat_requires_matching_report_token(client, upload):
    report_a, headers_a = upload()
    report_b, headers_b = upload()
    assert ask(client, report_a, {}, "hello").status_code == 404
    assert ask(client, report_a, headers_b, "hello").status_code == 404
    assert ask(client, report_a, {"X-Report-Token": "wrong-token-value"}, "hello").status_code == 404
    assert ask(client, report_a, headers_a, "hello").status_code == 200


def test_chat_input_limits(client, upload):
    report_id, headers = upload()
    assert ask(client, report_id, headers, "").status_code == 422
    assert ask(client, report_id, headers, "x" * 1001).status_code == 422
    assert ask(client, report_id, headers, "hi", language="fr").status_code == 422