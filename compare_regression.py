from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_BASELINE_ROOT = PROJECT_ROOT / "data" / "regression" / "baseline"
DEFAULT_OPTIMIZED_ROOT = PROJECT_ROOT / "data" / "regression" / "optimized"
SNAPSHOT_TYPES = ("candidate_profile", "scoring_result")
MISSING = object()


def values_equal(
    baseline: Any,
    optimized: Any,
    tolerance: float,
) -> bool:
    if (
        isinstance(baseline, (int, float))
        and not isinstance(baseline, bool)
        and isinstance(optimized, (int, float))
        and not isinstance(optimized, bool)
    ):
        return math.isclose(
            float(baseline),
            float(optimized),
            rel_tol=0.0,
            abs_tol=tolerance,
        )

    return type(baseline) is type(optimized) and baseline == optimized


def collect_differences(
    baseline: Any,
    optimized: Any,
    path: str = "$",
    tolerance: float = 0.0,
) -> list[tuple[str, Any, Any]]:
    if isinstance(baseline, dict) and isinstance(optimized, dict):
        differences = []
        for key in sorted(baseline.keys() | optimized.keys(), key=str):
            child_path = f"{path}.{key}"
            old_value = baseline.get(key, MISSING)
            new_value = optimized.get(key, MISSING)
            if old_value is MISSING or new_value is MISSING:
                differences.append((child_path, old_value, new_value))
            else:
                differences.extend(
                    collect_differences(
                        old_value,
                        new_value,
                        child_path,
                        tolerance,
                    )
                )
        return differences

    if isinstance(baseline, list) and isinstance(optimized, list):
        differences = []
        common_length = min(len(baseline), len(optimized))
        for index in range(common_length):
            differences.extend(
                collect_differences(
                    baseline[index],
                    optimized[index],
                    f"{path}[{index}]",
                    tolerance,
                )
            )
        for index in range(common_length, max(len(baseline), len(optimized))):
            differences.append(
                (
                    f"{path}[{index}]",
                    baseline[index] if index < len(baseline) else MISSING,
                    optimized[index] if index < len(optimized) else MISSING,
                )
            )
        return differences

    if values_equal(baseline, optimized, tolerance):
        return []

    return [(path, baseline, optimized)]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def display_value(value: Any) -> str:
    if value is MISSING:
        return "<missing>"
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def compare_snapshot_type(
    snapshot_type: str,
    baseline_root: Path,
    optimized_root: Path,
    tolerance: float,
) -> tuple[int, int]:
    baseline_dir = baseline_root / snapshot_type
    optimized_dir = optimized_root / snapshot_type

    if not baseline_dir.is_dir():
        print(f"[ERROR] Missing baseline directory: {baseline_dir}")
        return 0, 1
    if not optimized_dir.is_dir():
        print(f"[ERROR] Missing optimized directory: {optimized_dir}")
        return 0, 1

    baseline_files = {
        path.relative_to(baseline_dir)
        for path in baseline_dir.rglob("*.json")
    }
    optimized_files = {
        path.relative_to(optimized_dir)
        for path in optimized_dir.rglob("*.json")
    }

    if not baseline_files:
        print(f"[ERROR] No baseline JSON snapshots in {baseline_dir}")
        return 0, 1
    if not optimized_files:
        print(f"[ERROR] No optimized JSON snapshots in {optimized_dir}")
        return 0, 1

    difference_count = 0
    error_count = 0

    print(f"\n[{snapshot_type}]")
    for relative_path in sorted(baseline_files | optimized_files):
        baseline_file = baseline_dir / relative_path
        optimized_file = optimized_dir / relative_path
        display_path = str(Path(snapshot_type) / relative_path)

        if relative_path not in optimized_files:
            print(f"[MISSING OPTIMIZED] {display_path}")
            difference_count += 1
            continue
        if relative_path not in baseline_files:
            print(f"[MISSING BASELINE]  {display_path}")
            difference_count += 1
            continue

        try:
            baseline_data = load_json(baseline_file)
            optimized_data = load_json(optimized_file)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[ERROR] {display_path}: {exc}")
            error_count += 1
            continue

        differences = collect_differences(
            baseline_data,
            optimized_data,
            tolerance=tolerance,
        )
        if not differences:
            print(f"[SAME] {display_path}")
            continue

        print(f"[DIFFERENT] {display_path} ({len(differences)} field(s))")
        difference_count += len(differences)
        for field_path, baseline_value, optimized_value in differences:
            print(f"  {field_path}")
            print(f"    baseline : {display_value(baseline_value)}")
            print(f"    optimized: {display_value(optimized_value)}")

    return difference_count, error_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare baseline and optimized candidate profiles and scoring "
            "results stored as JSON snapshots."
        )
    )
    parser.add_argument(
        "--baseline-root",
        type=Path,
        default=DEFAULT_BASELINE_ROOT,
        help="Directory containing candidate_profile/ and scoring_result/.",
    )
    parser.add_argument(
        "--optimized-root",
        type=Path,
        default=DEFAULT_OPTIMIZED_ROOT,
        help="Directory containing candidate_profile/ and scoring_result/.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=1e-6,
        help="Absolute tolerance for numeric JSON values (default: 1e-6).",
    )
    args = parser.parse_args()

    if args.tolerance < 0:
        parser.error("--tolerance must be non-negative")

    total_differences = 0
    total_errors = 0
    for snapshot_type in SNAPSHOT_TYPES:
        differences, errors = compare_snapshot_type(
            snapshot_type,
            args.baseline_root,
            args.optimized_root,
            args.tolerance,
        )
        total_differences += differences
        total_errors += errors

    print("\n" + "=" * 72)
    print(f"Total differences: {total_differences}")
    print(f"Total errors     : {total_errors}")
    if total_errors:
        print("Comparison incomplete; resolve the reported errors.")
        return 2
    if total_differences:
        print("Regression differences found.")
        return 1
    print("All baseline and optimized snapshots match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
