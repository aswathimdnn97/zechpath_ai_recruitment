from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import BinaryIO


logger = logging.getLogger(__name__)


try:
    import pymupdf

except ImportError:

    try:
        import fitz as pymupdf

    except ImportError:
        pymupdf = None


_WORD_PATTERN = re.compile(
    r"\b[\w.+#/-]+\b"
)


def read_pdf(
    file: str | Path | BinaryIO,
    debug: bool = False,
) -> str:

    if pymupdf is None:
        raise ImportError(
            "PyMuPDF is required for PDF extraction. "
            "Install it using: pip install pymupdf"
        )

    total_start = time.perf_counter() if debug else 0.0

    document = None

    try:

        # ====================================================
        # OPEN PDF
        # ====================================================

        open_start = time.perf_counter() if debug else 0.0

        if isinstance(file, (str, Path)):

            document = pymupdf.open(str(file))

        else:

            try:
                file.seek(0)
            except Exception:
                pass

            pdf_bytes = file.read()

            if not pdf_bytes:
                return ""

            document = pymupdf.open(
                stream=pdf_bytes,
                filetype="pdf",
            )

        open_time = (
            time.perf_counter() - open_start
            if debug
            else 0.0
        )

        # ====================================================
        # PAGE TEXT EXTRACTION
        # ====================================================

        extraction_start = (
            time.perf_counter()
            if debug
            else 0.0
        )

        text_parts: list[str] = []

        page_times: list[float] = []

        for page_number, page in enumerate(
            document,
            start=1,
        ):

            page_start = (
                time.perf_counter()
                if debug
                else 0.0
            )

            page_text = page.get_text("text") or ""

            if debug:
                page_time = (
                    time.perf_counter() - page_start
                )
                page_times.append(page_time)

            if page_text:
                text_parts.append(page_text)

            if debug:
                print(
                    f"[PDF PAGE] "
                    f"page={page_number:<3} "
                    f"time={page_time:.6f}s "
                    f"chars={len(page_text)}"
                )

        extraction_time = (
            time.perf_counter() - extraction_start
            if debug
            else 0.0
        )

        # ====================================================
        # TEXT JOIN
        # ====================================================

        join_start = time.perf_counter() if debug else 0.0

        text = "\n".join(text_parts)

        join_time = (
            time.perf_counter() - join_start
            if debug
            else 0.0
        )

        # ====================================================
        # OCR DETECTION
        # ====================================================

        if debug:
            ocr_start = time.perf_counter()
            ocr_required = not bool(text.strip())
            ocr_detection_time = (
                time.perf_counter() - ocr_start
            )

        # ====================================================
        # TOTAL
        # ====================================================

        total_time = (
            time.perf_counter() - total_start
            if debug
            else 0.0
        )

        # ====================================================
        # PERFORMANCE REPORT
        # ====================================================

        if debug:

            print()
            print("=" * 70)
            print("PYMUPDF PDF READER PERFORMANCE")
            print("=" * 70)

            print(f"Pages                  : {len(document)}")
            print(f"Characters             : {len(text)}")
            print(f"Words                  : {_count_words(text)}")
            print(f"OCR required           : {ocr_required}")
            print()
            print(f"PDF open               : {open_time:.6f} s")
            print(f"Page extraction        : {extraction_time:.6f} s")
            print(f"Text join              : {join_time:.6f} s")
            print(f"OCR detection          : {ocr_detection_time:.6f} s")
            print()
            print(
                f"Total read_pdf         : {total_time:.6f} s"
            )

            if page_times:

                print()
                print("Per-page extraction:")

                for index, page_time in enumerate(
                    page_times,
                    start=1,
                ):
                    print(
                        f"  Page {index:<3}: "
                        f"{page_time:.6f} s"
                    )

            print("=" * 70)

        return text

    except Exception as exc:

        logger.exception(
            "PyMuPDF PDF extraction failed: %s",
            exc,
        )

        raise RuntimeError(
            f"Failed to extract PDF text: {exc}"
        ) from exc

    finally:

        if document is not None:

            try:
                document.close()
            except Exception:
                pass


def _count_words(text: str) -> int:

    if not isinstance(text, str):
        return 0

    return len(
        _WORD_PATTERN.findall(text)
    )