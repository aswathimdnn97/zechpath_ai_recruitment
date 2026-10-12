import sys
import time
from pathlib import Path

import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESUME_DIR = PROJECT_ROOT / "data" / "resumes"


def profile_pdf(file_path: Path):
    start = time.perf_counter()

    try:
        with pdfplumber.open(str(file_path)) as pdf:

            page_count = len(pdf.pages)

            total_chars = 0
            total_words = 0

            for page in pdf.pages:

                page_text = page.extract_text(
                    x_tolerance=2,
                    y_tolerance=2
                )

                if page_text:
                    total_chars += len(page_text)
                    total_words += len(page_text.split())

        elapsed = time.perf_counter() - start

        return {
            "file": file_path.name,
            "pages": page_count,
            "words": total_words,
            "characters": total_chars,
            "time": elapsed,
            "status": "SUCCESS",
        }

    except Exception as exc:

        elapsed = time.perf_counter() - start

        return {
            "file": file_path.name,
            "pages": 0,
            "words": 0,
            "characters": 0,
            "time": elapsed,
            "status": f"FAILED: {exc}",
        }


def main():

    files = sorted(
        file_path
        for file_path in RESUME_DIR.iterdir()
        if file_path.suffix.lower() == ".pdf"
    )

    print("=" * 80)
    print("PDF EXTRACTION PROFILE")
    print("=" * 80)

    results = []

    for file_path in files:

        result = profile_pdf(file_path)
        results.append(result)

        print(
            f"{result['file']:<35} "
            f"pages={result['pages']:<3} "
            f"words={result['words']:<5} "
            f"time={result['time']:.4f}s "
            f"{result['status']}"
        )

    print()
    print("=" * 80)
    print("SLOWEST FILES")
    print("=" * 80)

    successful = [
        result
        for result in results
        if result["status"] == "SUCCESS"
    ]

    for result in sorted(
        successful,
        key=lambda item: item["time"],
        reverse=True
    )[:5]:

        print(
            f"{result['file']:<35} "
            f"{result['time']:.4f}s "
            f"{result['pages']} pages "
            f"{result['words']} words"
        )


if __name__ == "__main__":
    main()