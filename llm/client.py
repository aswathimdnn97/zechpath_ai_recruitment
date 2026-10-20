"""
Minimal OpenAI-compatible JSON chat client.

Uses the standard library so ATS scoring does not gain a hard LLM dependency.
Never logs prompt or completion text: those can contain resume PII.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Optional

from llm.config import LLMSettings, load_llm_settings


logger = logging.getLogger(__name__)


class LLMClientError(RuntimeError):
    """Raised when the provider cannot return usable JSON."""


def _parse_json_content(content: str) -> dict[str, Any]:
    if not isinstance(content, str) or not content.strip():
        raise LLMClientError("Empty model content.")

    text = content.strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMClientError("Model response was not valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise LLMClientError("Model JSON must be an object.")

    return parsed


def complete_json(
    system_prompt: str,
    user_prompt: str,
    settings: Optional[LLMSettings] = None,
) -> dict[str, Any]:
    """
    Call chat completions and return a parsed JSON object.

    The caller must not pass secrets or extra PII beyond the resume
    fragment required for the task.
    """

    resolved = settings or load_llm_settings()

    if not resolved.is_ready():
        raise LLMClientError("LLM is not configured.")

    payload = {
        "model": resolved.model,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
    }

    url = f"{resolved.base_url}/chat/completions"
    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {resolved.api_key}",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=resolved.timeout_seconds,
        ) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        logger.warning(
            "LLM HTTP error: status=%s",
            exc.code,
        )
        raise LLMClientError(f"LLM HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        logger.warning("LLM request failed.")
        raise LLMClientError("LLM request failed.") from exc

    try:
        envelope = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMClientError("Provider envelope was not JSON.") from exc

    try:
        content = envelope["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMClientError("Unexpected provider envelope.") from exc

    return _parse_json_content(content)
