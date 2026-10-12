import argparse
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from document_processing.resume.resume_pipeline import resume_pipeline


RESUME_DIR = PROJECT_ROOT / "data" / "resumes"



from statistics import mean, median

WARMUP_RUNS = 1
MEASURED_RUNS = 5


def benchmark_resume(resume_path: Path):
    # ---------------------------------------------------------
    # Warm-up
    # ---------------------------------------------------------
    for _ in range(WARMUP_RUNS):
        resume_pipeline(
            resume_path,
            save_profile=False,
            debug=False,
            profile=False,
        )

    # ---------------------------------------------------------
    # Measured runs
    # ---------------------------------------------------------
    times = []

    for _ in range(MEASURED_RUNS):
        start = time.perf_counter()

        resume_pipeline(
            resume_path,
            save_profile=False,
            debug=False,
            profile=True,
        )

        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        "resume": resume_path.name,
        "average": mean(times),
        "median": median(times),
        "minimum": min(times),
        "maximum": max(times),
        "runs": times,
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark the resume pipeline for every resume in the configured "
            "directory, or for one specified resume."
        )
    )
    parser.add_argument(
        "resume",
        nargs="?",
        help="Optional PDF/DOCX filename from the configured resume directory.",
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help=(
            "Run the selected resume once with parser debug output and "
            "per-stage timings before benchmarking."
        ),
    )
    args = parser.parse_args()

    resumes = sorted(
        p for p in RESUME_DIR.iterdir()
        if p.suffix.lower() in {".pdf", ".docx"}
    )

    if args.resume:
        requested_name = Path(args.resume).name
        resumes = [
            resume
            for resume in resumes
            if resume.name.lower() == requested_name.lower()
        ]
        if not resumes:
            parser.error(
                f"Resume not found in {RESUME_DIR}: {args.resume}"
            )

    if args.diagnose and len(resumes) != 1:
        parser.error("--diagnose requires exactly one resume filename.")

    print("=" * 90)
    print("FINAL ATS RESUME PIPELINE RESPONSE-TIME BENCHMARK")
    print("=" * 90)

    print(f"Resume directory : {RESUME_DIR.resolve()}")
    print(f"Total resumes    : {len(resumes)}")
    print(f"Warm-up runs     : {WARMUP_RUNS}")
    print(f"Measured runs    : {MEASURED_RUNS}")
    print()

    if args.diagnose:
        resume_path = resumes[0]
        print("=" * 90)
        print(f"PIPELINE EXTRACTION DIAGNOSTICS: {resume_path.name}")
        print("=" * 90)
        resume_pipeline(
            resume_path,
            save_profile=False,
            debug=True,
            profile=True,
        )
        print("=" * 90)
        print()

    results = []

    for resume_path in resumes:
        print(f"Benchmarking: {resume_path.name}")

        result = benchmark_resume(resume_path)
        results.append(result)

        print(
            f"  avg={result['average']:.4f}s  "
            f"median={result['median']:.4f}s  "
            f"min={result['minimum']:.4f}s  "
            f"max={result['maximum']:.4f}s"
        )

    # ---------------------------------------------------------
    # Overall statistics
    # ---------------------------------------------------------
    averages = [r["average"] for r in results]

    print()
    print("=" * 90)
    print("FINAL BENCHMARK SUMMARY")
    print("=" * 90)

    if averages:
        print(f"Average response time : {mean(averages):.4f} s")
        print(f"Median response time  : {median(averages):.4f} s")
        print(f"Fastest resume        : {min(averages):.4f} s")
        print(f"Slowest resume        : {max(averages):.4f} s")

        below_500ms = sum(t < 0.5 for t in averages)
        below_1s = sum(t < 1.0 for t in averages)

        print()
        print(
            f"Resumes < 0.5 s       : "
            f"{below_500ms}/{len(averages)}"
        )

        print(
            f"Resumes < 1.0 s       : "
            f"{below_1s}/{len(averages)}"
        )

    # ---------------------------------------------------------
    # Detailed table
    # ---------------------------------------------------------
    print()
    print("=" * 90)
    print("PER-RESUME RESULTS")
    print("=" * 90)

    print(
        f"{'Resume':<35}"
        f"{'Average':>12}"
        f"{'Median':>12}"
        f"{'Min':>12}"
        f"{'Max':>12}"
    )

    print("-" * 90)

    for result in results:
        print(
            f"{result['resume']:<35}"
            f"{result['average']:>10.4f}s"
            f"{result['median']:>10.4f}s"
            f"{result['minimum']:>10.4f}s"
            f"{result['maximum']:>10.4f}s"
        )

    print("=" * 90)


if __name__ == "__main__":
    main()