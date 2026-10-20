from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_BASELINE_DIR = (
    PROJECT_ROOT / "data" / "regression" / "baseline" / "candidate_profile"
)
DEFAULT_RESUME_DIR = PROJECT_ROOT / "data" / "resumes"
DEFAULT_OUTPUT_DIR = (
    PROJECT_ROOT / "data" / "regression" / "optimized" / "candidate_profile"
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def find_resumes_by_hash(resume_dir: Path) -> dict[str, Path]:
    if not resume_dir.is_dir():
        raise FileNotFoundError(f"Resume directory not found: {resume_dir}")

    resumes_by_hash: dict[str, Path] = {}
    for path in sorted(resume_dir.rglob("*")):
        if path.is_file():
            # Identical PDF copies are valid; use the first deterministic path.
            resumes_by_hash.setdefault(sha256_file(path), path)
    return resumes_by_hash


def load_baseline_profiles(
    baseline_dir: Path,
) -> dict[str, dict[str, Any]]:
    if not baseline_dir.is_dir():
        raise FileNotFoundError(
            f"Baseline candidate profile directory not found: {baseline_dir}"
        )

    profiles: dict[str, dict[str, Any]] = {}
    for path in sorted(baseline_dir.glob("*.json")):
        data = load_json(path)
        if not isinstance(data, dict):
            raise ValueError(f"Baseline profile must be a JSON object: {path}")
        resume_hash = data.get("resume_hash")
        if not isinstance(resume_hash, str) or not resume_hash:
            raise ValueError(f"Baseline profile has no resume_hash: {path}")
        profiles[path.stem] = data

    if not profiles:
        raise ValueError(f"No baseline candidate profiles found in {baseline_dir}")
    return profiles


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False, default=str)
        file.write("\n")


def install_output(staged_dir: Path, output_dir: Path, overwrite: bool) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    if output_dir.exists() and not overwrite:
        raise FileExistsError(
            f"Optimized profiles already exist at {output_dir}. "
            "Use --overwrite to replace them."
        )

    backup_dir = staged_dir.parent / "previous_candidate_profile"
    moved_existing = False
    try:
        if output_dir.exists():
            os.replace(output_dir, backup_dir)
            moved_existing = True
        os.replace(staged_dir, output_dir)
    except OSError:
        if moved_existing and backup_dir.exists() and not output_dir.exists():
            os.replace(backup_dir, output_dir)
        raise


def generate_profiles(
    baseline_dir: Path,
    resume_dir: Path,
    output_dir: Path,
    overwrite: bool,
) -> int:
    from document_processing.resume.resume_pipeline import resume_pipeline

    baseline_profiles = load_baseline_profiles(baseline_dir)
    resumes_by_hash = find_resumes_by_hash(resume_dir)
    source_resumes: dict[str, Path] = {}

    for candidate_id, baseline in baseline_profiles.items():
        resume_hash = baseline["resume_hash"]
        resume_path = resumes_by_hash.get(resume_hash)
        if resume_path is None:
            raise FileNotFoundError(
                f"No source resume matches {candidate_id} "
                f"(SHA-256 {resume_hash})."
            )
        source_resumes[candidate_id] = resume_path

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix=".optimized-profiles-",
        dir=output_dir.parent,
    ) as temporary_dir:
        staging_root = Path(temporary_dir)
        staged_dir = staging_root / "candidate_profile"
        staged_dir.mkdir()

        total = len(source_resumes)
        for index, (candidate_id, resume_path) in enumerate(
            sorted(source_resumes.items()),
            start=1,
        ):
            print(
                f"[PARSE {index}/{total}] "
                f"{candidate_id} <- {resume_path.name}"
            )
            result = resume_pipeline(
                str(resume_path),
                save_profile=False,
            )
            if not isinstance(result, dict):
                raise ValueError(
                    f"Resume pipeline returned invalid output for {candidate_id}."
                )

            for profile_key in ("masked_profile", "original_profile"):
                profile = result.get(profile_key)
                if not isinstance(profile, dict):
                    raise ValueError(
                        f"Resume pipeline result for {candidate_id} "
                        f"is missing '{profile_key}'."
                    )
                profile["candidate_id"] = candidate_id

            result["candidate_id"] = candidate_id
            result["resume_hash"] = baseline_profiles[candidate_id]["resume_hash"]
            write_json(staged_dir / f"{candidate_id}.json", result)

        install_output(staged_dir, output_dir, overwrite)

    return len(source_resumes)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Rerun the current resume pipeline for every baseline candidate "
            "and save optimized candidate-profile snapshots."
        )
    )
    parser.add_argument(
        "--baseline-dir",
        type=Path,
        default=DEFAULT_BASELINE_DIR,
        help="Directory containing the old candidate profile JSON files.",
    )
    parser.add_argument(
        "--resume-dir",
        type=Path,
        default=DEFAULT_RESUME_DIR,
        help="Directory searched for source resumes matching baseline hashes.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where optimized candidate profile JSON files are saved.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the existing optimized profile directory after parsing succeeds.",
    )
    args = parser.parse_args()

    try:
        count = generate_profiles(
            args.baseline_dir,
            args.resume_dir,
            args.output_dir,
            args.overwrite,
        )
    except Exception as exc:
        parser.exit(2, f"Generation failed: {exc}\n")

    print(f"\nGenerated {count} optimized candidate profiles.")
    print(f"Output directory: {args.output_dir}")
    print("Baseline profiles and live candidate data were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
