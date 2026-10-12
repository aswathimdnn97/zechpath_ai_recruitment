"""
RESUME PIPELINE VALIDATION

Current validation flow:

    PDF
      |
      v
    PyMuPDF
      |
      v
    clean_text()
      |
      v
    fix_layout()
      |
      v
    text_reconstructor()

Current validation focus:
    Phase 2 - clean_text()
    Phase 3 - fix_layout()

The text_reconstructor() stage is included as an optional next-stage
hook but is NOT executed until explicitly enabled.

Test PDFs:
    - bullet_heavy.pdf
    - image_resume.pdf
    - multi_page.pdf
    - table_resume.pdf
    - two_column.pdf
"""

from __future__ import annotations

import inspect
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


# ============================================================================
# WINDOWS-SAFE CONSOLE
# ============================================================================

try:
    sys.stdout.reconfigure(
        encoding="utf-8",
        errors="replace",
    )
    sys.stderr.reconfigure(
        encoding="utf-8",
        errors="replace",
    )
except Exception:
    pass


# ============================================================================
# PROJECT ROOT
# ============================================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# PRODUCTION IMPORTS
# ============================================================================

from parsers.pdf_reader import read_pdf
from document_processing.common.cleaner import clean_text
from document_processing.common.handling_layout import fix_layout


# ============================================================================
# CONFIGURATION
# ============================================================================

TEST_PDF_FOLDER = (
    PROJECT_ROOT
    / "data"
    / "validation"
    / "edge_case_resumes"
)

TEST_FILES = [
    "bullet_heavy.pdf",
    "image_resume.pdf",
    "multi_page.pdf",
    "table_resume.pdf",
    "two_column.pdf",
]

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

CLEAN_TOKEN_RETENTION_THRESHOLD = 95.0

LAYOUT_TOKEN_RETENTION_THRESHOLD = 95.0

LAYOUT_CHAR_RETENTION_THRESHOLD = 90.0

MAX_EXCESSIVE_BLANK_LINES = 3

# A large unexpected line expansion can indicate accidental splitting.
MAX_LINE_EXPANSION_RATIO = 2.0


# ============================================================================
# COMMON RESUME TERMS
# ============================================================================

IMPORTANT_TERMS = [
    "experience",
    "education",
    "skills",
    "projects",
    "certifications",
    "python",
    "java",
]


# ============================================================================
# TEXT HELPERS
# ============================================================================

def normalize_tokens(text: str) -> List[str]:
    """
    Convert text into normalized tokens.

    Token comparison is used instead of exact string comparison because
    clean_text() and fix_layout() are allowed to change whitespace.
    """
    if not isinstance(text, str):
        return []

    return re.findall(
        r"\b[\w.+#/@-]+\b",
        text.lower(),
        flags=re.UNICODE,
    )


def count_words(text: str) -> int:
    return len(normalize_tokens(text))


def count_lines(text: str) -> int:
    if not text:
        return 0

    return len(text.splitlines())


def count_replacement_chars(text: str) -> int:
    """
    Count Unicode replacement characters without printing them.
    """
    if not isinstance(text, str):
        return 0

    return text.count("\ufffd")


def count_control_chars(text: str) -> int:
    """
    Count unexpected control characters.

    Newline, carriage return and tab are allowed.
    """
    if not isinstance(text, str):
        return 0

    count = 0

    for char in text:
        code = ord(char)

        if code < 32 and char not in ("\n", "\r", "\t"):
            count += 1

    return count


def count_excessive_blank_lines(text: str) -> int:
    """
    Count groups containing more than one consecutive blank line.
    """
    if not text:
        return 0

    matches = re.findall(
        r"\n[ \t]*\n(?:[ \t]*\n)+",
        text,
    )

    return len(matches)


def token_retention(before: str, after: str) -> float:
    """
    Calculate occurrence-aware token retention.

    Example:
        before = "Python Python Django"
        after  = "Python Django"

    Only 2 of the 3 token occurrences are retained.
    """
    before_tokens = normalize_tokens(before)
    after_tokens = normalize_tokens(after)

    if not before_tokens:
        return 100.0 if not after_tokens else 0.0

    after_counts: Dict[str, int] = {}

    for token in after_tokens:
        after_counts[token] = (
            after_counts.get(token, 0) + 1
        )

    matched = 0

    for token in before_tokens:
        if after_counts.get(token, 0) > 0:
            matched += 1
            after_counts[token] -= 1

    return (
        matched / len(before_tokens)
    ) * 100.0


def character_retention(
    before: str,
    after: str,
) -> float:
    """
    Approximate character retention.
    """
    before_length = len(before or "")

    if before_length == 0:
        return 100.0 if not after else 0.0

    return (
        len(after or "")
        / before_length
    ) * 100.0


def find_missing_tokens(
    before: str,
    after: str,
    limit: int = 20,
) -> List[str]:
    """
    Find unique tokens present before but absent afterwards.

    This is diagnostic only.
    """
    before_tokens = normalize_tokens(before)
    after_tokens = set(
        normalize_tokens(after)
    )

    missing: List[str] = []

    for token in before_tokens:
        if token not in after_tokens:
            if token not in missing:
                missing.append(token)

        if len(missing) >= limit:
            break

    return missing


# ============================================================================
# CONTACT INFORMATION CHECKS
# ============================================================================

EMAIL_PATTERN = re.compile(
    r"\b"
    r"[A-Za-z0-9._%+-]+"
    r"@"
    r"[A-Za-z0-9.-]+"
    r"\."
    r"[A-Za-z]{2,}"
    r"\b"
)


def extract_emails(text: str) -> List[str]:
    return EMAIL_PATTERN.findall(
        text or ""
    )


def emails_preserved(
    before: str,
    after: str,
) -> bool:
    emails = extract_emails(before)

    if not emails:
        return True

    after_lower = (after or "").lower()

    return all(
        email.lower() in after_lower
        for email in emails
    )


def extract_phone_candidates(
    text: str,
) -> List[str]:
    """
    Extract likely phone numbers.

    This is intentionally permissive because resumes contain
    different phone-number formats.
    """
    matches = re.findall(
        r"(?<!\w)"
        r"(?:\+?\d[\d\s().-]{7,}\d)"
        r"(?!\w)",
        text or "",
    )

    return [
        re.sub(
            r"\s+",
            " ",
            value,
        ).strip()
        for value in matches
    ]


def phones_preserved(
    before: str,
    after: str,
) -> bool:
    phones = extract_phone_candidates(
        before
    )

    if not phones:
        return True

    after_text = after or ""
    after_digits = re.sub(
        r"\D",
        "",
        after_text,
    )

    for phone in phones:
        phone_digits = re.sub(
            r"\D",
            "",
            phone,
        )

        if not phone_digits:
            continue

        if phone_digits not in after_digits:
            return False

    return True


# ============================================================================
# BULLET CHECKS
# ============================================================================

BULLET_PREFIX_PATTERN = re.compile(
    r"^\s*"
    r"(?:"
    r"[•●▪◦‣⁃∙·*➢➤►▸-]"
    r")"
    r"\s+"
)


def count_bullets(text: str) -> int:
    if not text:
        return 0

    count = 0

    for line in text.splitlines():
        if BULLET_PREFIX_PATTERN.match(line):
            count += 1

    return count


def bullets_preserved(
    before: str,
    after: str,
) -> bool:
    before_count = count_bullets(before)
    after_count = count_bullets(after)

    if before_count == 0:
        return True

    # Allow up to two bullets to disappear because layout normalization
    # can legitimately convert a wrapped bullet into a reconstructed line.
    return after_count >= max(
        0,
        before_count - 2,
    )


# ============================================================================
# HEADING CHECKS
# ============================================================================

DEFAULT_HEADINGS = {
    "summary",
    "professional summary",
    "profile",
    "objective",
    "career objective",
    "skills",
    "technical skills",
    "technical skill",
    "key skills",
    "core skills",
    "technical competencies",
    "experience",
    "work experience",
    "professional experience",
    "employment",
    "employment history",
    "work history",
    "education",
    "educational qualifications",
    "academic qualifications",
    "academic background",
    "certifications",
    "certificates",
    "projects",
    "project",
    "achievements",
    "awards",
    "languages",
    "interests",
    "hobbies",
    "contact",
    "contact information",
    "personal information",
    "references",
}


def find_headings(
    text: str,
) -> List[str]:
    """
    Find known headings that appear as standalone lines.
    """
    if not text:
        return []

    found = []

    for line in text.splitlines():
        normalized = line.strip().lower()

        if normalized in DEFAULT_HEADINGS:
            if normalized not in found:
                found.append(normalized)

    return found


def headings_preserved(
    before: str,
    after: str,
) -> bool:
    before_headings = find_headings(
        before
    )

    if not before_headings:
        return True

    after_lower = {
        line.strip().lower()
        for line in (after or "").splitlines()
    }

    return all(
        heading in after_lower
        for heading in before_headings
    )


# ============================================================================
# DATE CHECKS
# ============================================================================

DATE_PATTERN = re.compile(
    r"""
    (?:
        \b\d{4}\b
        |
        \b\d{1,2}[/-]\d{4}\b
        |
        \b(?:19|20)\d{2}\b
        |
        \b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)
        [a-z]*\s+\d{4}\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def extract_date_tokens(
    text: str,
) -> List[str]:
    if not text:
        return []

    return [
        value.lower()
        for value in DATE_PATTERN.findall(
            text
        )
    ]


def dates_preserved(
    before: str,
    after: str,
) -> bool:
    before_dates = extract_date_tokens(
        before
    )

    if not before_dates:
        return True

    after_lower = (after or "").lower()

    return all(
        date_value in after_lower
        for date_value in before_dates
    )


# ============================================================================
# IMPORTANT TERM CHECK
# ============================================================================

def important_terms_check(
    before: str,
    after: str,
) -> Dict[str, Any]:
    before_lower = (
        before or ""
    ).lower()

    after_lower = (
        after or ""
    ).lower()

    present_before = [
        term
        for term in IMPORTANT_TERMS
        if term in before_lower
    ]

    missing_after = [
        term
        for term in present_before
        if term not in after_lower
    ]

    return {
        "present_before": present_before,
        "missing_after": missing_after,
        "passed": not missing_after,
    }


# ============================================================================
# LAYOUT-SPECIFIC CHECKS
# ============================================================================

def count_lines_with_multiple_spaces(
    text: str,
) -> int:
    """
    Detect lines that still contain repeated spaces.

    fix_layout() should normalize these.
    """
    if not text:
        return 0

    count = 0

    for line in text.splitlines():
        if "  " in line:
            count += 1

    return count


def whitespace_normalized(
    text: str,
) -> bool:
    """
    Verify that fix_layout() did not leave obvious duplicate spaces.
    """
    return (
        count_lines_with_multiple_spaces(text)
        == 0
    )


def blank_lines_normalized(
    text: str,
) -> bool:
    return (
        count_excessive_blank_lines(text)
        <= MAX_EXCESSIVE_BLANK_LINES
    )


def line_expansion_check(
    before: str,
    after: str,
) -> bool:
    """
    Detect suspicious line explosion.

    A reduction in lines is normal for fix_layout().
    A very large increase may indicate accidental splitting.
    """
    before_lines = max(
        1,
        count_lines(before),
    )

    after_lines = count_lines(after)

    ratio = after_lines / before_lines

    return ratio <= MAX_LINE_EXPANSION_RATIO


# ============================================================================
# FIX_LAYOUT CALLER
# ============================================================================

def run_fix_layout(
    text: str,
) -> str:
    """
    Safely call the production fix_layout().

    Supports:

        fix_layout(text)

    and:

        fix_layout(text, headings=...)
    """
    if not isinstance(text, str):
        raise TypeError(
            "fix_layout input must be a string"
        )

    try:
        signature = inspect.signature(
            fix_layout
        )

        parameters = signature.parameters

        if "headings" in parameters:
            return fix_layout(
                text,
                headings=None,
            )

        return fix_layout(text)

    except (ValueError, TypeError):
        return fix_layout(text)


# ============================================================================
# SINGLE PDF VALIDATION
# ============================================================================

def validate_pdf(
    pdf_path: Path,
) -> Dict[str, Any]:

    start_time = time.perf_counter()

    result: Dict[str, Any] = {
        "file": pdf_path.name,
        "status": "UNKNOWN",
        "error": None,
    }

    try:
        # ==================================================================
        # STAGE 1
        # PDF -> PYMUPDF
        # ==================================================================

        raw_text = read_pdf(
            str(pdf_path)
        )

        raw_text = (
            raw_text
            if isinstance(raw_text, str)
            else str(raw_text or "")
        )

        raw_chars = len(raw_text)
        raw_words = count_words(raw_text)
        raw_lines = count_lines(raw_text)

        result.update(
            {
                "raw_chars": raw_chars,
                "raw_words": raw_words,
                "raw_lines": raw_lines,
                "raw_replacement_chars":
                    count_replacement_chars(
                        raw_text
                    ),
                "raw_control_chars":
                    count_control_chars(
                        raw_text
                    ),
            }
        )

        # ==================================================================
        # OCR CASE
        # ==================================================================

        if not raw_text.strip():

            result.update(
                {
                    "status": "OCR_REQUIRED",

                    "clean_chars": 0,
                    "clean_words": 0,
                    "clean_lines": 0,

                    "layout_chars": 0,
                    "layout_words": 0,
                    "layout_lines": 0,

                    "clean_token_retention": 0.0,
                    "layout_token_retention": 0.0,

                    "layout_char_retention": 0.0,

                    "clean_replacement_chars": 0,
                    "layout_replacement_chars": 0,

                    "clean_control_chars": 0,
                    "layout_control_chars": 0,

                    "clean_blank_line_issue": False,
                    "layout_blank_line_issue": False,

                    "emails_preserved": True,
                    "phones_preserved": True,
                    "bullets_preserved": True,
                    "headings_preserved": True,
                    "dates_preserved": True,
                    "important_terms_ok": True,

                    "whitespace_normalized": True,
                    "line_expansion_ok": True,

                    "missing_tokens": [],
                    "missing_important_terms": [],
                    "failed_checks": [],

                    "elapsed":
                        time.perf_counter()
                        - start_time,
                }
            )

            return result

        # ==================================================================
        # STAGE 2
        # PYMUPDF -> CLEAN TEXT
        # ==================================================================

        clean_start = time.perf_counter()

        cleaned_text = clean_text(
            raw_text
        )

        clean_elapsed = (
            time.perf_counter()
            - clean_start
        )

        if cleaned_text is None:
            cleaned_text = ""

        cleaned_text = str(
            cleaned_text
        )

        clean_chars = len(
            cleaned_text
        )

        clean_words = count_words(
            cleaned_text
        )

        clean_lines = count_lines(
            cleaned_text
        )

        clean_token_retention = (
            token_retention(
                raw_text,
                cleaned_text,
            )
        )

        # ==================================================================
        # STAGE 3
        # CLEAN TEXT -> FIX_LAYOUT
        # ==================================================================

        layout_start = time.perf_counter()

        layout_text = run_fix_layout(
            cleaned_text
        )

        layout_elapsed = (
            time.perf_counter()
            - layout_start
        )

        if layout_text is None:
            layout_text = ""

        layout_text = str(
            layout_text
        )

        layout_chars = len(
            layout_text
        )

        layout_words = count_words(
            layout_text
        )

        layout_lines = count_lines(
            layout_text
        )

        layout_token_retention = (
            token_retention(
                cleaned_text,
                layout_text,
            )
        )

        layout_char_retention = (
            character_retention(
                cleaned_text,
                layout_text,
            )
        )

        # ==================================================================
        # QUALITY CHECKS
        # ==================================================================

        clean_replacement_chars = (
            count_replacement_chars(
                cleaned_text
            )
        )

        layout_replacement_chars = (
            count_replacement_chars(
                layout_text
            )
        )

        clean_control_chars = (
            count_control_chars(
                cleaned_text
            )
        )

        layout_control_chars = (
            count_control_chars(
                layout_text
            )
        )

        clean_blank_line_issue = (
            count_excessive_blank_lines(
                cleaned_text
            )
            > MAX_EXCESSIVE_BLANK_LINES
        )

        layout_blank_line_issue = (
            count_excessive_blank_lines(
                layout_text
            )
            > MAX_EXCESSIVE_BLANK_LINES
        )

        # ==================================================================
        # CONTENT PRESERVATION
        # ==================================================================

        email_ok = emails_preserved(
            cleaned_text,
            layout_text,
        )

        phone_ok = phones_preserved(
            cleaned_text,
            layout_text,
        )

        bullet_ok = bullets_preserved(
            cleaned_text,
            layout_text,
        )

        heading_ok = headings_preserved(
            cleaned_text,
            layout_text,
        )

        date_ok = dates_preserved(
            cleaned_text,
            layout_text,
        )

        important_check = (
            important_terms_check(
                cleaned_text,
                layout_text,
            )
        )

        # ==================================================================
        # LAYOUT NORMALIZATION
        # ==================================================================

        whitespace_ok = whitespace_normalized(
            layout_text
        )

        blank_line_ok = (
            not layout_blank_line_issue
        )

        line_expansion_ok = (
            line_expansion_check(
                cleaned_text,
                layout_text,
            )
        )

        # ==================================================================
        # DIAGNOSTICS
        # ==================================================================

        missing_tokens = find_missing_tokens(
            cleaned_text,
            layout_text,
        )

        missing_important_terms = (
            important_check[
                "missing_after"
            ]
        )

        # ==================================================================
        # FINAL CHECKS
        # ==================================================================

        checks = {
            "clean_token_retention": (
                clean_token_retention
                >= CLEAN_TOKEN_RETENTION_THRESHOLD
            ),

            "clean_replacement_chars": (
                clean_replacement_chars == 0
            ),

            "clean_control_chars": (
                clean_control_chars == 0
            ),

            "layout_token_retention": (
                layout_token_retention
                >= LAYOUT_TOKEN_RETENTION_THRESHOLD
            ),

            "layout_char_retention": (
                layout_char_retention
                >= LAYOUT_CHAR_RETENTION_THRESHOLD
            ),

            "layout_replacement_chars": (
                layout_replacement_chars == 0
            ),

            "layout_control_chars": (
                layout_control_chars == 0
            ),

            "blank_lines": blank_line_ok,

            "whitespace_normalized": whitespace_ok,

            "line_expansion": line_expansion_ok,

            "emails_preserved": email_ok,

            "phones_preserved": phone_ok,

            "bullets_preserved": bullet_ok,

            "headings_preserved": heading_ok,

            "dates_preserved": date_ok,

            "important_terms": (
                important_check["passed"]
            ),
        }

        failed_checks = [
            name
            for name, passed in checks.items()
            if not passed
        ]

        status = (
            "PASS"
            if not failed_checks
            else "REVIEW"
        )

        result.update(
            {
                "status": status,

                # ----------------------------------------------------------
                # CLEAN STAGE
                # ----------------------------------------------------------

                "clean_chars": clean_chars,
                "clean_words": clean_words,
                "clean_lines": clean_lines,

                "clean_token_retention":
                    clean_token_retention,

                "clean_replacement_chars":
                    clean_replacement_chars,

                "clean_control_chars":
                    clean_control_chars,

                # ----------------------------------------------------------
                # LAYOUT STAGE
                # ----------------------------------------------------------

                "layout_chars": layout_chars,
                "layout_words": layout_words,
                "layout_lines": layout_lines,

                "layout_token_retention":
                    layout_token_retention,

                "layout_char_retention":
                    layout_char_retention,

                "layout_replacement_chars":
                    layout_replacement_chars,

                "layout_control_chars":
                    layout_control_chars,

                # ----------------------------------------------------------
                # CONTENT
                # ----------------------------------------------------------

                "emails_preserved": email_ok,
                "phones_preserved": phone_ok,
                "bullets_preserved": bullet_ok,
                "headings_preserved": heading_ok,
                "dates_preserved": date_ok,

                "important_terms_ok":
                    important_check[
                        "passed"
                    ],

                # ----------------------------------------------------------
                # LAYOUT QUALITY
                # ----------------------------------------------------------

                "clean_blank_line_issue":
                    clean_blank_line_issue,

                "layout_blank_line_issue":
                    layout_blank_line_issue,

                "whitespace_normalized":
                    whitespace_ok,

                "line_expansion_ok":
                    line_expansion_ok,

                # ----------------------------------------------------------
                # DIAGNOSTICS
                # ----------------------------------------------------------

                "missing_tokens":
                    missing_tokens,

                "missing_important_terms":
                    missing_important_terms,

                "failed_checks":
                    failed_checks,

                # ----------------------------------------------------------
                # PERFORMANCE
                # ----------------------------------------------------------

                "clean_elapsed":
                    clean_elapsed,

                "layout_elapsed":
                    layout_elapsed,

                "elapsed":
                    time.perf_counter()
                    - start_time,
            }
        )

        return result

    except Exception as exc:

        result.update(
            {
                "status": "FAIL",
                "error": (
                    f"{type(exc).__name__}: {exc}"
                ),
                "elapsed":
                    time.perf_counter()
                    - start_time,
            }
        )

        return result


# ============================================================================
# RESULT DISPLAY
# ============================================================================

def print_result(
    result: Dict[str, Any],
) -> None:

    print()
    print("-" * 70)

    print(
        f"PDF                 : "
        f"{result['file']}"
    )

    print(
        f"Status              : "
        f"{result['status']}"
    )

    print(
        f"Time                : "
        f"{result.get('elapsed', 0.0):.4f} sec"
    )

    # ========================================================================
    # FAILURE
    # ========================================================================

    if result["status"] == "FAIL":

        print(
            f"Error               : "
            f"{result.get('error', 'Unknown error')}"
        )

        return

    # ========================================================================
    # OCR
    # ========================================================================

    print()
    print("PYMUPDF -> CLEAN TEXT")

    print(
        f"Raw characters          : "
        f"{result.get('raw_chars', 0)}"
    )

    print(
        f"Clean characters        : "
        f"{result.get('clean_chars', 0)}"
    )

    print(
        f"Raw words               : "
        f"{result.get('raw_words', 0)}"
    )

    print(
        f"Clean words             : "
        f"{result.get('clean_words', 0)}"
    )

    print(
        f"Raw lines               : "
        f"{result.get('raw_lines', 0)}"
    )

    print(
        f"Clean lines             : "
        f"{result.get('clean_lines', 0)}"
    )

    print(
        f"Clean token retention   : "
        f"{result.get('clean_token_retention', 0.0):.2f}%"
    )

    print(
        f"Raw replacement chars   : "
        f"{result.get('raw_replacement_chars', 0)}"
    )

    print(
        f"Clean replacement chars : "
        f"{result.get('clean_replacement_chars', 0)}"
    )

    print(
        f"Clean control chars     : "
        f"{result.get('clean_control_chars', 0)}"
    )

    print(
        f"Clean blank-line issue  : "
        f"{result.get('clean_blank_line_issue', False)}"
    )

    if result["status"] == "OCR_REQUIRED":
        return

    # ========================================================================
    # FIX LAYOUT
    # ========================================================================

    print()
    print("CLEAN TEXT -> FIX_LAYOUT")

    print(
        f"Layout characters       : "
        f"{result.get('layout_chars', 0)}"
    )

    print(
        f"Layout words            : "
        f"{result.get('layout_words', 0)}"
    )

    print(
        f"Layout lines            : "
        f"{result.get('layout_lines', 0)}"
    )

    print(
        f"Layout token retention  : "
        f"{result.get('layout_token_retention', 0.0):.2f}%"
    )

    print(
        f"Layout char retention   : "
        f"{result.get('layout_char_retention', 0.0):.2f}%"
    )

    print(
        f"Layout replacement chars: "
        f"{result.get('layout_replacement_chars', 0)}"
    )

    print(
        f"Layout control chars    : "
        f"{result.get('layout_control_chars', 0)}"
    )

    print(
        f"Layout blank-line issue : "
        f"{result.get('layout_blank_line_issue', False)}"
    )

    print(
        f"Whitespace normalized   : "
        f"{result.get('whitespace_normalized', True)}"
    )

    print(
        f"Line expansion check    : "
        f"{result.get('line_expansion_ok', True)}"
    )

    # ========================================================================
    # CONTENT PRESERVATION
    # ========================================================================

    print()
    print("CONTENT PRESERVATION")

    print(
        f"Email preserved         : "
        f"{result.get('emails_preserved', True)}"
    )

    print(
        f"Phone preserved         : "
        f"{result.get('phones_preserved', True)}"
    )

    print(
        f"Bullets preserved       : "
        f"{result.get('bullets_preserved', True)}"
    )

    print(
        f"Headings preserved      : "
        f"{result.get('headings_preserved', True)}"
    )

    print(
        f"Dates preserved         : "
        f"{result.get('dates_preserved', True)}"
    )

    print(
        f"Important terms         : "
        f"{result.get('important_terms_ok', True)}"
    )

    # ========================================================================
    # DIAGNOSTICS
    # ========================================================================

    missing_terms = result.get(
        "missing_important_terms",
        [],
    )

    if missing_terms:
        print(
            "Missing important terms : "
            + ", ".join(missing_terms)
        )

    missing_tokens = result.get(
        "missing_tokens",
        [],
    )

    if missing_tokens:
        print(
            "Missing token samples   : "
            + ", ".join(
                missing_tokens[:20]
            )
        )

    failed_checks = result.get(
        "failed_checks",
        [],
    )

    if failed_checks:
        print(
            "Failed checks           : "
            + ", ".join(failed_checks)
        )


# ============================================================================
# SUMMARY
# ============================================================================

def print_summary(
    results: List[Dict[str, Any]],
) -> None:

    print()
    print()
    print("=" * 70)
    print(
        "PHASE 2/3 - RESUME PIPELINE "
        "VALIDATION SUMMARY"
    )
    print("=" * 70)

    print(
        f"{'PDF':30}"
        f"{'Clean':>10}"
        f"{'Layout':>10}"
        f"{'Retention':>12}"
        f"{'Status':>16}"
    )

    print("-" * 70)

    for result in results:

        file_name = result["file"]

        clean_chars = result.get(
            "clean_chars",
            0,
        )

        layout_chars = result.get(
            "layout_chars",
            0,
        )

        retention = result.get(
            "layout_token_retention",
            0.0,
        )

        print(
            f"{file_name:30}"
            f"{clean_chars:10}"
            f"{layout_chars:10}"
            f"{retention:11.2f}%"
            f"{result['status']:>16}"
        )

    print("-" * 70)

    total = len(results)

    passed = sum(
        result["status"] == "PASS"
        for result in results
    )

    review = sum(
        result["status"] == "REVIEW"
        for result in results
    )

    failed = sum(
        result["status"] == "FAIL"
        for result in results
    )

    ocr_required = sum(
        result["status"] == "OCR_REQUIRED"
        for result in results
    )

    missing = sum(
        result["status"] == "MISSING"
        for result in results
    )

    print(
        f"Total PDFs          : {total}"
    )

    print(
        f"PASS                : {passed}"
    )

    print(
        f"REVIEW              : {review}"
    )

    print(
        f"FAIL                : {failed}"
    )

    print(
        f"OCR_REQUIRED        : {ocr_required}"
    )

    print(
        f"MISSING             : {missing}"
    )

    # ========================================================================
    # FINAL STATUS
    # ========================================================================

    blocking_failures = (
        failed
        + review
        + missing
    )

    print()

    if blocking_failures == 0:

        print("=" * 70)
        print(
            "PHASE 2/3 STATUS : PASS"
        )
        print("=" * 70)

        print()
        print(
            "clean_text() and fix_layout() "
            "validation passed."
        )

        print(
            "Next stage: text_reconstructor() validation."
        )

    else:

        print("=" * 70)
        print(
            "PHASE 2/3 STATUS : REVIEW"
        )
        print("=" * 70)

        print()
        print(
            "Review the failed checks before "
            "moving to text_reconstructor()."
        )


# ============================================================================
# MAIN
# ============================================================================

def main() -> int:

    print("=" * 70)
    print(
        "PHASE 2/3 - RESUME PIPELINE VALIDATION"
    )
    print("=" * 70)

    print()
    print("Validation stages:")
    print(
        "PDF -> PyMuPDF -> clean_text() -> fix_layout()"
    )

    print()
    print("Test folder:")
    print(TEST_PDF_FOLDER)

    # ========================================================================
    # TEST FOLDER CHECK
    # ========================================================================

    if not TEST_PDF_FOLDER.exists():

        print()
        print(
            "ERROR: Test folder does not exist."
        )

        print(
            f"Expected folder: "
            f"{TEST_PDF_FOLDER}"
        )

        return 1

    results: List[Dict[str, Any]] = []

    # ========================================================================
    # TEST FILES
    # ========================================================================

    for file_name in TEST_FILES:

        pdf_path = (
            TEST_PDF_FOLDER
            / file_name
        )

        # ------------------------------------------------------------
        # Missing file
        # ------------------------------------------------------------

        if not pdf_path.exists():

            result = {
                "file": file_name,
                "status": "MISSING",
                "error": (
                    f"File not found: "
                    f"{pdf_path}"
                ),
            }

            results.append(result)

            print()
            print("-" * 70)

            print(
                f"PDF                 : "
                f"{file_name}"
            )

            print(
                "Status              : MISSING"
            )

            print(
                f"Expected path       : "
                f"{pdf_path}"
            )

            continue

        # ------------------------------------------------------------
        # Validate
        # ------------------------------------------------------------

        result = validate_pdf(
            pdf_path
        )

        results.append(result)

        print_result(result)

    # ========================================================================
    # SUMMARY
    # ========================================================================

    print_summary(results)

    # ========================================================================
    # EXIT CODE
    # ========================================================================

    for result in results:

        if result["status"] in {
            "FAIL",
            "REVIEW",
            "MISSING",
        }:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )