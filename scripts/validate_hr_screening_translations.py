
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

BANK_FILE = PROJECT_ROOT / "data"/"hr_screening"/"question_bank_multilingual.json"
TEMPLATES_FILE = PROJECT_ROOT / "data"/"hr_screening"/ "question_templates_multilingual.json"

LANGUAGES = ("ml", "hi")


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def validate_question_bank(data: dict) -> None:
    questions = data.get("questions", [])
    assert questions, "No questions found."

    ids = [q.get("question_id") for q in questions]
    assert len(ids) == len(set(ids)), "Duplicate question IDs found."

    missing = []

    for question in questions:
        qid = question.get("question_id", "UNKNOWN")
        translations = question.get("question_text", {})

        for language in LANGUAGES:
            value = translations.get(language)
            if not isinstance(value, str) or not value.strip():
                missing.append(f"{qid}: question_text.{language}")

        for option in question.get("options", []):
            for language in LANGUAGES:
                labels = option.get("label_translations", {})
                value = labels.get(language)

                if not isinstance(value, str) or not value.strip():
                    missing.append(
                        f"{qid}/{option.get('option_id')}: "
                        f"label_translations.{language}"
                    )

    if missing:
        print("Missing translations:")
        for item in missing:
            print(f" - {item}")
        raise ValueError(f"{len(missing)} translation fields need attention.")

    print(f"Question bank valid: {len(questions)} questions.")
    print(f"Unique question IDs: {len(set(ids))}.")


def validate_templates(data: dict) -> None:
    # Check the generated template JSON is valid and contains templates.
    templates = data.get("templates", data.get("question_templates", []))

    if not templates:
        print(
            "WARNING: Could not find a 'templates' or "
            "'question_templates' list. Check the template JSON structure."
        )
        return

    print(f"Template JSON loaded: {len(templates)} templates.")


def main():
    bank = load_json(BANK_FILE)
    templates = load_json(TEMPLATES_FILE)

    validate_question_bank(bank)
    validate_templates(templates)

    print("Validation completed.")


if __name__ == "__main__":
    main()
