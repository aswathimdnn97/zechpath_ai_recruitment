"""
PHASE 5 - TEXT NORMALIZATION VALIDATION

Validation flow:

PDF
 ↓
PyMuPDF
 ↓
clean_text()
 ↓
fix_layout()
 ↓
text_reconstructor()
 ↓
normalize_text()

Purpose:
    Validate that normalize_text() correctly:
        - removes unnecessary whitespace
        - removes bullet markers
        - normalizes known headings
        - preserves meaningful resume content
        - preserves technical terms
        - preserves contact information
        - does not unexpectedly modify normal content
"""

import re
import sys
import time
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORTS
# ============================================================

from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import clean_text
from document_processing.common.handling_layout import fix_layout
from document_processing.resume.text_reconstruction import (
    text_reconstructor,
)
from document_processing.resume.resume_normalizer import (
    normalize_text,
)


# ============================================================
# TEST DIRECTORY
# ============================================================

TEST_FOLDER = (
    PROJECT_ROOT
    / "data"
    / "validation"
    / "edge_case_resumes"
)


# ============================================================
# REGEX HELPERS
# ============================================================

REPLACEMENT_CHAR = "\ufffd"

CONTROL_CHAR_PATTERN = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]"
)

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+"
    r"@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:\+?\d[\d\s().-]{7,}\d)"
    r"(?!\d)"
)

DATE_PATTERN = re.compile(
    r"\b"
    r"(?:"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|"
    r"\d{4}[/-]\d{1,2}[/-]\d{1,2}"
    r"|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"[a-z]*\s+\d{4}"
    r"|"
    r"\d{4}"
    r")"
    r"\b",
    re.IGNORECASE,
)


# ============================================================
# TEST TERMS
# ============================================================

IMPORTANT_TERMS = [
    "python",
    "java",
    "javascript",
    "react",
    "django",
    "fastapi",
    "mysql",
    "mongodb",
    "docker",
    "git",
    "github",
    "sql",
    "machine learning",
    "tensorflow",
    "pandas",
    "numpy",
]


# ============================================================
# BASIC HELPERS
# ============================================================

def count_words(text):
    """
    Count words using a resume-friendly token pattern.
    """

    if not text:
        return 0

    return len(
        re.findall(
            r"\b[\w.+#/-]+\b",
            text
        )
    )


def count_replacement_chars(text):
    return text.count(REPLACEMENT_CHAR)


def count_control_chars(text):
    return len(
        CONTROL_CHAR_PATTERN.findall(text)
    )


def has_excessive_blank_lines(text):
    if not text:
        return False

    return bool(
        re.search(
            r"\n\s*\n\s*\n\s*\n",
            text
        )
    )


def extract_emails(text):
    return set(
        EMAIL_PATTERN.findall(text or "")
    )


def extract_phones(text):
    return set(
        PHONE_PATTERN.findall(text or "")
    )


def extract_dates(text):
    return set(
        DATE_PATTERN.findall(text or "")
    )


def normalize_for_comparison(value):
    """
    Normalize text for preservation comparisons.

    This intentionally ignores:
        - case
        - repeated whitespace
        - bullet symbols
        - common heading separators
    """

    if not value:
        return ""

    value = value.lower()

    value = re.sub(
        r"[•●◦▪■‣⁃]",
        " ",
        value
    )

    value = re.sub(
        r"[-_/]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def contains_term(text, term):
    """
    Case-insensitive content check.
    """

    return term.lower() in text.lower()


# ============================================================
# PRESERVATION CHECKS
# ============================================================

def check_emails_preserved(
    before,
    after
):
    before_emails = extract_emails(before)
    after_emails = extract_emails(after)

    return before_emails.issubset(
        after_emails
    )


def check_phones_preserved(
    before,
    after
):
    before_phones = extract_phones(before)

    if not before_phones:
        return True

    after_phones = extract_phones(after)

    # Phone extraction can differ slightly because
    # whitespace/punctuation normalization is allowed.
    for phone in before_phones:

        digits = re.sub(
            r"\D",
            "",
            phone
        )

        if len(digits) < 8:
            continue

        if digits not in re.sub(
            r"\D",
            "",
            after
        ):
            return False

    return True


def check_dates_preserved(
    before,
    after
):
    before_dates = extract_dates(before)

    if not before_dates:
        return True

    after_normalized = after.lower()

    for date in before_dates:

        if date.lower() not in after_normalized:
            # Four-digit years can be normalized safely,
            # so check the numeric content as fallback.
            numeric_date = re.sub(
                r"\D",
                "",
                date
            )

            if numeric_date and numeric_date not in re.sub(
                r"\D",
                "",
                after
            ):
                return False

    return True


def check_important_terms(
    before,
    after
):
    """
    Ensure important technical terms that existed in the
    input are still present after normalization.

    Only terms present in the input are checked.
    """

    missing = []

    for term in IMPORTANT_TERMS:

        if not contains_term(before, term):
            continue

        if not contains_term(after, term):
            missing.append(term)

    return missing


# ============================================================
# BULLET VALIDATION
# ============================================================

def count_bullet_lines(text):
    if not text:
        return 0

    count = 0

    for line in text.splitlines():

        if re.match(
            r"^\s*[•●◦▪■‣⁃*-]\s+",
            line
        ):
            count += 1

    return count


def bullet_removal_correct(
    before,
    after
):
    """
    The normalizer is expected to remove bullet markers.

    Therefore:
        bullets before > 0
        bullets after == 0

    is considered correct.
    """

    before_count = count_bullet_lines(before)
    after_count = count_bullet_lines(after)

    if before_count == 0:
        return True

    return after_count == 0


# ============================================================
# HEADING VALIDATION
# ============================================================

def get_heading_map():
    """
    Load the actual heading aliases used by normalize_text().
    """

    try:

        from document_processing.resume.headings import (
            heading_aliases
        )

    except Exception:
        return {}

    return {
        str(alias).strip().lower(): canonical
        for alias, canonical
        in heading_aliases.items()
    }


def check_heading_normalization(
    before,
    after
):
    """
    Validate that recognized heading aliases become their
    configured canonical headings.

    Only exact standalone lines are tested.
    """

    heading_map = get_heading_map()

    if not heading_map:
        return True, []

    errors = []

    after_lines = {
        line.strip().lower()
        for line in after.splitlines()
        if line.strip()
    }

    for alias, canonical in heading_map.items():

        alias_normalized = alias.strip().lower()
        canonical_normalized = (
            str(canonical)
            .strip()
            .lower()
        )

        # Only test aliases that actually appear as
        # standalone lines in the input.
        for line in before.splitlines():

            if (
                line.strip().lower()
                != alias_normalized
            ):
                continue

            if canonical_normalized not in after_lines:

                errors.append(
                    f"{alias} -> {canonical}"
                )

    return (
        len(errors) == 0,
        errors
    )


# ============================================================
# TEXT CHANGE ANALYSIS
# ============================================================

def get_normalized_token_set(text):
    if not text:
        return set()

    tokens = re.findall(
        r"\b[\w.+#/-]+\b",
        text.lower()
    )

    return set(tokens)


def get_missing_tokens(
    before,
    after
):
    before_tokens = get_normalized_token_set(
        before
    )

    after_tokens = get_normalized_token_set(
        after
    )

    return sorted(
        before_tokens - after_tokens
    )


# ============================================================
# VALIDATE ONE PDF
# ============================================================

def validate_pdf(pdf_path):

    start_time = time.perf_counter()

    raw_text = extract_raw_text(
        str(pdf_path)
    )

    if not raw_text.strip():

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print(
            f"PDF                 : {pdf_path.name}"
        )

        print(
            "Status              : OCR_REQUIRED"
        )

        print(
            f"Time                : {elapsed:.4f} sec"
        )

        print(
            "Raw characters      : 0"
        )

        print(
            "Normalized          : 0"
        )

        print("-" * 70)

        return "OCR_REQUIRED"

    # ========================================================
    # PHASE 2
    # ========================================================

    cleaned = clean_text(
        raw_text
    )

    # ========================================================
    # PHASE 3
    # ========================================================

    layout_text = fix_layout(
        cleaned
    )

    # ========================================================
    # PHASE 4
    # ========================================================

    reconstructed = text_reconstructor(
        layout_text
    )

    # ========================================================
    # PHASE 5
    # ========================================================

    normalized = normalize_text(
        reconstructed
    )

    elapsed = (
        time.perf_counter()
        - start_time
    )

    # ========================================================
    # BASIC METRICS
    # ========================================================

    layout_chars = len(
        reconstructed
    )

    normalized_chars = len(
        normalized
    )

    layout_words = count_words(
        reconstructed
    )

    normalized_words = count_words(
        normalized
    )

    layout_lines = len(
        reconstructed.splitlines()
    )

    normalized_lines = len(
        normalized.splitlines()
    )

    # ========================================================
    # RETENTION
    # ========================================================

    layout_tokens = get_normalized_token_set(
        reconstructed
    )

    normalized_tokens = get_normalized_token_set(
        normalized
    )

    if layout_tokens:

        token_retention = (
            len(
                layout_tokens
                & normalized_tokens
            )
            / len(layout_tokens)
            * 100
        )

    else:
        token_retention = 100.0

    # ========================================================
    # QUALITY
    # ========================================================

    replacement_chars = (
        count_replacement_chars(normalized)
    )

    control_chars = (
        count_control_chars(normalized)
    )

    excessive_blank_lines = (
        has_excessive_blank_lines(normalized)
    )

    # ========================================================
    # PRESERVATION
    # ========================================================

    email_preserved = (
        check_emails_preserved(
            reconstructed,
            normalized
        )
    )

    phone_preserved = (
        check_phones_preserved(
            reconstructed,
            normalized
        )
    )

    dates_preserved = (
        check_dates_preserved(
            reconstructed,
            normalized
        )
    )

    important_missing = (
        check_important_terms(
            reconstructed,
            normalized
        )
    )

    bullets_correct = (
        bullet_removal_correct(
            reconstructed,
            normalized
        )
    )

    headings_ok, heading_errors = (
        check_heading_normalization(
            reconstructed,
            normalized
        )
    )

    missing_tokens = get_missing_tokens(
        reconstructed,
        normalized
    )

    # ========================================================
    # EXPECTED CHANGES
    # ========================================================

    text_changed = (
        reconstructed != normalized
    )

    # ========================================================
    # STATUS
    # ========================================================

    failures = []

    if replacement_chars > 0:
        failures.append(
            "replacement characters"
        )

    if control_chars > 0:
        failures.append(
            "control characters"
        )

    if excessive_blank_lines:
        failures.append(
            "excessive blank lines"
        )

    if token_retention < 99.0:
        failures.append(
            "low token retention"
        )

    if not email_preserved:
        failures.append(
            "email not preserved"
        )

    if not phone_preserved:
        failures.append(
            "phone not preserved"
        )

    if not dates_preserved:
        failures.append(
            "date not preserved"
        )

    if not bullets_correct:
        failures.append(
            "bullet normalization failed"
        )

    if not headings_ok:
        failures.append(
            "heading normalization failed"
        )

    if important_missing:
        failures.append(
            "important terms missing"
        )

    status = (
        "FAIL"
        if failures
        else "PASS"
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    print(
        f"PDF                 : {pdf_path.name}"
    )

    print(
        f"Status              : {status}"
    )

    print(
        f"Time                : {elapsed:.4f} sec"
    )

    print()

    print(
        "TEXT_RECONSTRUCTOR -> NORMALIZE_TEXT"
    )

    print("-" * 70)

    print(
        f"Reconstructed characters : {layout_chars}"
    )

    print(
        f"Normalized characters    : {normalized_chars}"
    )

    print(
        f"Reconstructed words      : {layout_words}"
    )

    print(
        f"Normalized words         : {normalized_words}"
    )

    print(
        f"Reconstructed lines      : {layout_lines}"
    )

    print(
        f"Normalized lines         : {normalized_lines}"
    )

    print()

    print("NORMALIZATION QUALITY")

    print("-" * 70)

    print(
        f"Token retention          : "
        f"{token_retention:.2f}%"
    )

    print(
        f"Replacement characters   : "
        f"{replacement_chars}"
    )

    print(
        f"Control characters      : "
        f"{control_chars}"
    )

    print(
        f"Excessive blank lines    : "
        f"{excessive_blank_lines}"
    )

    print(
        f"Text changed             : "
        f"{text_changed}"
    )

    print()

    print("CONTENT PRESERVATION")

    print("-" * 70)

    print(
        f"Email preserved          : "
        f"{email_preserved}"
    )

    print(
        f"Phone preserved          : "
        f"{phone_preserved}"
    )

    print(
        f"Dates preserved          : "
        f"{dates_preserved}"
    )

    print(
        f"Important terms          : "
        f"{not bool(important_missing)}"
    )

    print(
        f"Bullet normalization     : "
        f"{bullets_correct}"
    )

    print(
        f"Heading normalization    : "
        f"{headings_ok}"
    )

    print()

    print("NORMALIZATION SAFETY")

    print("-" * 70)

    print(
        f"Missing token types      : "
        f"{len(missing_tokens)}"
    )

    print(
        f"Missing tokens           : "
        f"{missing_tokens}"
    )

    print(
        f"Heading errors           : "
        f"{heading_errors}"
    )

    print("-" * 70)

    return status


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)

    print(
        "PHASE 5 - TEXT NORMALIZATION VALIDATION"
    )

    print("=" * 70)

    print()

    print(
        "Validation stages:"
    )

    print(
        "PDF -> PyMuPDF -> clean_text() "
        "-> fix_layout() -> text_reconstructor() "
        "-> normalize_text()"
    )

    print()

    print(
        "Test folder:"
    )

    print(
        TEST_FOLDER
    )

    print("-" * 70)

    if not TEST_FOLDER.exists():

        print(
            "ERROR: Test folder does not exist."
        )

        return

    pdf_files = sorted(
        TEST_FOLDER.glob("*.pdf")
    )

    if not pdf_files:

        print(
            "ERROR: No PDF files found."
        )

        return

    results = []

    for pdf_file in pdf_files:

        status = validate_pdf(
            pdf_file
        )

        results.append(
            (
                pdf_file.name,
                status
            )
        )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()

    print("=" * 70)

    print(
        "PHASE 5 - TEXT NORMALIZATION "
        "VALIDATION SUMMARY"
    )

    print("=" * 70)

    print(
        f"{'PDF':35}"
        f"{'Status':18}"
    )

    print("-" * 70)

    for name, status in results:

        print(
            f"{name:35}"
            f"{status:18}"
        )

    print("-" * 70)

    total = len(results)

    passed = sum(
        status == "PASS"
        for _, status in results
    )

    failed = sum(
        status == "FAIL"
        for _, status in results
    )

    ocr_required = sum(
        status == "OCR_REQUIRED"
        for _, status in results
    )

    print(
        f"Total PDFs          : {total}"
    )

    print(
        f"PASS                : {passed}"
    )

    print(
        f"FAIL                : {failed}"
    )

    print(
        f"OCR_REQUIRED        : {ocr_required}"
    )

    print()

    if failed == 0:

        print(
            "PHASE 5 STATUS : PASS"
        )

        print()

        print(
            "normalize_text() "
            "validation passed."
        )

        print(
            "Next stage: section detection validation."
        )

    else:

        print(
            "PHASE 5 STATUS : FAIL"
        )

        print()

        print(
            "Review normalization failures "
            "before continuing."
        )


if __name__ == "__main__":
    main()