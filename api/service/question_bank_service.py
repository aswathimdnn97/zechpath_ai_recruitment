
"""
question_bank_service.py

Responsibilities
----------------
1. Load and validate the HR screening question bank and templates.
2. Validate JSON structure and unique question/template IDs.
3. Validate role, category, answer type, scoring, and template references.
4. Retrieve active questions by role, category, and language.
5. Fall back to English when a translation is missing.
6. Return candidate-facing questions without internal evaluation metadata.
7. Raise clear service errors for invalid configuration.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# PATH CONFIGURATION
# ------------------------------------------------------------

# This file is located at project_root/api/service/.
PROJECT_ROOT = Path(__file__).resolve().parents[2]

HR_SCREENING_DATA_DIR = PROJECT_ROOT / "data" / "hr_screening"

QUESTION_BANK_PATH = (
    HR_SCREENING_DATA_DIR / "question_bank_multilingual.json"
)

QUESTION_TEMPLATES_PATH = (
    HR_SCREENING_DATA_DIR / "question_templates_multilingual.json"
)

DEFAULT_LANGUAGE = "en"

REQUIRED_QUESTION_FIELDS = {
    "question_id",
    "role_id",
    "category",
    "template_id",
    "question_text",
    "answer_type",
    "mandatory",
    "active",
}

REQUIRED_TEMPLATE_FIELDS = {
    "template_id",
    "category",
    "question_pattern",
    "answer_type",
    "active",
}

SUPPORTED_ANSWER_TYPES = {
    "TEXT",
    "YES_NO_WITH_DETAILS",
    "MULTI_SELECT_WITH_DETAILS",
    "CURRENCY_RANGE",
    "DATE_OR_DURATION",
    "SINGLE_CHOICE",
    "MULTIPLE_CHOICE",
    "BOOLEAN",
}

CHOICE_ANSWER_TYPES = {
    "SINGLE_CHOICE",
    "MULTIPLE_CHOICE",
    "MULTI_SELECT_WITH_DETAILS",
}

ALLOWED_SCORING_LABELS = {
    "LOW",
    "MEDIUM",
    "HIGH",
    "CRITICAL",
}

SUPPORTED_TRANSLATION_STATUSES = {
    "NOT_TRANSLATED",
    "NEEDS_REVIEW",
    "REVIEWED",
}


# ------------------------------------------------------------
# SERVICE EXCEPTION
# ------------------------------------------------------------

class QuestionBankError(Exception):
    """Raised when question-bank data cannot be loaded or used."""


# ------------------------------------------------------------
# INTERNAL HELPERS
# ------------------------------------------------------------

def _load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file and require a top-level JSON object."""

    if not path.is_file():
        raise QuestionBankError(
            f"Required HR screening file was not found: {path}"
        )

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise QuestionBankError(
            f"Invalid JSON in {path.name}: "
            f"line {exc.lineno}, column {exc.colno}."
        ) from exc
    except OSError as exc:
        raise QuestionBankError(
            f"Unable to read {path.name}: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise QuestionBankError(
            f"{path.name} must contain a JSON object."
        )

    return data


def _normalize_identifier(value: Any) -> str:
    """Return a normalized identifier for case-insensitive comparisons."""

    if not isinstance(value, str):
        return ""

    return value.strip().casefold()


def _get_configured_id(
    record: Any,
    field_name: str,
) -> str:
    """Read an identifier from a string or configuration object."""

    if isinstance(record, str):
        return record.strip()

    if isinstance(record, dict):
        value = record.get(field_name)
        return value.strip() if isinstance(value, str) else ""

    return ""


def _validate_unique_ids(
    records: list[Any],
    id_field: str,
    file_description: str,
) -> None:
    """Ensure each record is an object with a unique, non-empty ID."""

    seen_ids: set[str] = set()

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise QuestionBankError(
                f"{file_description}: record at index {index} "
                "must be a JSON object."
            )

        record_id = record.get(id_field)

        if not isinstance(record_id, str) or not record_id.strip():
            raise QuestionBankError(
                f"{file_description}: record at index {index} "
                f"has a missing or invalid '{id_field}'."
            )

        normalized_id = record_id.strip().casefold()

        if normalized_id in seen_ids:
            raise QuestionBankError(
                f"{file_description}: duplicate {id_field} "
                f"'{record_id}'."
            )

        seen_ids.add(normalized_id)


def _validate_scoring_importance(
    question: dict[str, Any],
    question_id: str,
) -> None:
    """Validate optional scoring importance metadata."""

    value = question.get("scoring_importance")

    # Some questions may intentionally omit scoring importance.
    if value is None:
        return

    if isinstance(value, bool):
        raise QuestionBankError(
            f"Question '{question_id}' has invalid "
            "'scoring_importance'."
        )

    if isinstance(value, (int, float)):
        if not 1 <= value <= 10:
            raise QuestionBankError(
                f"Question '{question_id}' has invalid "
                "'scoring_importance'. Expected a number from 1 to 10."
            )
        return

    if isinstance(value, str):
        if value.strip().upper() not in ALLOWED_SCORING_LABELS:
            raise QuestionBankError(
                f"Question '{question_id}' has invalid "
                "'scoring_importance'. Expected a number from 1 to 10 "
                "or one of LOW, MEDIUM, HIGH, CRITICAL."
            )
        return

    raise QuestionBankError(
        f"Question '{question_id}' has invalid 'scoring_importance'."
    )


def _validate_question_options(
    question: dict[str, Any],
    question_id: str,
    answer_type: str,
) -> None:
    """Validate options for choice-based questions."""

    if answer_type not in CHOICE_ANSWER_TYPES:
        return

    options = question.get("options")

    if options is None:
        options = question.get("choices")

    if not isinstance(options, list) or not options:
        raise QuestionBankError(
            f"Question '{question_id}' uses answer type '{answer_type}' "
            "and must define a non-empty 'options' or 'choices' list."
        )

    seen_option_ids: set[str] = set()

    for index, option in enumerate(options):
        if isinstance(option, str):
            option_id = option.strip()

        elif isinstance(option, dict):
            # Use the first available identifier field.
            raw_id = (
                option.get("option_id")
                or option.get("id")
                or option.get("value")
            )
            option_id = raw_id.strip() if isinstance(raw_id, str) else ""

        else:
            option_id = ""

        if not option_id:
            raise QuestionBankError(
                f"Question '{question_id}' has an invalid option "
                f"at index {index}."
            )

        normalized_id = option_id.casefold()

        if normalized_id in seen_option_ids:
            raise QuestionBankError(
                f"Question '{question_id}' has duplicate option "
                f"'{option_id}'."
            )

        seen_option_ids.add(normalized_id)

    if answer_type == "SINGLE_CHOICE" and len(options) < 2:
        raise QuestionBankError(
            f"Question '{question_id}' must have at least two options "
            "for SINGLE_CHOICE."
        )


def _validate_language_configuration(
    data: dict[str, Any],
    file_description: str,
) -> None:
    """Validate supported languages and the default language."""

    languages = data.get("supported_languages", [DEFAULT_LANGUAGE])

    if (
        not isinstance(languages, list)
        or not languages
        or any(
            not isinstance(language, str) or not language.strip()
            for language in languages
        )
    ):
        raise QuestionBankError(
            f"{file_description}: 'supported_languages' must be "
            "a non-empty list of language codes."
        )

    normalized_languages = [language.strip().casefold() for language in languages]

    if len(normalized_languages) != len(set(normalized_languages)):
        raise QuestionBankError(
            f"{file_description}: 'supported_languages' contains duplicates."
        )

    default_language = data.get("default_language", DEFAULT_LANGUAGE)

    if (
        not isinstance(default_language, str)
        or default_language.strip().casefold() not in normalized_languages
    ):
        raise QuestionBankError(
            f"{file_description}: 'default_language' must be included "
            "in 'supported_languages'."
        )


# ------------------------------------------------------------
# QUESTION BANK VALIDATION
# ------------------------------------------------------------

def _validate_question_bank(bank: Any) -> None:
    """Validate question-bank structure and individual question records."""

    if not isinstance(bank, dict):
        raise QuestionBankError("Question bank must be a JSON object.")

    _validate_language_configuration(bank, "question_bank.json")

    questions = bank.get("questions")
    roles = bank.get("roles")
    categories = bank.get("categories")

    if not isinstance(questions, list):
        raise QuestionBankError("'questions' must be a list.")

    if not isinstance(roles, list) or not roles:
        raise QuestionBankError("'roles' must be a non-empty list.")

    if not isinstance(categories, list) or not categories:
        raise QuestionBankError("'categories' must be a non-empty list.")

    # Validate configured role identifiers.
    role_ids: set[str] = set()

    for role in roles:
        role_id = _get_configured_id(role, "role_id")

        if not role_id:
            raise QuestionBankError(
                "Each role must be a non-empty string or an object "
                "containing a non-empty 'role_id'."
            )

        normalized_id = role_id.casefold()

        if normalized_id in role_ids:
            raise QuestionBankError(
                f"Duplicate role identifier '{role_id}'."
            )

        role_ids.add(normalized_id)

    # Validate configured category identifiers.
    category_ids: set[str] = set()

    for category in categories:
        category_id = _get_configured_id(category, "category_id")

        if not category_id:
            raise QuestionBankError(
                "Each category must be a non-empty string or an object "
                "containing a non-empty 'category_id'."
            )

        normalized_id = category_id.casefold()

        if normalized_id in category_ids:
            raise QuestionBankError(
                f"Duplicate category identifier '{category_id}'."
            )

        category_ids.add(normalized_id)

    # Check record types before validating identifiers.
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            raise QuestionBankError(
                f"Question at index {index} must be a JSON object."
            )

    _validate_unique_ids(
        questions,
        "question_id",
        "question_bank.json",
    )

    supported_languages = {
        language.strip().casefold()
        for language in bank.get("supported_languages", [DEFAULT_LANGUAGE])
    }

    for question in questions:
        question_id = question["question_id"].strip()

        missing_fields = REQUIRED_QUESTION_FIELDS - question.keys()

        if missing_fields:
            raise QuestionBankError(
                f"Question '{question_id}' is missing required fields: "
                f"{sorted(missing_fields)}."
            )

        # Validate role reference.
        role_id = question.get("role_id")

        if (
            not isinstance(role_id, str)
            or role_id.strip().casefold() not in role_ids
        ):
            raise QuestionBankError(
                f"Question '{question_id}' references unknown role "
                f"'{role_id}'."
            )

        # Validate category reference.
        category = question.get("category")

        if (
            not isinstance(category, str)
            or category.strip().casefold() not in category_ids
        ):
            raise QuestionBankError(
                f"Question '{question_id}' references unknown category "
                f"'{category}'."
            )

        # Validate multilingual question text.
        question_text = question.get("question_text")

        if not isinstance(question_text, dict):
            raise QuestionBankError(
                f"Question '{question_id}' must have a 'question_text' object."
            )

        english_text = question_text.get(DEFAULT_LANGUAGE)

        if not isinstance(english_text, str) or not english_text.strip():
            raise QuestionBankError(
                f"Question '{question_id}' requires non-empty English "
                "question text for fallback."
            )

        for language, translated_text in question_text.items():
            if not isinstance(language, str) or not language.strip():
                raise QuestionBankError(
                    f"Question '{question_id}' has an invalid language key."
                )

            if language.strip().casefold() not in supported_languages:
                raise QuestionBankError(
                    f"Question '{question_id}' contains unsupported language "
                    f"'{language}'."
                )

            if translated_text is not None and not isinstance(
                translated_text, str
            ):
                raise QuestionBankError(
                    f"Question '{question_id}' has invalid text for "
                    f"language '{language}'. Expected a string or null."
                )

        # Validate answer type.
        raw_answer_type = question.get("answer_type")

        if not isinstance(raw_answer_type, str):
            raise QuestionBankError(
                f"Question '{question_id}' has an invalid answer type."
            )

        answer_type = raw_answer_type.strip().upper()

        if answer_type not in SUPPORTED_ANSWER_TYPES:
            raise QuestionBankError(
                f"Question '{question_id}' has unsupported answer type "
                f"'{raw_answer_type}'."
            )

        # Validate flags.
        if not isinstance(question.get("mandatory"), bool):
            raise QuestionBankError(
                f"Question '{question_id}' must have a boolean 'mandatory' value."
            )

        if not isinstance(question.get("active"), bool):
            raise QuestionBankError(
                f"Question '{question_id}' must have a boolean 'active' value."
            )

        # Validate importance for every question, not just the final one.
        _validate_scoring_importance(question, question_id)

        # Choice-based questions must have valid configured options.
        _validate_question_options(
            question,
            question_id,
            answer_type,
        )

        # Validate optional translation-status metadata.
        translation_status = question.get("translation_status")

        if translation_status is not None:
            if not isinstance(translation_status, dict):
                raise QuestionBankError(
                    f"Question '{question_id}' has invalid "
                    "'translation_status'; expected an object."
                )

            for language, status in translation_status.items():
                if (
                    not isinstance(language, str)
                    or language.strip().casefold() not in supported_languages
                ):
                    raise QuestionBankError(
                        f"Question '{question_id}' has an unsupported "
                        f"translation-status language '{language}'."
                    )

                if (
                    not isinstance(status, str)
                    or status.strip().upper()
                    not in SUPPORTED_TRANSLATION_STATUSES
                ):
                    raise QuestionBankError(
                        f"Question '{question_id}' has an invalid translation "
                        f"status for language '{language}'."
                    )

                if status.strip().upper() == "REVIEWED":
                    translated_text = question_text.get(language)

                    if (
                        not isinstance(translated_text, str)
                        or not translated_text.strip()
                    ):
                        raise QuestionBankError(
                            f"Question '{question_id}' marks language "
                            f"'{language}' as REVIEWED but has no text."
                        )


# ------------------------------------------------------------
# TEMPLATE VALIDATION
# ------------------------------------------------------------

def _validate_templates(data: dict[str, Any]) -> None:
    """Validate reusable question templates."""

    if not isinstance(data, dict):
        raise QuestionBankError(
            "question_templates.json must contain a JSON object."
        )

    _validate_language_configuration(data, "question_templates.json")

    templates = data.get("templates")

    if not isinstance(templates, list):
        raise QuestionBankError(
            "question_templates.json must contain a 'templates' list."
        )

    for index, template in enumerate(templates):
        if not isinstance(template, dict):
            raise QuestionBankError(
                f"Template at index {index} must be a JSON object."
            )

    _validate_unique_ids(
        templates,
        "template_id",
        "question_templates.json",
    )

    for template in templates:
        template_id = template["template_id"].strip()

        missing_fields = REQUIRED_TEMPLATE_FIELDS - template.keys()

        if missing_fields:
            raise QuestionBankError(
                f"Template '{template_id}' is missing fields: "
                f"{sorted(missing_fields)}."
            )

        category = template.get("category")

        if not isinstance(category, str) or not category.strip():
            raise QuestionBankError(
                f"Template '{template_id}' must have a non-empty category."
            )

        answer_type = template.get("answer_type")

        if (
            not isinstance(answer_type, str)
            or answer_type.strip().upper() not in SUPPORTED_ANSWER_TYPES
        ):
            raise QuestionBankError(
                f"Template '{template_id}' has unsupported answer type "
                f"'{answer_type}'."
            )

        if not isinstance(template.get("active"), bool):
            raise QuestionBankError(
                f"Template '{template_id}' must have a boolean 'active' value."
            )

        patterns = template.get("question_pattern")

        if not isinstance(patterns, dict):
            raise QuestionBankError(
                f"Template '{template_id}' must have a "
                "'question_pattern' object."
            )

        english_pattern = patterns.get(DEFAULT_LANGUAGE)

        if not isinstance(english_pattern, str) or not english_pattern.strip():
            raise QuestionBankError(
                f"Template '{template_id}' requires a non-empty English "
                "question pattern."
            )

        for language, pattern in patterns.items():
            if (
                not isinstance(language, str)
                or language.strip().casefold()
                not in {
                    code.strip().casefold()
                    for code in data.get(
                        "supported_languages",
                        [DEFAULT_LANGUAGE],
                    )
                }
            ):
                raise QuestionBankError(
                    f"Template '{template_id}' has unsupported language "
                    f"'{language}'."
                )

            if pattern is not None and not isinstance(pattern, str):
                raise QuestionBankError(
                    f"Template '{template_id}' has invalid pattern for "
                    f"language '{language}'."
                )


def _validate_template_references(
    questions: list[dict[str, Any]],
    templates: list[dict[str, Any]],
) -> None:
    """Ensure every question references an existing template."""

    template_ids = {
        template["template_id"].strip().casefold()
        for template in templates
    }

    for question in questions:
        template_id = question.get("template_id")

        if (
            not isinstance(template_id, str)
            or template_id.strip().casefold() not in template_ids
        ):
            raise QuestionBankError(
                f"Question '{question.get('question_id')}' references "
                f"unknown template '{template_id}'."
            )


# ------------------------------------------------------------
# LANGUAGE RESOLUTION
# ------------------------------------------------------------

def _get_question_text(
    question: dict[str, Any],
    language: str,
) -> tuple[str, str]:
    """
    Return (question_text, actual_language).

    A missing or blank translation falls back to English.
    """

    translations = question["question_text"]
    requested_language = language.strip().casefold()

    for configured_language, text in translations.items():
        if (
            isinstance(configured_language, str)
            and configured_language.strip().casefold() == requested_language
            and isinstance(text, str)
            and text.strip()
        ):
            return text.strip(), configured_language.strip().casefold()

    english_text = translations.get(DEFAULT_LANGUAGE)

    if isinstance(english_text, str) and english_text.strip():
        if requested_language != DEFAULT_LANGUAGE:
            logger.warning(
                "Missing translation: question_id=%s language=%s; "
                "using English fallback.",
                question["question_id"],
                language,
            )

        return english_text.strip(), DEFAULT_LANGUAGE

    raise QuestionBankError(
        f"Question '{question['question_id']}' has no usable translation "
        "in the requested language or English."
    )


def _validate_requested_language(language: str) -> str:
    """Validate and normalize a requested language code."""

    if not isinstance(language, str) or not language.strip():
        raise ValueError("language must be a non-empty string.")

    normalized_language = language.strip().casefold()
    supported_languages = get_available_languages()

    if normalized_language not in {
        code.casefold() for code in supported_languages
    }:
        raise ValueError(
            f"Unsupported language '{language}'. "
            f"Supported languages: {supported_languages}"
        )

    return normalized_language


# ------------------------------------------------------------
# CACHED DATA LOADERS
# ------------------------------------------------------------

@lru_cache(maxsize=1)
def load_question_bank() -> dict[str, Any]:
    """Load and validate question_bank.json."""

    data = _load_json(QUESTION_BANK_PATH)
    _validate_question_bank(data)

    logger.info(
        "HR question bank loaded: %d questions.",
        len(data["questions"]),
    )

    return data


@lru_cache(maxsize=1)
def load_question_templates() -> dict[str, Any]:
    """Load and validate question_templates.json."""

    data = _load_json(QUESTION_TEMPLATES_PATH)
    _validate_templates(data)

    logger.info(
        "HR question templates loaded: %d templates.",
        len(data["templates"]),
    )

    return data


def validate_question_data() -> dict[str, int]:
    """Validate both files and all question-to-template references."""

    bank = load_question_bank()
    template_data = load_question_templates()

    _validate_template_references(
        bank["questions"],
        template_data["templates"],
    )

    # Ensure each question category exists in the template's category.
    template_by_id = {
        template["template_id"].strip().casefold(): template
        for template in template_data["templates"]
    }

    for question in bank["questions"]:
        template = template_by_id[question["template_id"].strip().casefold()]

        if (
            question["category"].strip().casefold()
            != template["category"].strip().casefold()
        ):
            raise QuestionBankError(
                f"Question '{question['question_id']}' and template "
                f"'{question['template_id']}' have different categories."
            )

        if (
            question["answer_type"].strip().upper()
            != template["answer_type"].strip().upper()
        ):
            raise QuestionBankError(
                f"Question '{question['question_id']}' and template "
                f"'{question['template_id']}' have different answer types."
            )

    return {
        "question_count": len(bank["questions"]),
        "template_count": len(template_data["templates"]),
        "role_count": len(bank["roles"]),
        "category_count": len(bank["categories"]),
    }


def clear_question_data_cache() -> None:
    """Clear cached JSON data after configuration files are updated."""

    load_question_bank.cache_clear()
    load_question_templates.cache_clear()

    logger.info("HR screening question data cache cleared.")


# ------------------------------------------------------------
# ROLE / CATEGORY / LANGUAGE LOOKUPS
# ------------------------------------------------------------

def get_available_roles() -> list[Any]:
    """Return configured screening roles."""

    return load_question_bank()["roles"]


def get_available_categories() -> list[Any]:
    """Return configured screening categories."""

    return load_question_bank()["categories"]


def get_available_languages() -> list[str]:
    """Return configured language codes."""

    bank = load_question_bank()
    languages = bank.get("supported_languages", [DEFAULT_LANGUAGE])

    if (
        not isinstance(languages, list)
        or not languages
        or any(
            not isinstance(language, str) or not language.strip()
            for language in languages
        )
    ):
        raise QuestionBankError(
            "'supported_languages' must be a non-empty list of language codes."
        )

    return [language.strip().casefold() for language in languages]


def get_question_templates(
    category: str | None = None,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """
    Return reusable templates for internal configuration.

    Templates should not be exposed directly as candidate questions.
    """

    templates = load_question_templates()["templates"]

    if active_only:
        templates = [
            template for template in templates
            if template["active"] is True
        ]

    if category is not None:
        if not isinstance(category, str) or not category.strip():
            raise ValueError("category must be a non-empty string.")

        templates = [
            template for template in templates
            if template["category"].strip().casefold()
            == category.strip().casefold()
        ]

    return templates


# ------------------------------------------------------------
# QUESTION RETRIEVAL
# ------------------------------------------------------------

def get_question_record(
    question_id: str,
) -> dict[str, Any] | None:
    """
    Return the full internal question record.

    Internal use only: records may contain scoring and evaluation metadata.
    """

    if not isinstance(question_id, str) or not question_id.strip():
        raise ValueError("question_id must be a non-empty string.")

    normalized_id = question_id.strip().casefold()
    bank = load_question_bank()

    for question in bank["questions"]:
        if question["question_id"].strip().casefold() == normalized_id:
            return question

    return None

def _get_localized_options(
    question: dict[str, Any],
    language: str,
) -> list[Any] | None:
    """Return candidate-facing options in the requested language."""

    options = question.get("options", question.get("choices"))

    if options is None:
        return None

    if not isinstance(options, list):
        raise QuestionBankError(
            f"Question '{question.get('question_id')}' "
            "has invalid options."
        )

    localized_options: list[Any] = []

    for option in options:
        # Support legacy string options.
        if isinstance(option, str):
            localized_options.append(option)
            continue

        if not isinstance(option, dict):
            raise QuestionBankError(
                f"Question '{question.get('question_id')}' "
                "contains an invalid option."
            )

        option_id = (
            option.get("option_id")
            or option.get("id")
            or option.get("value")
        )

        translations = option.get("label_translations", {})
        if not isinstance(translations, dict):
            translations = {}

        label = translations.get(language)

        if not isinstance(label, str) or not label.strip():
            label = translations.get(DEFAULT_LANGUAGE)

        if not isinstance(label, str) or not label.strip():
            label = option.get("label")

        if not isinstance(label, str) or not label.strip():
            raise QuestionBankError(
                f"Question '{question.get('question_id')}' "
                f"has an option without a usable label."
            )

        # Expose only fields needed to render a candidate selection.
        localized_option: dict[str, Any] = {
            "label": label.strip(),
        }

        if isinstance(option_id, str) and option_id.strip():
            localized_option["option_id"] = option_id.strip()

        localized_options.append(localized_option)

    return localized_options

def _candidate_question_payload(
    question: dict[str, Any],
    language: str,
) -> dict[str, Any]:
    """Build a candidate-safe question response in the requested language."""

    text, actual_language = _get_question_text(question, language)

    payload = {
        "question_id": question["question_id"],
        "role_id": question["role_id"],
        "category": question["category"],
        "question_text": text,
        "language": actual_language,
        "requested_language": language,
        "translation_fallback": actual_language != language,
        "answer_type": question["answer_type"],
        "mandatory": question["mandatory"],
    }

    options = _get_localized_options(question, language)

    if options is not None:
        payload["options"] = options

    # Do not expose scoring importance, evaluation rubrics,
    # correct answers, or translation review metadata.

    return payload

def get_candidate_questions(
    role_id: str,
    language: str = DEFAULT_LANGUAGE,
    category: str | None = None,
    include_optional: bool = True,
) -> list[dict[str, Any]]:
    """Retrieve active, candidate-facing questions for a role."""

    if not isinstance(role_id, str) or not role_id.strip():
        raise ValueError("role_id must be a non-empty string.")

    normalized_role_id = role_id.strip().casefold()
    normalized_language = _validate_requested_language(language)

    bank = load_question_bank()

    known_roles = {
        _get_configured_id(role, "role_id").casefold()
        for role in bank["roles"]
    }

    if normalized_role_id not in known_roles:
        raise ValueError(f"Unknown role_id: '{role_id}'.")

    normalized_category = None

    if category is not None:
        if not isinstance(category, str) or not category.strip():
            raise ValueError("category must be a non-empty string.")

        normalized_category = category.strip().casefold()

        known_categories = {
            _get_configured_id(item, "category_id").casefold()
            for item in bank["categories"]
        }

        if normalized_category not in known_categories:
            raise ValueError(f"Unknown question category: '{category}'.")

    results: list[dict[str, Any]] = []

    for question in bank["questions"]:
        if question["role_id"].strip().casefold() != normalized_role_id:
            continue

        if question["active"] is not True:
            continue

        if (
            normalized_category is not None
            and question["category"].strip().casefold()
            != normalized_category
        ):
            continue

        if not include_optional and question["mandatory"] is not True:
            continue

        results.append(
            _candidate_question_payload(question, normalized_language)
        )

    return results


def get_candidate_question(
    question_id: str,
    language: str = DEFAULT_LANGUAGE,
) -> dict[str, Any] | None:
    """Retrieve one active question in candidate-facing format."""

    normalized_language = _validate_requested_language(language)
    question = get_question_record(question_id)

    if question is None or question["active"] is not True:
        return None

    return _candidate_question_payload(question, normalized_language)
