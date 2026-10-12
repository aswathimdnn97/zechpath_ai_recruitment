import time
import re
from pathlib import Path

import fitz


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

RESUME_DIR = (
    BASE_DIR
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


# ============================================================
# HELPERS
# ============================================================

def count_words(text: str) -> int:
    """Count words from extracted text."""

    if not text:
        return 0

    return len(
        re.findall(
            r"\b[\w.+#/-]+\b",
            text
        )
    )


def detect_malformed_text(text: str) -> list:
    """Detect obvious extraction artifacts."""

    issues = []

    if not text:
        return issues

    # Common PDF extraction artifacts
    if "(cid:" in text.lower():
        issues.append("CID_ARTIFACT")

    replacement_count = text.count("�")

    if replacement_count > 0:
        issues.append(
            f"UNICODE_REPLACEMENT:{replacement_count}"
        )

    return issues


def extract_with_pymupdf(pdf_path: Path) -> dict:
    """Extract PDF text using PyMuPDF only."""

    start_time = time.perf_counter()

    document = None

    try:

        document = fitz.open(pdf_path)

        page_count = len(document)

        page_texts = []

        image_only_pages = 0

        for page_number, page in enumerate(
            document,
            start=1
        ):

            text = page.get_text("text") or ""

            page_texts.append(text)

            if not text.strip():
                image_only_pages += 1

        text = "\n".join(page_texts)

        elapsed = (
            time.perf_counter()
            - start_time
        )

        words = count_words(text)

        malformed = detect_malformed_text(
            text
        )

        ocr_required = not bool(
            text.strip()
        )

        return {
            "success": True,
            "pages": page_count,
            "characters": len(text),
            "words": words,
            "lines": len(
                text.splitlines()
            ),
            "image_only_pages": image_only_pages,
            "ocr_required": ocr_required,
            "malformed": malformed,
            "time": elapsed,
            "text": text,
        }

    except Exception as exc:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        return {
            "success": False,
            "error": str(exc),
            "time": elapsed,
            "pages": 0,
            "characters": 0,
            "words": 0,
            "lines": 0,
            "image_only_pages": 0,
            "ocr_required": False,
            "malformed": [],
            "text": "",
        }

    finally:

        if document is not None:

            try:
                document.close()

            except Exception:
                pass


# ============================================================
# VALIDATE ONE PDF
# ============================================================

def validate_pdf(pdf_path: Path) -> dict:

    result = extract_with_pymupdf(
        pdf_path
    )

    print()
    print("=" * 78)
    print(f"PDF : {pdf_path.name}")
    print("=" * 78)

    if not result["success"]:

        print("Status       : FAILED")
        print(
            f"Error        : {result['error']}"
        )

        return result

    print("Status       : SUCCESS")
    print(
        f"Time         : "
        f"{result['time']:.4f} sec"
    )
    print(
        f"Pages        : "
        f"{result['pages']}"
    )
    print(
        f"Characters   : "
        f"{result['characters']}"
    )
    print(
        f"Words        : "
        f"{result['words']}"
    )
    print(
        f"Lines        : "
        f"{result['lines']}"
    )
    print(
        f"Image pages  : "
        f"{result['image_only_pages']}"
    )

    print(
        f"OCR required : "
        f"{'YES' if result['ocr_required'] else 'NO'}"
    )

    if result["malformed"]:

        print(
            "Malformed    : YES"
        )

        print(
            f"Issues       : "
            f"{result['malformed']}"
        )

    else:

        print(
            "Malformed    : NO"
        )

    # --------------------------------------------------------
    # Preview
    # --------------------------------------------------------

    print()
    print("TEXT PREVIEW")
    print("-" * 78)

    preview = result["text"].strip()

    if preview:

        preview_lines = preview.splitlines()

        for line in preview_lines:

            print(line)

    else:

        print(
            "[NO EXTRACTABLE TEXT]"
        )

    # --------------------------------------------------------
    # Final status
    # --------------------------------------------------------

    if result["ocr_required"]:

        result["status"] = "OCR_REQUIRED"

    elif result["malformed"]:

        result["status"] = "REVIEW"

    else:

        result["status"] = "PASS"

    print()
    print(
        f"FINAL STATUS : "
        f"{result['status']}"
    )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print("=" * 78)
    print("FINAL ROUND 5 - PYMUPDF READER VALIDATION")
    print("=" * 78)

    print()
    print(
        f"Resume directory : {RESUME_DIR}"
    )

    print(
        f"Test files       : {len(TEST_FILES)}"
    )

    # --------------------------------------------------------
    # Directory check
    # --------------------------------------------------------

    if not RESUME_DIR.exists():

        print()
        print(
            "ERROR: Resume directory does not exist."
        )

        print(
            RESUME_DIR
        )

        return

    # --------------------------------------------------------
    # Validate all five PDFs
    # --------------------------------------------------------

    results = []

    for filename in TEST_FILES:

        pdf_path = (
            RESUME_DIR / filename
        )

        if not pdf_path.exists():

            print()
            print("=" * 78)
            print(
                f"PDF : {filename}"
            )
            print("=" * 78)

            print(
                "Status : FILE NOT FOUND"
            )

            results.append(
                {
                    "file": filename,
                    "status": "FILE_NOT_FOUND",
                    "success": False,
                }
            )

            continue

        result = validate_pdf(
            pdf_path
        )

        result["file"] = filename

        results.append(result)

    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 78)
    print("FINAL ROUND 5 SUMMARY")
    print("=" * 78)

    successful = sum(
        1
        for result in results
        if result.get("success")
    )

    failed = len(results) - successful

    ocr_required = sum(
        1
        for result in results
        if result.get("status")
        == "OCR_REQUIRED"
    )

    review_required = sum(
        1
        for result in results
        if result.get("status")
        == "REVIEW"
    )

    passed = sum(
        1
        for result in results
        if result.get("status")
        == "PASS"
    )

    print()
    print(
        f"Total PDFs       : {len(results)}"
    )

    print(
        f"Reader success   : "
        f"{successful}/{len(results)}"
    )

    print(
        f"Reader failures  : "
        f"{failed}"
    )

    print(
        f"PASS             : "
        f"{passed}"
    )

    print(
        f"OCR required     : "
        f"{ocr_required}"
    )

    print(
        f"Review required  : "
        f"{review_required}"
    )

    # --------------------------------------------------------
    # Per-file summary
    # --------------------------------------------------------

    print()
    print("-" * 78)
    print(
        f"{'PDF':25}"
        f"{'Status':18}"
        f"{'Pages':8}"
        f"{'Words':10}"
        f"{'Time':10}"
    )
    print("-" * 78)

    for result in results:

        print(
            f"{result['file'][:24]:25}"
            f"{result.get('status', 'UNKNOWN'):18}"
            f"{str(result.get('pages', '-')):8}"
            f"{str(result.get('words', '-')):10}"
            f"{result.get('time', 0):.4f}"
        )

    # ========================================================
    # FINAL DECISION
    # ========================================================

    print()
    print("=" * 78)
    print("READER VALIDATION RESULT")
    print("=" * 78)

    non_ocr_failures = [
        result
        for result in results
        if (
            result.get("status")
            not in {
                "PASS",
                "OCR_REQUIRED",
            }
        )
    ]

    if (
        successful == len(TEST_FILES)
        and not non_ocr_failures
    ):

        print()
        print(
            "STATUS : PYMuPDF READER VALIDATED"
        )

        print()
        print(
            "PyMuPDF successfully processed "
            "the final test set."
        )

        print(
            "Image-only PDFs are correctly "
            "identified as OCR_REQUIRED."
        )

        print(
            "The PDF reader validation is complete."
        )

    else:

        print()
        print(
            "STATUS : REVIEW REQUIRED"
        )

        print()
        print(
            "One or more reader validation "
            "checks require investigation."
        )

    print()
    print("=" * 78)
    print("PDF READER VALIDATION COMPLETED")
    print("=" * 78)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()