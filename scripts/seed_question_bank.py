"""
Seed the ZechPath PostgreSQL questions table from question_bank_multilingual.json.

Requirements:
    pip install psycopg2-binary

PowerShell example:
    $env:ZECHPATH_DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/zechpath_screening"
    python seed_question_bank.py --json question_bank_multilingual.json

This script:
- validates the multilingual JSON before writing anything;
- inserts one row per question per language (56 logical questions x 3 languages = 168 rows);
- lets PostgreSQL generate question_pk;
- maps answer_type to question_type;
- preserves additional source metadata in a JSONB column;
- safely re-runs using ON CONFLICT (question_id, language) DO UPDATE;
- runs schema change and inserts in one transaction.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import psycopg2
from psycopg2.extras import Json


EXTRA_METADATA_FIELDS = (
    "template_id",
    "translation_status",
    "scoring_importance",
    "evaluation_type",
    "version",
    "options",
    "evaluation_criteria",
    "max_score",
)


def load_and_validate(path: Path) -> tuple[dict, list[dict]]:
    with path.open("r", encoding="utf-8") as handle:
        bank = json.load(handle)

    languages = bank.get("supported_languages")
    questions = bank.get("questions")

    if not isinstance(languages, list) or not languages:
        raise ValueError("JSON must contain a non-empty supported_languages list.")
    if not isinstance(questions, list) or not questions:
        raise ValueError("JSON must contain a non-empty questions list.")

    required = ("question_id", "role_id", "category", "question_text",
                "answer_type", "mandatory", "active")
    seen_ids = set()
    rows = []

    for index, question in enumerate(questions, start=1):
        missing = [key for key in required if key not in question]
        if missing:
            raise ValueError(
                f"Question #{index} is missing required fields: {', '.join(missing)}"
            )

        question_id = question["question_id"]
        if not question_id or question_id in seen_ids:
            raise ValueError(f"Blank or duplicate question_id: {question_id!r}")
        seen_ids.add(question_id)

        text_by_language = question["question_text"]
        for language in languages:
            text = text_by_language.get(language)
            if not isinstance(text, str) or not text.strip():
                raise ValueError(
                    f"{question_id} has missing/blank question_text for language "
                    f"{language!r}. No database changes were made."
                )

            metadata = {
                key: question[key]
                for key in EXTRA_METADATA_FIELDS
                if key in question
            }
            # Keep the language-specific translation status alongside each row.
            translation_status = question.get("translation_status", {})
            if isinstance(translation_status, dict) and language in translation_status:
                metadata["translation_status"] = translation_status[language]
            metadata["source_schema_version"] = bank.get("schema_version", "unknown")

            rows.append({
                "question_id": question_id,
                "role_id": question["role_id"],
                "category": question["category"],
                "language": language,
                "question_text": text,
                "question_type": question["answer_type"],
                "is_mandatory": bool(question["mandatory"]),
                "is_active": bool(question["active"]),
                "metadata": metadata,
            })

    expected = len(questions) * len(languages)
    if len(rows) != expected:
        raise ValueError(f"Expected {expected} language rows but prepared {len(rows)}.")

    return bank, rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Load multilingual HR questions into PostgreSQL.")
    parser.add_argument("--json", required=True, help="Path to question_bank_multilingual.json")
    args = parser.parse_args()

    database_url = os.environ.get("ZECHPATH_DATABASE_URL")
    if not database_url:
        print(
            "ERROR: ZECHPATH_DATABASE_URL is not set.\n"
            "Set it in PowerShell before running this script.",
            file=sys.stderr,
        )
        return 2

    json_path = Path(args.json)
    if not json_path.is_file():
        print(f"ERROR: JSON file not found: {json_path}", file=sys.stderr)
        return 2

    try:
        bank, rows = load_and_validate(json_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"VALIDATION FAILED: {exc}", file=sys.stderr)
        return 2

    print(f"Validated {len(bank['questions'])} logical questions.")
    print(f"Languages: {', '.join(bank['supported_languages'])}")
    print(f"Prepared {len(rows)} language-specific rows.")
    print("Connecting to PostgreSQL...")

    insert_sql = """
        INSERT INTO public.questions (
            question_id,
            role_id,
            category,
            language,
            question_text,
            question_type,
            is_mandatory,
            is_active,
            metadata
        )
        VALUES (
            %(question_id)s,
            %(role_id)s,
            %(category)s,
            %(language)s,
            %(question_text)s,
            %(question_type)s,
            %(is_mandatory)s,
            %(is_active)s,
            %(metadata)s
        )
        ON CONFLICT (question_id, language)
        DO UPDATE SET
            role_id = EXCLUDED.role_id,
            category = EXCLUDED.category,
            question_text = EXCLUDED.question_text,
            question_type = EXCLUDED.question_type,
            is_mandatory = EXCLUDED.is_mandatory,
            is_active = EXCLUDED.is_active,
            metadata = EXCLUDED.metadata;
    """

    try:
        with psycopg2.connect(database_url) as connection:
            with connection.cursor() as cursor:
                # Preserve question-bank fields that do not have dedicated SQL columns.
                cursor.execute("""
                    ALTER TABLE public.questions
                    ADD COLUMN IF NOT EXISTS metadata JSONB
                    NOT NULL DEFAULT '{}'::jsonb;
                """)

                for row in rows:
                    row["metadata"] = Json(row["metadata"])
                    cursor.execute(insert_sql, row)

                cursor.execute("""
                    SELECT language, COUNT(*)
                    FROM public.questions
                    GROUP BY language
                    ORDER BY language;
                """)
                counts = cursor.fetchall()

                cursor.execute("SELECT COUNT(*) FROM public.questions;")
                total = cursor.fetchone()[0]

        print("\nMigration completed successfully.")
        print(f"Total rows now in public.questions: {total}")
        print("Rows by language:")
        for language, count in counts:
            print(f"  {language}: {count}")
        print("\nNext: verify question_pk and language rows in pgAdmin.")
        return 0

    except Exception as exc:
        print(f"\nDATABASE MIGRATION FAILED: {exc}", file=sys.stderr)
        print("The transaction was rolled back; fix the reported issue before retrying.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
