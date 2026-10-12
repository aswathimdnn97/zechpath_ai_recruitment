import sys
import time
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# IMPORTS
# ============================================================

from parsers.pdf_reader import read_pdf
from parsers.docx_reader import read_docx


# ============================================================
# CONFIGURATION
# ============================================================

RESUME_DIR = (
    PROJECT_ROOT
    / "data"
    / "resumes"
)

WARMUP_RUNS = 1
MEASURED_RUNS = 5

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
}


# ============================================================
# TEXT EXTRACTION
# ============================================================

def extract_text(
    file_path: Path,
) -> str:

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return read_pdf(str(file_path))

    if extension == ".docx":
        return read_docx(str(file_path))

    raise ValueError(
        f"Unsupported file format: {extension}"
    )


# ============================================================
# BENCHMARK ONE FILE
# ============================================================

def benchmark_file(
    file_path: Path,
) -> dict:

    # --------------------------------------------------------
    # Warm-up
    # --------------------------------------------------------

    for _ in range(WARMUP_RUNS):
        extract_text(file_path)

    # --------------------------------------------------------
    # Measured runs
    # --------------------------------------------------------

    timings = []
    text = ""

    for _ in range(MEASURED_RUNS):

        start_time = time.perf_counter()

        text = extract_text(file_path)

        elapsed = (
            time.perf_counter()
            - start_time
        )

        timings.append(elapsed)

    average_time = (
        sum(timings)
        / len(timings)
    )

    minimum_time = min(timings)
    maximum_time = max(timings)

    return {
        "file": file_path.name,
        "average": average_time,
        "minimum": minimum_time,
        "maximum": maximum_time,
        "characters": len(text),
        "words": len(text.split()),
        "status": "SUCCESS",
    }


# ============================================================
# MAIN BENCHMARK
# ============================================================

def benchmark():

    if not RESUME_DIR.exists():

        print(
            f"Resume directory not found: "
            f"{RESUME_DIR}"
        )

        return

    files = sorted(
        file_path
        for file_path in RESUME_DIR.iterdir()
        if (
            file_path.is_file()
            and file_path.suffix.lower()
            in SUPPORTED_EXTENSIONS
        )
    )

    if not files:

        print(
            "No PDF/DOCX resumes found in: "
            f"{RESUME_DIR}"
        )

        return

    print("=" * 90)
    print(
        "ATS TEXT EXTRACTION PERFORMANCE BENCHMARK"
    )
    print("=" * 90)

    print(
        f"Resume directory : {RESUME_DIR}"
    )

    print(
        f"Total resumes    : {len(files)}"
    )

    print(
        f"Warm-up runs     : {WARMUP_RUNS}"
    )

    print(
        f"Measured runs    : {MEASURED_RUNS}"
    )

    print()

    results = []

    # --------------------------------------------------------
    # Process files
    # --------------------------------------------------------

    for file_path in files:

        try:

            result = benchmark_file(
                file_path
            )

            results.append(result)

            print(
                f"{file_path.name:<45} "
                f"avg={result['average']:.4f}s   "
                f"min={result['minimum']:.4f}s   "
                f"max={result['maximum']:.4f}s   "
                f"{result['words']:>6} words"
            )

        except Exception as exc:

            results.append(
                {
                    "file": file_path.name,
                    "average": 0.0,
                    "minimum": 0.0,
                    "maximum": 0.0,
                    "characters": 0,
                    "words": 0,
                    "status": f"FAILED: {exc}",
                }
            )

            print(
                f"{file_path.name:<45} "
                f"FAILED: {exc}"
            )

    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)

    successful = [
        result
        for result in results
        if result["status"] == "SUCCESS"
    ]

    failed = [
        result
        for result in results
        if result["status"] != "SUCCESS"
    ]

    if not successful:

        print(
            "No resumes were successfully processed."
        )

        return

    total_average_time = sum(
        result["average"]
        for result in successful
    )

    average_per_resume = (
        total_average_time
        / len(successful)
    )

    fastest = min(
        successful,
        key=lambda result: result["minimum"],
    )

    slowest = max(
        successful,
        key=lambda result: result["maximum"],
    )

    total_words = sum(
        result["words"]
        for result in successful
    )

    total_characters = sum(
        result["characters"]
        for result in successful
    )

    print(
        f"Successful resumes : "
        f"{len(successful)}"
    )

    print(
        f"Failed resumes     : "
        f"{len(failed)}"
    )

    print(
        f"Total avg time     : "
        f"{total_average_time:.4f} sec"
    )

    print(
        f"Average per resume : "
        f"{average_per_resume:.4f} sec"
    )

    print(
        f"Fastest file       : "
        f"{fastest['file']} "
        f"({fastest['minimum']:.4f} sec)"
    )

    print(
        f"Slowest file       : "
        f"{slowest['file']} "
        f"({slowest['maximum']:.4f} sec)"
    )

    print(
        f"Total words        : "
        f"{total_words}"
    )

    print(
        f"Total characters   : "
        f"{total_characters}"
    )

    # ========================================================
    # FILE SUMMARY
    # ========================================================

    print()
    print("-" * 90)

    print(
        f"{'PDF/DOCX':35}"
        f"{'AVG':12}"
        f"{'MIN':12}"
        f"{'MAX':12}"
        f"{'WORDS':10}"
    )

    print("-" * 90)

    for result in successful:

        print(
            f"{result['file'][:34]:35}"
            f"{result['average']:<12.4f}"
            f"{result['minimum']:<12.4f}"
            f"{result['maximum']:<12.4f}"
            f"{result['words']:<10}"
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    benchmark()