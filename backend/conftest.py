"""
Test configuration: isolated temporary storage, no real AI calls, generous rate limits.
These environment variables are set before the app is imported.
"""
import os
import sys
import tempfile
from pathlib import Path

_TMP = tempfile.mkdtemp(prefix="medexplain_test_")
os.environ["DATA_DIR"] = _TMP
os.environ["GEMINI_API_KEY"] = ""  # tests must never call the real Gemini API
os.environ["RATE_LIMIT_UPLOADS_PER_MINUTE"] = "1000"
os.environ["RATE_LIMIT_AI_PER_MINUTE"] = "1000"

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SCRATCH = Path(__file__).resolve().parent / "scratch_test_files"
SAMPLE_CURRENT = SCRATCH / "sample_lab_report.pdf"
SAMPLE_PREVIOUS = SCRATCH / "sample_lab_report_previous.pdf"


@pytest.fixture(scope="session")
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def upload(client):
    """Uploads a PDF and returns (report_id, headers_with_access_token)."""
    def _upload(path=SAMPLE_CURRENT, name="report.pdf"):
        with open(path, "rb") as f:
            resp = client.post("/api/reports/upload", files={"file": (name, f, "application/pdf")})
        assert resp.status_code == 201, resp.text
        body = resp.json()
        return body["reportId"], {"X-Report-Token": body["accessToken"]}
    return _upload


@pytest.fixture
def mock_llm(monkeypatch):
    """
    Replaces the Gemini call. Set `mock_llm.response` to a dict (or a callable taking the
    prompt JSON) or `mock_llm.error` to a reason string. Records calls in `mock_llm.calls`.
    """
    import json as _json
    from app.services import llm_client

    class _Mock:
        response = None
        error = None
        calls = []

    mock = _Mock()
    mock.calls = []

    async def fake_generate_json(system_instruction, prompt, temperature=0.2, max_output_tokens=4096):
        mock.calls.append(_json.loads(prompt))
        if mock.error:
            raise llm_client.LLMUnavailable(mock.error)
        resp = mock.response(_json.loads(prompt)) if callable(mock.response) else mock.response
        return resp, "mock-model"

    monkeypatch.setattr(llm_client, "generate_json", fake_generate_json)
    monkeypatch.setattr(llm_client, "is_configured", lambda: True)
    return mock
