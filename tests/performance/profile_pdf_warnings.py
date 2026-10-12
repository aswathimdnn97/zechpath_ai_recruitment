import logging
import sys
import time
from pathlib import Path

import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESUME_DIR = PROJECT_ROOT / "data" / "resumes"


class FontWarningHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.font_bbox_warnings = 0

    def emit(self, record):
        message = record.getMessage()

        if "FontBBox" in message:
            self.font_bbox_warnings += 1


def profile_pdf(file_path: Path):

    handler = FontWarningHandler()

    # Capture pdfminer/pdfplumber logging
    logger_names = [
        "pdfminer",
        "pdfminer.pdfinterp",
        "pdfminer.pdffont",
        "pdfminer.psparser",
    ]

    loggers = []

    for name in logger_names:
        logger = logging.getLogger(name)

        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)

        loggers.append(logger)

    start = time.perf_counter()

    try:

        with pdfplumber.open(str(file_path)) as pdf:

            page_count = len(pdf.pages)

            text_parts = []

            for page in pdf.pages:

                page_text = page.extract_text(
                    x_tolerance=2,
                    y_tolerance=2
                )

                if page_text:
                    text_parts.append(page_text)

        elapsed = time.perf_counter() - start

        return {
            "file": file_path.name,
            "pages": page_count,
            "time": elapsed,
            "warnings": handler.font_bbox_warnings,
            "status": "SUCCESS",
        }

    except Exception as exc:

        elapsed = time.perf_counter() - start

        return {
            "file": file_path.name,
            "pages": 0,
            "time": elapsed,
            "warnings": handler.font_bbox_warnings,
            "status": f"FAILED: {exc}",
        }

    finally:

        for logger in loggers:
            logger.removeHandler(handler)


def main():

    files = sorted(
        file_path
        for file_path in RESUME_DIR.iterdir()
        if file_path.suffix.lower() == ".pdf"
    )

    print("=" * 80)
    print("PDF FONT WARNING PROFILE")
    print("=" * 80)

    results = []

    for file_path in files:

        result = profile_pdf(file_path)

        results.append(result)

        print(
            f"{result['file']:<35} "
            f"time={result['time']:.4f}s "
            f"warnings={result['warnings']:<3} "
            f"pages={result['pages']:<2} "
            f"{result['status']}"
        )

    print()
    print("=" * 80)
    print("WARNING / PERFORMANCE SUMMARY")
    print("=" * 80)

    for result in sorted(
        results,
        key=lambda item: item["time"],
        reverse=True
    ):

        print(
            f"{result['file']:<35} "
            f"{result['time']:.4f}s "
            f"FontBBox warnings={result['warnings']}"
        )


if __name__ == "__main__":
    main()