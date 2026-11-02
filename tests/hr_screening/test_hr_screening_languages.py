"""
Compact multilingual question-bank smoke test.

Run from the ZechPath project root:
    python scripts/test_hr_screening_languages.py

Checks English, Malayalam, and Hindi question retrieval for
PYTHON_DEV_FRESHER.
"""

from api.service.question_bank_service import (
    get_available_languages,
    get_candidate_questions,
)

ROLE_ID = "PYTHON_DEV_FRESHER"
EXPECTED_LANGUAGES = ("en", "ml", "hi")


def main() -> None:
    available_languages = get_available_languages()
    print("Available languages:", available_languages)

    missing_languages = set(EXPECTED_LANGUAGES) - set(available_languages)
    assert not missing_languages, (
        f"Missing expected languages: {sorted(missing_languages)}"
    )

    for language in EXPECTED_LANGUAGES:
        questions = get_candidate_questions(
            role_id=ROLE_ID,
            language=language,
        )

        assert questions, f"No questions returned for language={language}"

        wrong_language = [
            question.get("question_id", "<unknown>")
            for question in questions
            if question.get("language") != language
        ]
        assert not wrong_language, (
            f"Questions returned with an unexpected language for "
            f"{language}: {wrong_language}"
        )

        fallback_count = sum(
            bool(question.get("translation_fallback", False))
            for question in questions
        )

        print(
            f"PASS | role={ROLE_ID} | language={language} | "
            f"count={len(questions)} | fallbacks={fallback_count}"
        )

    print("All multilingual smoke tests passed.")


if __name__ == "__main__":
    main()
