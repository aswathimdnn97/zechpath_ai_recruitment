import time
from pathlib import Path

import pymupdf


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESUME_DIR = PROJECT_ROOT / "data" / "resumes"


def read_pdf_pymupdf(file_path: Path) -> str:
    text_parts = []

    with pymupdf.open(str(file_path)) as document:

        for page in document:
            page_text = page.get_text("text")

            if page_text:
                text_parts.append(page_text)

    return "\n".join(text_parts)


def main():

    files = sorted(
        file_path
        for file_path in RESUME_DIR.iterdir()
        if file_path.suffix.lower() == ".pdf"
    )

    print("=" * 80)
    print("PYMUPDF TEXT EXTRACTION BENCHMARK")
    print("=" * 80)

    results = []

    for file_path in files:

        start = time.perf_counter()

        try:

            text = read_pdf_pymupdf(file_path)

            elapsed = time.perf_counter() - start

            result = {
                "file": file_path.name,
                "time": elapsed,
                "words": len(text.split()),
                "characters": len(text),
                "status": "SUCCESS",
            }

        except Exception as exc:

            elapsed = time.perf_counter() - start

            result = {
                "file": file_path.name,
                "time": elapsed,
                "words": 0,
                "characters": 0,
                "status": f"FAILED: {exc}",
            }

        results.append(result)

        print(
            f"{result['file']:<35} "
            f"{result['time']:.4f}s "
            f"{result['words']:>5} words "
            f"{result['status']}"
        )

    successful = [
        result
        for result in results
        if result["status"] == "SUCCESS"
    ]

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    if successful:

        total_time = sum(
            result["time"]
            for result in successful
        )

        average_time = total_time / len(successful)

        print(f"Successful resumes : {len(successful)}")
        print(f"Total extraction   : {total_time:.4f}s")
        print(f"Average extraction : {average_time:.4f}s")
        print(
            f"Fastest extraction : "
            f"{min(r['time'] for r in successful):.4f}s"
        )
        print(
            f"Slowest extraction : "
            f"{max(r['time'] for r in successful):.4f}s"
        )
        print(
            f"Total words        : "
            f"{sum(r['words'] for r in successful)}"
        )
        print(
            f"Total characters   : "
            f"{sum(r['characters'] for r in successful)}"
        )


if __name__ == "__main__":
    main()