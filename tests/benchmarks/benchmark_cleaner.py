
import statistics
import time
from pathlib import Path
import sys



PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import (
    clean_text as original_clean_text,
)
from document_processing.common.updated_cleaner import (
    clean_text as updated_clean_text,
)


RESUME_DIR = Path("data/resumes")
WARMUP_RUNS = 1
MEASURED_RUNS = 5


def benchmark_function(function, text):
    """Warm up once, then measure repeated cleaner execution."""
    function(text)

    timings = []
    result = None

    for _ in range(MEASURED_RUNS):
        start = time.perf_counter()
        result = function(text)
        timings.append(time.perf_counter() - start)

    return {
        "result": result,
        "average": statistics.mean(timings),
        "median": statistics.median(timings),
        "maximum": max(timings),
    }


def show_first_difference(original, updated, resume_name):
    """Display the first text difference between two cleaner outputs."""
    limit = min(len(original), len(updated))
    index = next(
        (
            i for i in range(limit)
            if original[i] != updated[i]
        ),
        limit,
    )

    if index == limit and len(original) == len(updated):
        return

    start = max(0, index - 60)
    end_original = min(len(original), index + 100)
    end_updated = min(len(updated), index + 100)

    print(f"\n--- OUTPUT DIFFERENCE: {resume_name} ---")
    print(f"First differing character: {index}")
    print(f"Original length: {len(original)}")
    print(f"Updated length : {len(updated)}")
    print(f"Original text  : {original[start:end_original]!r}")
    print(f"Updated text   : {updated[start:end_updated]!r}")
    

def show_cleaner_comparison(raw_text, original_text, updated_text, name):
    print(f"\n--- {name} ---")
    print("RAW     :", repr(raw_text[:180]))
    print("ORIGINAL:", repr(original_text[:180]))
    print("UPDATED :", repr(updated_text[:180]))
    
def main():
    resume_files = sorted(
        path
        for path in RESUME_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".pdf", ".docx"}
    )

    if not resume_files:
        print(f"No PDF or DOCX resumes found in {RESUME_DIR}")
        return

    rows = []

    for resume_path in resume_files:
        try:
            # Extraction is outside the timed cleaner calls.
            raw_text = extract_raw_text(resume_path)

            if not isinstance(raw_text, str):
                raise TypeError(
                    f"Expected extracted text as str, "
                    f"got {type(raw_text).__name__}"
                )

            original = benchmark_function(
                original_clean_text, raw_text
            )
            updated = benchmark_function(
                updated_clean_text, raw_text
            )
            
            
            if original["result"] != updated["result"]:
                show_first_difference(
                    original["result"],
                    updated["result"],
                    resume_path.name,
                )
            
            
            show_cleaner_comparison(
            raw_text,
            original["result"],
            updated["result"],
            resume_path.name,
        )

            old_avg = original["average"]
            new_avg = updated["average"]

            if old_avg > 0:
                change_pct = (
                    (new_avg - old_avg) / old_avg
                ) * 100
            else:
                change_pct = 0.0

            rows.append({
                "resume": resume_path.name,
                "chars": len(raw_text),
                "original_avg": old_avg,
                "updated_avg": new_avg,
                "change_pct": change_pct,
                "outputs_equal": (
                    original["result"] == updated["result"]
                ),
            })

        except Exception as exc:
            print(f"FAILED: {resume_path.name}: {exc}")

    if not rows:
        print("No resumes were benchmarked successfully.")
        return

    print("\n" + "=" * 105)
    print("CLEAN_TEXT PERFORMANCE BENCHMARK")
    print("=" * 105)
    print(
        f"{'Resume':<30} {'Chars':>7} "
        f"{'Original ms':>13} {'Updated ms':>12} "
        f"{'Change %':>10} {'Same output':>12}"
    )
    print("-" * 105)

    for row in rows:
        print(
            f"{row['resume']:<30} "
            f"{row['chars']:>7} "
            f"{row['original_avg'] * 1000:>13.4f} "
            f"{row['updated_avg'] * 1000:>12.4f} "
            f"{row['change_pct']:>9.2f}% "
            f"{str(row['outputs_equal']):>12}"
        )

    old_total = sum(row["original_avg"] for row in rows)
    new_total = sum(row["updated_avg"] for row in rows)

    old_median = statistics.median(
        row["original_avg"] for row in rows
    )
    new_median = statistics.median(
        row["updated_avg"] for row in rows
    )

    overall_change = (
        ((new_total - old_total) / old_total) * 100
        if old_total > 0
        else 0.0
    )

    different_outputs = sum(
        not row["outputs_equal"] for row in rows
    )

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Resumes benchmarked       : {len(rows)}")
    print(f"Warm-up runs per version : {WARMUP_RUNS}")
    print(f"Measured runs per version: {MEASURED_RUNS}")
    print(f"Original total avg time  : {old_total * 1000:.4f} ms")
    print(f"Updated total avg time   : {new_total * 1000:.4f} ms")
    print(f"Original median/resume   : {old_median * 1000:.4f} ms")
    print(f"Updated median/resume    : {new_median * 1000:.4f} ms")
    print(f"Overall time change      : {overall_change:.2f}%")
    print(f"Different outputs        : {different_outputs}/{len(rows)}")

    if overall_change < 0:
        print("Result: Updated cleaner was faster in this run.")
    elif overall_change > 0:
        print("Result: Updated cleaner was slower in this run.")
    else:
        print("Result: No measured total-time difference.")


if __name__ == "__main__":
    main()