"""
Phase 4 - Text Reconstructor Validation

Pipeline:

PDF
 ↓
PyMuPDF
 ↓
clean_text()
 ↓
fix_layout()
 ↓
text_reconstructor()

Purpose:
Validate that text reconstruction improves spacing while preserving
resume content and avoiding suspicious modifications.
"""

import re
import sys
import time
from pathlib import Path
from collections import Counter


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TEST_FOLDER = (
    PROJECT_ROOT
    / "data"
    / "validation"
    / "edge_case_resumes"
)


# ============================================================
# IMPORT PROJECT MODULES
# ============================================================

sys.path.insert(0, str(PROJECT_ROOT))

from parsers.pdf_reader import read_pdf
from document_processing.common.cleaner import clean_text
from document_processing.common.handling_layout import fix_layout
from document_processing.resume.text_reconstruction import text_reconstructor


# ============================================================
# VALIDATION THRESHOLDS
# ============================================================

TOKEN_RETENTION_THRESHOLD = 95.0
WORD_RETENTION_THRESHOLD = 95.0
CHAR_RETENTION_THRESHOLD = 85.0

MAX_REPLACEMENT_CHARS = 0
MAX_CONTROL_CHARS = 0

MAX_EXCESSIVE_BLANK_LINES = 3

MAX_DUPLICATE_RATIO = 0.15


# ============================================================
# TEST FILES
# ============================================================

TEST_FILES = [
    "bullet_heavy.pdf",
    "image_resume.pdf",
    "multi_page.pdf",
    "table_resume.pdf",
    "two_column.pdf",
]


# ============================================================
# REGEX
# ============================================================

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:\+?\d[\d\s().-]{7,}\d)"
    r"(?!\d)"
)

DATE_PATTERN = re.compile(
    r"""
    (?:
        \b(?:19|20)\d{2}\b
        |
        \b\d{1,2}[/-]\d{4}\b
        |
        \b(?:19|20)\d{2}\s*[-–—]\s*
        (?:present|current|(19|20)\d{2})
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

BULLET_PATTERN = re.compile(
    r"^[ \t]*"
    r"(?:[•●▪◦‣⁃∙·*➢➤►▸-])"
    r"\s+",
    re.MULTILINE,
)

HEADING_PATTERN = re.compile(
    r"(?im)^\s*"
    r"(?:"
    r"summary|profile|objective|"
    r"skills?|technical skills?|"
    r"experience|work experience|"
    r"education|"
    r"certifications?|"
    r"projects?|"
    r"languages?"
    r")"
    r"\s*:?\s*$"
)


# ============================================================
# IMPORTANT TERMS
# ============================================================

IMPORTANT_TERMS = [
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "django",
    "spring",
    "sql",
    "mysql",
    "mongodb",
    "machine learning",
    "data",
    "experience",
    "education",
    "skills",
    "projects",
    "certifications",
]


# ============================================================
# BASIC HELPERS
# ============================================================

def normalize_for_comparison(text):
    """
    Normalize text only for comparison purposes.
    Does not modify the actual pipeline output.
    """
    if not text:
        return ""

    return re.sub(
        r"\s+",
        " ",
        text.lower()
    ).strip()


def tokenize(text):
    """
    Tokenize text for preservation comparison.
    """
    if not text:
        return []

    return re.findall(
        r"\b[\w.+#/-]+\b",
        text.lower()
    )


def word_count(text):
    return len(tokenize(text))


def char_count(text):
    return len(text or "")


def line_count(text):
    if not text:
        return 0

    return len(text.splitlines())


def count_replacement_chars(text):
    return (text or "").count("\ufffd")


def count_control_chars(text):
    """
    Count suspicious control characters while allowing
    normal whitespace characters.
    """
    count = 0

    for char in text or "":
        if ord(char) < 32 and char not in "\n\r\t":
            count += 1

    return count


def excessive_blank_lines(text):
    """
    Detect runs of more than the allowed number of
    consecutive blank lines.
    """
    if not text:
        return False

    return bool(
        re.search(
            r"\n{" + str(MAX_EXCESSIVE_BLANK_LINES + 2) + r",}",
            text
        )
    )


# ============================================================
# TOKEN RETENTION
# ============================================================

def token_retention(before, after):
    """
    Calculate percentage of original token occurrences
    preserved after reconstruction.

    Counter-based comparison prevents duplicate tokens
    from being ignored.
    """
    before_tokens = tokenize(before)
    after_tokens = tokenize(after)

    if not before_tokens:
        return 100.0

    before_counter = Counter(before_tokens)
    after_counter = Counter(after_tokens)

    preserved = 0

    for token, count in before_counter.items():
        preserved += min(
            count,
            after_counter.get(token, 0)
        )

    return (
        preserved
        / len(before_tokens)
        * 100
    )


# ============================================================
# MISSING / ADDED TOKENS
# ============================================================

def token_difference(before, after):
    before_counter = Counter(tokenize(before))
    after_counter = Counter(tokenize(after))

    missing = before_counter - after_counter
    added = after_counter - before_counter

    return missing, added


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def duplicate_line_ratio(text):
    """
    Detect duplicated non-empty lines.

    A reconstruction should not accidentally duplicate
    resume content.
    """
    if not text:
        return 0.0

    lines = [
        normalize_for_comparison(line)
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return 0.0

    counts = Counter(lines)

    duplicate_count = sum(
        count - 1
        for count in counts.values()
        if count > 1
    )

    return duplicate_count / len(lines)


# ============================================================
# SUSPICIOUS MERGING
# ============================================================

def detect_suspicious_merging(before, after):
    """
    Look for cases where reconstruction causes two or more
    previously separate tokens to become a suspicious
    long token.

    Example:

        Python Developer

    becoming:

        PythonDeveloper

    """
    before_tokens = set(tokenize(before))
    suspicious = []

    for token in tokenize(after):
        if len(token) < 12:
            continue

        # If the long token was not present previously,
        # it deserves inspection.
        if token not in before_tokens:
            suspicious.append(token)

    return suspicious


# ============================================================
# SUSPICIOUS SPLITTING
# ============================================================

def detect_suspicious_splitting(before, after):
    """
    Detect known technical compounds that may have been
    incorrectly split.

    Example:

        JavaScript -> Java Script
    """

    compounds = [
        "javascript",
        "typescript",
        "github",
        "gitlab",
        "tensorflow",
        "pytorch",
        "mongodb",
        "postgresql",
        "mysql",
        "nodejs",
        "reactjs",
        "angularjs",
        "expressjs",
        "powerbi",
        "devops",
        "fullstack",
        "machinelearning",
        "deepfake",
    ]

    before_normalized = normalize_for_comparison(before)
    after_normalized = normalize_for_comparison(after)

    suspicious = []

    for compound in compounds:
        if compound not in before_normalized:
            continue

        if compound not in after_normalized:
            # Check whether it became separated.
            parts = compound

            if compound == "javascript":
                possible = "java script"
            elif compound == "typescript":
                possible = "type script"
            elif compound == "machinelearning":
                possible = "machine learning"
            elif compound == "fullstack":
                possible = "full stack"
            elif compound == "nodejs":
                possible = "node js"
            elif compound == "reactjs":
                possible = "react js"
            elif compound == "angularjs":
                possible = "angular js"
            elif compound == "expressjs":
                possible = "express js"
            elif compound == "powerbi":
                possible = "power bi"
            elif compound == "github":
                possible = "git hub"
            elif compound == "gitlab":
                possible = "git lab"
            elif compound == "mongodb":
                possible = "mongo db"
            elif compound == "tensorflow":
                possible = "tensor flow"
            elif compound == "pytorch":
                possible = "py torch"
            elif compound == "postgresql":
                possible = "postgre sql"
            elif compound == "devops":
                possible = "dev ops"
            elif compound == "deepfake":
                possible = "deep fake"
            else:
                possible = ""

            if possible and possible in after_normalized:
                suspicious.append(
                    f"{compound} -> {possible}"
                )

    return suspicious


# ============================================================
# PRESERVATION CHECKS
# ============================================================

def extract_emails(text):
    return set(
        EMAIL_PATTERN.findall(text or "")
    )


def extract_phones(text):
    return set(
        match.group(0).strip()
        for match in PHONE_PATTERN.finditer(text or "")
    )


def extract_dates(text):
    return set(
        match.group(0).strip().lower()
        for match in DATE_PATTERN.finditer(text or "")
    )


def check_email_preservation(before, after):
    expected = extract_emails(before)
    actual = extract_emails(after)

    return expected.issubset(actual)


def check_phone_preservation(before, after):
    expected = extract_phones(before)

    if not expected:
        return True

    actual = extract_phones(after)

    return expected.issubset(actual)


def check_date_preservation(before, after):
    expected = extract_dates(before)

    if not expected:
        return True

    actual = extract_dates(after)

    return expected.issubset(actual)


def check_bullet_preservation(before, after):
    before_count = len(
        BULLET_PATTERN.findall(before or "")
    )

    after_count = len(
        BULLET_PATTERN.findall(after or "")
    )

    return after_count >= before_count


def check_heading_preservation(before, after):
    before_headings = {
        normalize_for_comparison(match.group(0))
        for match in HEADING_PATTERN.finditer(before or "")
    }

    if not before_headings:
        return True

    after_normalized = normalize_for_comparison(after)

    return all(
        heading in after_normalized
        for heading in before_headings
    )


def check_important_terms(before, after):
    before_normalized = normalize_for_comparison(before)
    after_normalized = normalize_for_comparison(after)

    expected_terms = [
        term
        for term in IMPORTANT_TERMS
        if term in before_normalized
    ]

    return all(
        term in after_normalized
        for term in expected_terms
    )


# ============================================================
# RECONSTRUCTION QUALITY
# ============================================================

def reconstruction_changed(before, after):
    return before != after


def whitespace_improved(text):
    if not text:
        return True

    return not bool(
        re.search(
            r"[ \t]{2,}",
            text
        )
    )


def deterministic_check(text):
    """
    Run the reconstruction twice and ensure both outputs
    are identical.
    """
    first = text_reconstructor(text)
    second = text_reconstructor(text)

    return first == second


# ============================================================
# PRINT DETAILS
# ============================================================

def print_section(title):
    print()
    print(title)
    print("-" * 70)


# ============================================================
# VALIDATE ONE PDF
# ============================================================

def validate_pdf(pdf_path):
    start_time = time.perf_counter()

    raw_text = read_pdf(str(pdf_path))

    # --------------------------------------------------------
    # OCR REQUIRED
    # --------------------------------------------------------

    if not raw_text.strip():
        elapsed = time.perf_counter() - start_time

        print("-" * 70)
        print(f"PDF                 : {pdf_path.name}")
        print("Status              : OCR_REQUIRED")
        print(f"Time                : {elapsed:.4f} sec")
        print("Raw characters      : 0")
        print("Reconstructed       : 0")

        return {
            "file": pdf_path.name,
            "status": "OCR_REQUIRED",
        }

    # --------------------------------------------------------
    # PHASE 2/3
    # --------------------------------------------------------

    cleaned_text = clean_text(raw_text)

    layout_text = fix_layout(
        cleaned_text
    )

    # --------------------------------------------------------
    # PHASE 4
    # --------------------------------------------------------

    reconstructed_text = text_reconstructor(
        layout_text
    )

    elapsed = time.perf_counter() - start_time

    # --------------------------------------------------------
    # METRICS
    # --------------------------------------------------------

    layout_words = word_count(layout_text)
    reconstructed_words = word_count(
        reconstructed_text
    )

    layout_chars = char_count(layout_text)
    reconstructed_chars = char_count(
        reconstructed_text
    )

    layout_lines = line_count(layout_text)
    reconstructed_lines = line_count(
        reconstructed_text
    )

    token_retention_pct = token_retention(
    layout_text,
    reconstructed_text
    )

    if layout_words:
        word_retention = (
            reconstructed_words
            / layout_words
            * 100
        )
    else:
        word_retention = 100.0

    if layout_chars:
        char_retention = (
            reconstructed_chars
            / layout_chars
            * 100
        )
    else:
        char_retention = 100.0

    replacement_chars = count_replacement_chars(
        reconstructed_text
    )

    control_chars = count_control_chars(
        reconstructed_text
    )

    blank_line_issue = excessive_blank_lines(
        reconstructed_text
    )

    duplicate_ratio = duplicate_line_ratio(
        reconstructed_text
    )

    missing_tokens, added_tokens = token_difference(
        layout_text,
        reconstructed_text
    )

    suspicious_merging = detect_suspicious_merging(
        layout_text,
        reconstructed_text
    )

    suspicious_splitting = detect_suspicious_splitting(
        layout_text,
        reconstructed_text
    )

    # --------------------------------------------------------
    # PRESERVATION
    # --------------------------------------------------------

    email_ok = check_email_preservation(
        layout_text,
        reconstructed_text
    )

    phone_ok = check_phone_preservation(
        layout_text,
        reconstructed_text
    )

    bullet_ok = check_bullet_preservation(
        layout_text,
        reconstructed_text
    )

    heading_ok = check_heading_preservation(
        layout_text,
        reconstructed_text
    )

    date_ok = check_date_preservation(
        layout_text,
        reconstructed_text
    )

    important_ok = check_important_terms(
        layout_text,
        reconstructed_text
    )

    deterministic_ok = deterministic_check(
        layout_text
    )

    whitespace_ok = whitespace_improved(
        reconstructed_text
    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    failures = []

    if token_retention_pct < TOKEN_RETENTION_THRESHOLD:
        failures.append(
            f"token retention {token_retention_pct:.2f}%"
        )

    if word_retention < WORD_RETENTION_THRESHOLD:
        failures.append(
            f"word retention {word_retention:.2f}%"
        )

    if char_retention < CHAR_RETENTION_THRESHOLD:
        failures.append(
            f"char retention {char_retention:.2f}%"
        )

    if replacement_chars > MAX_REPLACEMENT_CHARS:
        failures.append(
            "replacement characters"
        )

    if control_chars > MAX_CONTROL_CHARS:
        failures.append(
            "control characters"
        )

    if blank_line_issue:
        failures.append(
            "excessive blank lines"
        )

    if duplicate_ratio > MAX_DUPLICATE_RATIO:
        failures.append(
            f"duplicate line ratio {duplicate_ratio:.2%}"
        )

    if not email_ok:
        failures.append(
            "email not preserved"
        )

    if not phone_ok:
        failures.append(
            "phone not preserved"
        )

    if not bullet_ok:
        failures.append(
            "bullets not preserved"
        )

    if not heading_ok:
        failures.append(
            "headings not preserved"
        )

    if not date_ok:
        failures.append(
            "dates not preserved"
        )

    if not important_ok:
        failures.append(
            "important terms not preserved"
        )

    if not deterministic_ok:
        failures.append(
            "non-deterministic output"
        )

    if failures:
        status = "FAIL"
    elif (
        suspicious_merging
        or suspicious_splitting
        or not whitespace_ok
    ):
        status = "REVIEW"
    else:
        status = "PASS"

    # --------------------------------------------------------
    # OUTPUT
    # --------------------------------------------------------

    print("-" * 70)
    print(f"PDF                 : {pdf_path.name}")
    print(f"Status              : {status}")
    print(f"Time                : {elapsed:.4f} sec")

    print_section(
        "FIX_LAYOUT -> TEXT_RECONSTRUCTOR"
    )

    print(
        f"Layout characters        : {layout_chars}"
    )
    print(
        f"Reconstructed characters  : {reconstructed_chars}"
    )
    print(
        f"Layout words             : {layout_words}"
    )
    print(
        f"Reconstructed words      : {reconstructed_words}"
    )
    print(
        f"Layout lines             : {layout_lines}"
    )
    print(
        f"Reconstructed lines      : {reconstructed_lines}"
    )

    print(
        f"Token retention          : "
        f"{token_retention_pct:.2f}%"
    )
    print(
        f"Word retention           : "
        f"{word_retention:.2f}%"
    )
    print(
        f"Character retention      : "
        f"{char_retention:.2f}%"
    )

    print(
        f"Text changed             : "
        f"{reconstruction_changed(layout_text, reconstructed_text)}"
    )

    print_section(
        "TEXT QUALITY"
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
        f"Excessive blank lines   : "
        f"{blank_line_issue}"
    )
    print(
        f"Duplicate line ratio    : "
        f"{duplicate_ratio:.2%}"
    )
    print(
        f"Whitespace normalized   : "
        f"{whitespace_ok}"
    )
    print(
        f"Deterministic output    : "
        f"{deterministic_ok}"
    )

    print_section(
        "CONTENT PRESERVATION"
    )

    print(
        f"Email preserved         : "
        f"{email_ok}"
    )
    print(
        f"Phone preserved         : "
        f"{phone_ok}"
    )
    print(
        f"Bullets preserved       : "
        f"{bullet_ok}"
    )
    print(
        f"Headings preserved      : "
        f"{heading_ok}"
    )
    print(
        f"Dates preserved         : "
        f"{date_ok}"
    )
    print(
        f"Important terms         : "
        f"{important_ok}"
    )

    print_section(
        "RECONSTRUCTION SAFETY"
    )

    print(
        f"Missing token types     : "
        f"{len(missing_tokens)}"
    )

    if missing_tokens:
        print(
            "Missing tokens          : "
            + ", ".join(
                list(missing_tokens.keys())[:20]
            )
        )

    print(
        f"Added token types       : "
        f"{len(added_tokens)}"
    )

    if added_tokens:
        print(
            "Added tokens            : "
            + ", ".join(
                list(added_tokens.keys())[:20]
            )
        )

    print(
        f"Suspicious merging      : "
        f"{len(suspicious_merging)}"
    )

    if suspicious_merging:
        print(
            "Merged candidates       : "
            + ", ".join(
                suspicious_merging[:20]
            )
        )

    print(
        f"Suspicious splitting    : "
        f"{len(suspicious_splitting)}"
    )

    if suspicious_splitting:
        print(
            "Split compounds         : "
            + ", ".join(
                suspicious_splitting
            )
        )

    return {
        "file": pdf_path.name,
        "status": status,
        "token_retention": token_retention_pct,
        "word_retention": word_retention,
        "char_retention": char_retention,
        "suspicious_merging": suspicious_merging,
        "suspicious_splitting": suspicious_splitting,
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("PHASE 4 - TEXT RECONSTRUCTOR VALIDATION")
    print("=" * 70)

    print()
    print("Validation stages:")
    print(
        "PDF -> PyMuPDF -> clean_text() -> "
        "fix_layout() -> text_reconstructor()"
    )

    print()
    print("Test folder:")
    print(TEST_FOLDER)

    results = []

    for filename in TEST_FILES:

        pdf_path = TEST_FOLDER / filename

        if not pdf_path.exists():

            print("-" * 70)
            print(
                f"PDF                 : {filename}"
            )
            print("Status              : MISSING")

            results.append({
                "file": filename,
                "status": "MISSING",
            })

            continue

        try:
            result = validate_pdf(
                pdf_path
            )

        except Exception as exc:

            print("-" * 70)
            print(
                f"PDF                 : {filename}"
            )
            print("Status              : FAIL")
            print(
                f"Error               : {exc}"
            )

            results.append({
                "file": filename,
                "status": "FAIL",
            })

            continue

        results.append(result)

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print()
    print("=" * 70)
    print("PHASE 4 - TEXT RECONSTRUCTOR VALIDATION SUMMARY")
    print("=" * 70)

    print(
        f"{'PDF':35}"
        f"{'Status':12}"
        f"{'Token':12}"
        f"{'Words':12}"
        f"{'Chars':12}"
    )

    print("-" * 70)

    pass_count = 0
    review_count = 0
    fail_count = 0
    ocr_count = 0
    missing_count = 0

    for result in results:

        status = result["status"]

        if status == "PASS":
            pass_count += 1

        elif status == "REVIEW":
            review_count += 1

        elif status == "FAIL":
            fail_count += 1

        elif status == "OCR_REQUIRED":
            ocr_count += 1

        elif status == "MISSING":
            missing_count += 1

        token = result.get(
            "token_retention"
        )

        words = result.get(
            "word_retention"
        )

        chars = result.get(
            "char_retention"
        )

        token_text = (
            f"{token:.2f}%"
            if token is not None
            else "-"
        )

        word_text = (
            f"{words:.2f}%"
            if words is not None
            else "-"
        )

        char_text = (
            f"{chars:.2f}%"
            if chars is not None
            else "-"
        )

        print(
            f"{result['file']:35}"
            f"{status:12}"
            f"{token_text:12}"
            f"{word_text:12}"
            f"{char_text:12}"
        )

    print("-" * 70)

    print(
        f"Total PDFs          : {len(results)}"
    )
    print(
        f"PASS                : {pass_count}"
    )
    print(
        f"REVIEW              : {review_count}"
    )
    print(
        f"FAIL                : {fail_count}"
    )
    print(
        f"OCR_REQUIRED        : {ocr_count}"
    )
    print(
        f"MISSING             : {missing_count}"
    )

    # ========================================================
    # FINAL STATUS
    # ========================================================

    if (
        fail_count == 0
        and missing_count == 0
    ):
        print()
        print("=" * 70)
        print("PHASE 4 STATUS : PASS")
        print("=" * 70)
        print()
        print(
            "text_reconstructor() validation passed."
        )
        print(
            "Next stage: normalize_text() validation."
        )

    elif fail_count == 0:

        print()
        print("=" * 70)
        print("PHASE 4 STATUS : REVIEW")
        print("=" * 70)

    else:

        print()
        print("=" * 70)
        print("PHASE 4 STATUS : FAIL")
        print("=" * 70)


if __name__ == "__main__":
    main()