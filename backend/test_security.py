"""Upload validation, access control, retention, error handling and secret-handling tests."""
import json
import time

import pytest
from fastapi import HTTPException

from app import config
from app.security import RateLimiter
from app.services import storage


def post_file(client, name, content, mime="application/pdf"):
    return client.post("/api/reports/upload", files={"file": (name, content, mime)})


def test_rejects_unsupported_extension(client):
    resp = post_file(client, "notes.txt", b"hello", "text/plain")
    assert resp.status_code == 400


def test_rejects_content_that_does_not_match_extension(client):
    resp = post_file(client, "fake.pdf", b"MZ\x90\x00 this is not a pdf")
    assert resp.status_code == 400
    assert "does not look like" in resp.json()["detail"]


def test_rejects_empty_and_oversized_files(client):
    assert post_file(client, "empty.pdf", b"").status_code == 400
    big = b"%PDF-" + b"0" * (config.MAX_UPLOAD_SIZE_BYTES + 1)
    assert post_file(client, "big.pdf", big).status_code == 413


def test_path_traversal_filenames_are_sanitized(client):
    resp = post_file(client, "..\\..\\etc/passwd.pdf", b"%PDF-1.4 minimal")
    assert resp.status_code == 201
    name = resp.json()["fileName"]
    assert "/" not in name and "\\" not in name and not name.startswith(".")
    assert storage.sanitize_filename("../../a b?.pdf") == "a_b_.pdf"


def test_report_ids_are_unguessable_and_tokens_not_stored(client, upload):
    report_id, headers = upload()
    assert len(report_id) == 4 + 24
    record = storage.load_record(report_id)
    assert headers["X-Report-Token"] not in json.dumps(record)
    assert record["tokenHash"] != headers["X-Report-Token"]


@pytest.mark.parametrize("path", ["/api/reports/{id}", "/api/reports/{id}/parameters", "/api/reports/{id}/insights",
                                  "/api/reports/{id}/summary.pdf"])
def test_endpoints_require_the_right_token(client, upload, path):
    report_id, headers = upload()
    other_id, other_headers = upload()
    url = path.format(id=report_id)
    assert client.get(url).status_code == 404
    assert client.get(url, headers=other_headers).status_code == 404
    assert client.get(url, headers=headers).status_code == 200


def test_malformed_ids_are_rejected(client):
    for bad in ["..%2F..%2Fetc", "rep_XYZ", "rep_" + "a" * 40, "anything"]:
        assert client.get(f"/api/reports/{bad}", headers={"X-Report-Token": "x" * 20}).status_code == 404


def test_delete_removes_report(client, upload):
    report_id, headers = upload()
    assert client.delete(f"/api/reports/{report_id}", headers=headers).status_code == 204
    assert client.get(f"/api/reports/{report_id}", headers=headers).status_code == 404
    assert not list(config.UPLOAD_DIR.glob(f"{report_id}*"))


def test_expired_reports_are_purged(client, upload):
    report_id, headers = upload()
    record = storage.load_record(report_id)
    record["createdAt"] = time.time() - (config.REPORT_RETENTION_HOURS + 1) * 3600
    storage.save_record(record)
    assert client.get(f"/api/reports/{report_id}", headers=headers).status_code == 404
    assert storage.load_record(report_id) is None


def test_purge_leaves_legacy_uploads_untouched(tmp_path, monkeypatch):
    legacy = config.UPLOAD_DIR / "rep_3ef140eb_old_report.pdf"
    legacy.write_bytes(b"%PDF-legacy")
    old = time.time() - 10 * 24 * 3600
    import os
    os.utime(legacy, (old, old))
    storage.purge_expired_reports()
    assert legacy.exists()
    legacy.unlink()


def test_rate_limiter_blocks_bursts():
    limiter = RateLimiter()
    for _ in range(3):
        limiter.check("ip", 3)
    with pytest.raises(HTTPException) as exc:
        limiter.check("ip", 3)
    assert exc.value.status_code == 429


def test_validation_errors_do_not_echo_input(client, upload):
    report_id, headers = upload()
    secret_like = "PATIENT-NAME-SHOULD-NOT-ECHO"
    resp = client.post(f"/api/reports/{report_id}/chat", json={"message": 123, "language": secret_like}, headers=headers)
    assert resp.status_code == 422
    assert secret_like not in resp.text


def test_health_never_exposes_secrets(client, monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "SECRET-KEY-VALUE-123")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["aiConfigured"] is True
    assert "SECRET-KEY-VALUE-123" not in resp.text
    assert body["knowledgePassages"] > 0


def test_gemini_key_is_sent_in_header_not_url(monkeypatch):
    import asyncio
    import httpx
    from app.services import llm_client

    seen = {}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json=None, headers=None):
            seen["url"], seen["headers"] = url, headers
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "{\"ok\": true}"}]}}]})

    monkeypatch.setattr(config, "GEMINI_API_KEY", "SECRET-KEY-VALUE-123")
    monkeypatch.setattr(llm_client.httpx, "AsyncClient", FakeClient)
    data, model = asyncio.run(llm_client.generate_json("sys", "{}"))
    assert data == {"ok": True}
    assert "SECRET-KEY-VALUE-123" not in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == "SECRET-KEY-VALUE-123"


def test_security_headers_present(client):
    resp = client.get("/api/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"