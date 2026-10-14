"""
Security helpers: report identifiers, per-report access tokens and a small rate limiter.

MedExplain AI has no user accounts. Instead, every uploaded report gets a random
access token that is returned only once (to the uploader). All report endpoints
require that token in the `X-Report-Token` header, so knowing or guessing a report
ID is not enough to read someone else's report. Only a SHA-256 hash of the token
is stored on the server.
"""
import hashlib
import hmac
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

REPORT_ID_PATTERN = re.compile(r"^rep_[0-9a-f]{8,32}$")
TOKEN_HEADER = "X-Report-Token"


def generate_report_id() -> str:
    """Unguessable report identifier, e.g. rep_3f9a0c1d2e4b5a6978c0d1e2."""
    return f"rep_{secrets.token_hex(12)}"


def is_valid_report_id(report_id: str) -> bool:
    return bool(report_id) and bool(REPORT_ID_PATTERN.match(report_id))


def generate_access_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def token_matches(token: str, token_hash: str) -> bool:
    if not token or not token_hash:
        return False
    return hmac.compare_digest(hash_token(token), token_hash)


def validate_report_id_or_404(report_id: str) -> None:
    # Malformed IDs get the same response as unknown IDs (no information leak)
    if not is_valid_report_id(report_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")


class RateLimiter:
    """In-memory sliding-window limiter keyed by client IP. Good enough for a single instance."""

    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: float = 60.0) -> None:
        if limit <= 0:
            return
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > window_seconds:
                hits.popleft()
            if len(hits) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Please wait a minute and try again.",
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()


def client_key(request: Request, bucket: str) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    return f"{bucket}:{ip}"