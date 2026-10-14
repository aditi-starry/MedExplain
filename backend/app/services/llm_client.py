"""
Minimal Gemini API client.

- The API key is sent in the `x-goog-api-key` header (never in the URL, so it cannot
  appear in HTTP access logs) and is never logged or returned to clients.
- Models are tried in order: GEMINI_MODEL, then GEMINI_FALLBACK_MODELS.
- Only the model name and HTTP status are logged, never prompts or responses,
  because prompts contain report data.
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app import config

logger = logging.getLogger(__name__)

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"


class LLMUnavailable(Exception):
    """Raised when no usable answer could be obtained. `reason` is 'unconfigured' or 'error'."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def is_configured() -> bool:
    return bool(config.GEMINI_API_KEY)


def _models() -> List[str]:
    models: List[str] = []
    for m in [config.GEMINI_MODEL, *config.GEMINI_FALLBACK_MODELS]:
        if m and m not in models:
            models.append(m)
    return models


def _parse_json_text(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.S)
    if fence:
        cleaned = fence.group(1)
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("Expected a JSON object")
    return data


async def generate_json(
    system_instruction: str,
    prompt: str,
    temperature: float = 0.2,
    max_output_tokens: int = 4096,
) -> Tuple[Dict[str, Any], str]:
    """Calls Gemini in JSON mode. Returns (parsed_json, model_name) or raises LLMUnavailable."""
    if not is_configured():
        raise LLMUnavailable("unconfigured")

    payload = {
        "systemInstruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
    }
    headers = {"x-goog-api-key": config.GEMINI_API_KEY, "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=config.GEMINI_TIMEOUT_SECONDS) as client:
        for model in _models():
            try:
                resp = await client.post(f"{API_ROOT}/{model}:generateContent", json=payload, headers=headers)
            except httpx.HTTPError as exc:
                logger.warning("Gemini request to model %s failed: %s", model, type(exc).__name__)
                continue
            if resp.status_code != 200:
                logger.warning("Gemini model %s returned HTTP %s", model, resp.status_code)
                continue
            try:
                data = resp.json()
                candidate = (data.get("candidates") or [{}])[0]
                parts = candidate.get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
                if not text:
                    logger.warning("Gemini model %s returned no text (finishReason=%s)", model, candidate.get("finishReason"))
                    continue
                return _parse_json_text(text), model
            except (ValueError, KeyError, IndexError, TypeError):
                logger.warning("Gemini model %s returned unparseable JSON", model)
                continue
    raise LLMUnavailable("error")


def model_list() -> List[str]:
    return _models()


def configured_model() -> Optional[str]:
    return config.GEMINI_MODEL if is_configured() else None