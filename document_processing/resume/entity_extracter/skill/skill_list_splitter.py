import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[4]

MASTER_SKILL_DICTIONARY = (
    BASE_DIR
    / "data"
    / "resume"
    / "skills"
    / "master_skill_dictionary.json"
)

SKILL_ALIASES = (
    BASE_DIR
    / "data"
    / "resume"
    / "skills"
    / "skill_aliases.json"
)


# ---------------------------------------------------------------------
# JSON LOADERS
# ---------------------------------------------------------------------

def _load_json(path: Path) -> Any:
    """Load JSON safely."""
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _load_master_skills() -> list[str]:
    """
    Load active skill names from master_skill_dictionary.json.
    """
    data = _load_json(MASTER_SKILL_DICTIONARY)

    if not data:
        return []

    skills: list[str] = []

    if isinstance(data, list):
        for item in data:

            if isinstance(item, str):
                value = item.strip()

                if value:
                    skills.append(value)

            elif isinstance(item, dict):

                status = item.get("status", "active")

                if status not in ("active", None):
                    continue

                value = (
                    item.get("name")
                    or item.get("skill")
                    or item.get("skill_name")
                    or item.get("canonical_name")
                )

                if isinstance(value, str) and value.strip():
                    skills.append(value.strip())

    elif isinstance(data, dict):

        for key, value in data.items():

            if isinstance(value, str):
                value = value.strip()

                if value:
                    skills.append(value)

            elif isinstance(key, str):
                key = key.strip()

                if key:
                    skills.append(key)

    # Remove duplicates while preserving order.
    return list(dict.fromkeys(skills))


def _load_aliases() -> dict[str, str]:
    """
    Load skill aliases.

    Keys are normalized for matching.
    Values are canonical skill names.
    """
    data = _load_json(SKILL_ALIASES)

    if not isinstance(data, dict):
        return {}

    aliases: dict[str, str] = {}

    for key, value in data.items():

        if not isinstance(key, str):
            continue

        if not isinstance(value, str):
            continue

        key = key.strip()
        value = value.strip()

        if not key or not value:
            continue

        aliases[_normalize_match_text(key)] = value

    return aliases


# ---------------------------------------------------------------------
# NORMALIZATION
# ---------------------------------------------------------------------

def _normalize_match_text(value: str) -> str:
    """
    Normalize text only for comparison.

    This does NOT change the returned skill.
    """
    if not isinstance(value, str):
        return ""

    value = value.lower().strip()

    value = value.replace("–", "-")
    value = value.replace("—", "-")

    value = re.sub(r"\s+", " ", value)

    return value


def _compact_match_text(value: str) -> str:
    """
    Create a compact comparison form.

    Examples:

        Fast API
        fastapi

    both become:

        fastapi
    """
    normalized = _normalize_match_text(value)

    return re.sub(r"[^a-z0-9]+", "", normalized)


# ---------------------------------------------------------------------
# CLEANING
# ---------------------------------------------------------------------

def _clean_skill_item(skill: str) -> str:
    """Clean an individual skill."""
    if not isinstance(skill, str):
        return ""

    skill = skill.strip()

    skill = re.sub(r"^[,;|•·]+", "", skill)
    skill = re.sub(r"[,;|•·]+$", "", skill)

    skill = re.sub(r"\s+", " ", skill)

    return skill.strip()


def _remove_category_prefix(skill: str) -> str:
    """
    Remove a category prefix.

    Examples:

        Backend: Django, Flask
        Frontend: React
        Database: MySQL

    become:

        Django, Flask
        React
        MySQL
    """
    if not isinstance(skill, str):
        return ""

    skill = skill.strip()

    # Only remove a prefix when a colon is present.
    match = re.match(
        r"^[A-Za-z][A-Za-z0-9 /&+.#-]*\s*:\s*",
        skill,
    )

    if match:
        skill = skill[match.end():]

    return skill.strip()


# ---------------------------------------------------------------------
# ALIAS HANDLING
# ---------------------------------------------------------------------

def _apply_formatting_alias(
    skill: str,
    aliases: dict[str, str],
) -> str:
    """
    Apply ONLY formatting-equivalent aliases.

    Examples:

        Fast API -> FastAPI
        node js -> Node.js
        django-rest-framework -> Django REST Framework

    But:

        REST APIs -> REST APIs

    because:

        restapis != restapi
    """
    skill = _clean_skill_item(skill)

    if not skill:
        return ""

    normalized = _normalize_match_text(skill)

    canonical = aliases.get(normalized)

    if not canonical:
        return skill

    # Only normalize if the difference is formatting.
    if _compact_match_text(skill) == _compact_match_text(canonical):
        return canonical

    # Otherwise preserve the candidate text.
    return skill


# ---------------------------------------------------------------------
# EXPLICIT-SEPARATOR SPLITTING
# ---------------------------------------------------------------------

def _split_explicit_separators(
    text: str,
    aliases: dict[str, str],
) -> list[str]:
    """
    Split comma/semicolon/pipe/bullet separated skills.
    """
    parts = re.split(r"[,;|•·]+", text)

    result: list[str] = []

    for part in parts:

        part = _clean_skill_item(part)
        part = _remove_category_prefix(part)

        if not part:
            continue

        part = _apply_formatting_alias(
            part,
            aliases,
        )

        if part:
            result.append(part)

    return result


# ---------------------------------------------------------------------
# MASTER-DICTIONARY MATCHING
# ---------------------------------------------------------------------

def _build_known_skill_phrases(
    master_skills: list[str],
    aliases: dict[str, str],
) -> dict[str, list[tuple[str, list[str]]]]:
    """
    Build all recognized phrases.

    Both master names and alias names are accepted for matching.
    """
    phrases: set[str] = set()

    for skill in master_skills:

        normalized = _normalize_match_text(skill)

        if normalized:
            phrases.add(normalized)

    for alias in aliases:

        normalized = _normalize_match_text(alias)

        if normalized:
            phrases.add(normalized)

    # Keep the original longest-first order within each initial token.
    ordered_phrases = sorted(
        phrases,
        key=lambda value: (
            len(value.split()),
            len(value),
        ),
        reverse=True,
    )

    phrases_by_first_token: dict[
        str,
        list[tuple[str, list[str]]],
    ] = {}

    for phrase in ordered_phrases:
        phrase_tokens = phrase.split()

        if phrase_tokens:
            phrases_by_first_token.setdefault(
                phrase_tokens[0],
                [],
            ).append((phrase, phrase_tokens))

    return phrases_by_first_token


def _find_matching_phrase(
    tokens: list[str],
    start: int,
    phrases: dict[str, list[tuple[str, list[str]]]],
) -> tuple[str | None, int]:
    """
    Find the longest known skill beginning at `start`.

    Returns:

        (matched_phrase, number_of_tokens)

    or:

        (None, 0)
    """
    for phrase, phrase_tokens in phrases.get(tokens[start], ()):
        count = len(phrase_tokens)

        if start + count > len(tokens):
            continue

        if tokens[start:start + count] == phrase_tokens:
            return phrase, count

    return None, 0


def _split_using_known_skills(
    text: str,
    aliases: dict[str, str],
    phrases: dict[str, list[tuple[str, list[str]]]],
) -> list[str]:
    """
    Split whitespace-separated skills using the master dictionary.

    Example:

        Python SQL MySQL JavaScript HTML CSS Git

    becomes:

        Python
        SQL
        MySQL
        JavaScript
        HTML
        CSS
        Git
    """
    text = _clean_skill_item(text)

    if not text:
        return []

    if not phrases:
        return []

    normalized_text = _normalize_match_text(text)

    tokens = normalized_text.split()

    result: list[str] = []

    index = 0

    while index < len(tokens):

        matched_phrase, token_count = _find_matching_phrase(
            tokens,
            index,
            phrases,
        )

        if matched_phrase is None:

            # Unknown token.
            index += 1
            continue

        # Preserve the candidate's token spelling as much as possible.
        original_tokens = tokens[
            index:index + token_count
        ]

        candidate = " ".join(original_tokens)

        # Apply only formatting aliases.
        candidate = _apply_formatting_alias(
            candidate,
            aliases,
        )

        if candidate:
            result.append(candidate)

        index += token_count

    return result


# ---------------------------------------------------------------------
# ONE-LINE PROCESSING
# ---------------------------------------------------------------------

def _split_line(
    line: str,
    aliases: dict[str, str],
    phrases: dict[str, list[tuple[str, list[str]]]],
) -> list[str]:

    if not isinstance(line, str):
        return []

    line = line.strip()

    if not line:
        return []

    # Remove category labels such as Backend:
    line = _remove_category_prefix(line)

    if not line:
        return []

    # -------------------------------------------------------------
    # Case 1: explicit separators
    # -------------------------------------------------------------
    if re.search(r"[,;|•·]", line):

        return _split_explicit_separators(
            line,
            aliases,
        )

    # -------------------------------------------------------------
    # Case 2: whitespace-separated skills
    # -------------------------------------------------------------
    result = _split_using_known_skills(
        line,
        aliases,
        phrases,
    )

    if result:
        return result

    # -------------------------------------------------------------
    # Case 3: entire line is one skill
    # -------------------------------------------------------------
    cleaned = _clean_skill_item(line)

    if cleaned:
        return [
            _apply_formatting_alias(
                cleaned,
                aliases,
            )
        ]

    return []


# ---------------------------------------------------------------------
# PUBLIC FUNCTION
# ---------------------------------------------------------------------

def split_skill_line(raw_skills: Any) -> list[str]:
    """
    Split skills from a resume skills section.

    Supported:

        "Python SQL MySQL Git"

        ["Python SQL MySQL Git"]

        [["Backend: Django, Flask, Fast API"]]

        [["Backend: Django"], ["Frontend: React"]]

    Responsibilities:

        - split skills
        - recognize master-dictionary skills
        - recognize aliases
        - preserve candidate spelling where appropriate
        - normalize formatting-only aliases

    Not responsible for:

        - fuzzy matching
        - synonym resolution
        - semantic relationships
        - stack expansion
        - skill IDs
        - confidence scoring
    """

    master_skills = _load_master_skills()
    aliases = _load_aliases()

    if raw_skills is None:
        return []

    # -------------------------------------------------------------
    # Flatten input
    # -------------------------------------------------------------

    lines: list[str] = []

    def collect(value: Any) -> None:

        if isinstance(value, str):

            if value.strip():
                lines.append(value)

        elif isinstance(value, (list, tuple)):

            for item in value:
                collect(item)

    collect(raw_skills)

    if not lines:
        return []

    phrases: dict[
        str,
        list[tuple[str, list[str]]],
    ] = {}

    if any(
        not re.search(r"[,;|•·]", line)
        for line in lines
    ):
        phrases = _build_known_skill_phrases(
            master_skills,
            aliases,
        )

    # -------------------------------------------------------------
    # Split every line
    # -------------------------------------------------------------

    result: list[str] = []

    for line in lines:

        result.extend(
            _split_line(
                line,
                aliases,
                phrases,
            )
        )

    # -------------------------------------------------------------
    # Deduplicate
    # -------------------------------------------------------------

    deduplicated: list[str] = []

    seen: set[str] = set()

    for skill in result:

        normalized = _normalize_match_text(skill)

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        deduplicated.append(skill)

    return deduplicated