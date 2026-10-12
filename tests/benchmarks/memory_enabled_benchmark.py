import argparse
from pathlib import Path
import sys
import time
import threading

import psutil

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from document_processing.resume.resume_pipeline import resume_pipeline


RESUME_DIR = PROJECT_ROOT / "data" / "resumes"

from statistics import mean, median


WARMUP_RUNS = 1
MEASURED_RUNS = 5

# Memory sampling interval.
# 10 ms gives a good balance between accuracy and overhead.
MEMORY_SAMPLE_INTERVAL = 0.01


# ---------------------------------------------------------
# Process memory helper
# ---------------------------------------------------------
PROCESS = psutil.Process()


def get_memory_mb():
    """
    Return current process RSS memory in MB.
    """
    return PROCESS.memory_info().rss / (1024 * 1024)


# ---------------------------------------------------------
# Peak memory monitor
# ---------------------------------------------------------
class MemoryMonitor:
    """
    Monitor process RSS while the resume pipeline is running.
    """

    def __init__(self, interval=MEMORY_SAMPLE_INTERVAL):
        self.interval = interval
        self.peak_mb = 0.0
        self.running = False
        self.thread = None

    def _monitor(self):
        while self.running:
            memory_mb = get_memory_mb()

            if memory_mb > self.peak_mb:
                self.peak_mb = memory_mb

            time.sleep(self.interval)

    def start(self):
        """
        Start monitoring process RSS.
        """

        # Capture memory before starting the thread.
        self.peak_mb = get_memory_mb()

        self.running = True

        self.thread = threading.Thread(
            target=self._monitor,
            daemon=True,
        )

        self.thread.start()

    def stop(self):
        """
        Stop monitoring and return peak RSS.
        """

        self.running = False

        if self.thread is not None:
            self.thread.join()

        # Final memory check so we don't miss the last measurement.
        final_mb = get_memory_mb()

        if final_mb > self.peak_mb:
            self.peak_mb = final_mb

        return self.peak_mb


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

    memory_before = []
    memory_after = []
    memory_deltas = []
    peak_memories = []

    for _ in range(MEASURED_RUNS):

        # Memory immediately before pipeline execution.
        before_mb = get_memory_mb()

        # Start peak memory monitoring.
        monitor = MemoryMonitor()
        monitor.start()

        start = time.perf_counter()

        resume_pipeline(
            resume_path,
            save_profile=False,
            debug=False,
            profile=False,
        )

        elapsed = time.perf_counter() - start

        # Stop monitor after pipeline execution.
        peak_mb = monitor.stop()

        # Memory immediately after pipeline execution.
        after_mb = get_memory_mb()

        delta_mb = after_mb - before_mb

        # Store measurements.
        times.append(elapsed)

        memory_before.append(before_mb)
        memory_after.append(after_mb)
        memory_deltas.append(delta_mb)
        peak_memories.append(peak_mb)

    return {
        "resume": resume_path.name,

        # -----------------------------------------------------
        # Timing
        # -----------------------------------------------------
        "average": mean(times),
        "median": median(times),
        "minimum": min(times),
        "maximum": max(times),
        "runs": times,

        # -----------------------------------------------------
        # Memory
        # -----------------------------------------------------
        "memory_before": mean(memory_before),
        "memory_after": mean(memory_after),
        "memory_delta": mean(memory_deltas),

        # TRUE peak RSS while pipeline is running.
        "peak_memory": max(peak_memories),

        "memory_deltas": memory_deltas,
        "peak_memories": peak_memories,
    }


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Benchmark the resume pipeline for every resume in the configured "
            "directory, or for one specified resume."
        ),
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
        p
        for p in RESUME_DIR.iterdir()
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

    print("=" * 100)
    print("FINAL ATS RESUME PIPELINE RESPONSE-TIME + PEAK MEMORY BENCHMARK")
    print("=" * 100)

    print(f"Resume directory       : {RESUME_DIR.resolve()}")
    print(f"Total resumes          : {len(resumes)}")
    print(f"Warm-up runs           : {WARMUP_RUNS}")
    print(f"Measured runs          : {MEASURED_RUNS}")
    print(f"Memory sample interval : {MEMORY_SAMPLE_INTERVAL:.3f} s")
    print(f"Initial RSS            : {get_memory_mb():.2f} MB")
    print()

    # ---------------------------------------------------------
    # Optional diagnostics
    # ---------------------------------------------------------
    if args.diagnose:

        resume_path = resumes[0]

        print("=" * 100)
        print(
            f"PIPELINE EXTRACTION DIAGNOSTICS: "
            f"{resume_path.name}"
        )
        print("=" * 100)

        resume_pipeline(
            resume_path,
            save_profile=False,
            debug=True,
            profile=True,
        )

        print("=" * 100)
        print()

    results = []

    # ---------------------------------------------------------
    # Benchmark every resume
    # ---------------------------------------------------------
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

        print(
            f"  memory before={result['memory_before']:.2f} MB  "
            f"after={result['memory_after']:.2f} MB  "
            f"delta={result['memory_delta']:+.2f} MB  "
            f"peak={result['peak_memory']:.2f} MB"
        )

    # ---------------------------------------------------------
    # Overall statistics
    # ---------------------------------------------------------
    averages = [
        r["average"]
        for r in results
    ]

    peak_memories = [
        r["peak_memory"]
        for r in results
    ]

    memory_deltas = [
        r["memory_delta"]
        for r in results
    ]

    final_memory = get_memory_mb()

    print()
    print("=" * 100)
    print("FINAL BENCHMARK SUMMARY")
    print("=" * 100)

    if averages:

        print(
            f"Average response time : "
            f"{mean(averages):.4f} s"
        )

        print(
            f"Median response time  : "
            f"{median(averages):.4f} s"
        )

        print(
            f"Fastest resume        : "
            f"{min(averages):.4f} s"
        )

        print(
            f"Slowest resume        : "
            f"{max(averages):.4f} s"
        )

        print()

        print(
            f"Average memory delta  : "
            f"{mean(memory_deltas):+.2f} MB"
        )

        print(
            f"Maximum peak RSS      : "
            f"{max(peak_memories):.2f} MB"
        )

        print(
            f"Final process RSS     : "
            f"{final_memory:.2f} MB"
        )

        below_500ms = sum(
            t < 0.5
            for t in averages
        )

        below_1s = sum(
            t < 1.0
            for t in averages
        )

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
    print("=" * 100)
    print("PER-RESUME RESULTS")
    print("=" * 100)

    print(
        f"{'Resume':<35}"
        f"{'Average':>10}"
        f"{'Median':>10}"
        f"{'Min':>10}"
        f"{'Max':>10}"
        f"{'Mem Before':>14}"
        f"{'Mem After':>14}"
        f"{'Delta':>12}"
        f"{'Peak RSS':>14}"
    )

    print("-" * 100)

    for result in results:

        print(
            f"{result['resume']:<35}"
            f"{result['average']:>9.4f}s"
            f"{result['median']:>9.4f}s"
            f"{result['minimum']:>9.4f}s"
            f"{result['maximum']:>9.4f}s"
            f"{result['memory_before']:>12.2f} MB"
            f"{result['memory_after']:>12.2f} MB"
            f"{result['memory_delta']:>+10.2f} MB"
            f"{result['peak_memory']:>12.2f} MB"
        )

    print("=" * 100)


if __name__ == "__main__":
    main()
