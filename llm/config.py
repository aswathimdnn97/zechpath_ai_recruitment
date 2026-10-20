"""
LLM configuration.

Environment variables
---------------------
LLM_API_KEY
    Provider API key. When unset, LLM calls are skipped.

LLM_BASE_URL
    OpenAI-compatible base URL. Default: https://api.openai.com/v1

LLM_MODEL
    Chat model name. Default: gpt-4o-mini

LLM_TIMEOUT_SECONDS
    HTTP timeout. Default: 20

LLM_SECTION_DETECTION_ENABLED
    Set to 0/false/off to force-disable the section-detection fallback.
    Default: enabled when LLM_API_KEY is present.

LLM_MAX_SECTION_LINES
    Maximum numbered resume lines sent to the model. Default: 250
"""

from __future__ import annotations

import os
from dataclasses import dataclass


try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)

    if raw is None:
        return default

    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)

    if raw is None or not raw.strip():
        return default

    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class LLMSettings:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int
    section_detection_enabled: bool
    max_section_lines: int

    def is_ready(self) -> bool:
        return bool(self.api_key) and bool(self.base_url) and bool(self.model)


def load_llm_settings() -> LLMSettings:
    api_key = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
    enabled_default = bool(api_key)

    return LLMSettings(
        api_key=api_key,
        base_url=(
            os.getenv("LLM_BASE_URL")
            or "https://api.openai.com/v1"
        ).rstrip("/"),
        model=(os.getenv("LLM_MODEL") or "gpt-4o-mini").strip(),
        timeout_seconds=_env_int("LLM_TIMEOUT_SECONDS", 20),
        section_detection_enabled=_env_flag(
            "LLM_SECTION_DETECTION_ENABLED",
            enabled_default,
        ),
        max_section_lines=_env_int("LLM_MAX_SECTION_LINES", 250),
    )
