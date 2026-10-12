
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import clean_text
from document_processing.common.handling_layout import fix_layout


RESUME_DIR = PROJECT_ROOT / "data" / "resumes"
WARMUP_RUNS = 1
MEASURED_RUNS = 5


def benchmark_resume(resume_path):
    raw_text = extract_raw_text(resume_path)
    cleaned_text = clean_text(raw_text)

    # Warm-up runs
    for _ in range(WARMUP_RUNS):
        fix_layout(cleaned_text)

    timings = []
    result = None

    for _ in range(MEASURED_RUNS):
        start = time.perf_counter_ns()
        current_result = fix_layout(cleaned_text)
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000

        timings.append(elapsed_ms)
        result = current_result

    return {
        "filename": resume_path.name,
        "characters": len(cleaned_text),
        "median_ms": statistics.median(timings),
        "average_ms": statistics.mean(timings),
        "result": result,
    }


def main():
    resume_paths = sorted(RESUME_DIR.glob("*.pdf"))

    print("=" * 85)
    print("FIX_LAYOUT PERFORMANCE BASELINE")
    print("=" * 85)
    print(
        f"{'Resume':30} {'Chars':>8} "
        f"{'Median ms':>12} {'Average ms':>12}"
    )
    print("-" * 85)

    results = []

    for resume_path in resume_paths:
        try:
            result = benchmark_resume(resume_path)
            results.append(result)

            print(
                f"{result['filename']:30} "
                f"{result['characters']:8} "
                f"{result['median_ms']:12.4f} "
                f"{result['average_ms']:12.4f}"
            )
        except Exception as exc:
            print(f"FAILED: {resume_path.name}: {exc}")

    if results:
        print("-" * 85)
        print(f"Successful resumes: {len(results)}")
        print(
            "Median of resume medians: "
            f"{statistics.median(r['median_ms'] for r in results):.4f} ms"
        )
        print(
            "Average of resume averages: "
            f"{statistics.mean(r['average_ms'] for r in results):.4f} ms"
        )


if __name__ == "__main__":
    main()