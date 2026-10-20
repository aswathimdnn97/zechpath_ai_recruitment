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
DEFAULT_BASELINE_ROOT = PROJECT_ROOT / "data" / "regression" / "baseline"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "regression" / "optimized"
DEFAULT_RESUME_ROOT = PROJECT_ROOT / "data" / "resumes"
DEFAULT_PARSED_JD_ROOT = PROJECT_ROOT / "data" / "extracted" / "jd"
SNAPSHOT_TYPES = ("candidate_profile", "scoring_result")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, indent=2, ensure_ascii=False, default=str)
        file.write("\n")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def discover_resumes(resume_root: Path) -> dict[str, Path]:
    if not resume_root.is_dir():
        raise FileNotFoundError(f"Resume directory not found: {resume_root}")

    resumes: dict[str, Path] = {}
    for path in resume_root.rglob("*"):
        if path.is_file():
            file_hash = sha256_file(path)
            resumes.setdefault(file_hash, path)
    return resumes


def load_baseline_profiles(baseline_root: Path) -> dict[str, dict[str, Any]]:
    profile_dir = baseline_root / "candidate_profile"
    if not profile_dir.is_dir():
        raise FileNotFoundError(
            f"Baseline profile directory not found: {profile_dir}"
        )

    profiles = {}
    for path in sorted(profile_dir.glob("*.json")):
        candidate_id = path.stem
        data = load_json(path)
        if not isinstance(data, dict):
            raise ValueError(f"Baseline profile must be a JSON object: {path}")

        resume_hash = data.get("resume_hash")
        if not isinstance(resume_hash, str) or not resume_hash:
            raise ValueError(
                f"Baseline profile is missing resume_hash: {path}"
            )
        profiles[candidate_id] = data

    if not profiles:
        raise ValueError(f"No baseline profiles found in {profile_dir}")
    return profiles


def load_baseline_scoring_cases(
    baseline_root: Path,
) -> list[tuple[Path, dict[str, Any]]]:
    scoring_dir = baseline_root / "scoring_result"
    if not scoring_dir.is_dir():
        raise FileNotFoundError(
            f"Baseline scoring directory not found: {scoring_dir}"
        )

    cases = []
    for path in sorted(scoring_dir.rglob("*.json")):
        data = load_json(path)
        if not isinstance(data, dict):
            raise ValueError(f"Baseline score must be a JSON object: {path}")
        for key in ("candidate_id", "job_id", "jd_id"):
            if not isinstance(data.get(key), str) or not data[key]:
                raise ValueError(
                    f"Baseline score is missing '{key}': {path}"
                )
        cases.append((path.relative_to(scoring_dir), data))

    if not cases:
        raise ValueError(f"No baseline scoring cases found in {scoring_dir}")
    return cases


def set_candidate_id(profile_result: dict[str, Any], candidate_id: str) -> None:
    profile_result["candidate_id"] = candidate_id
    for key in ("masked_profile", "original_profile"):
        profile = profile_result.get(key)
        if not isinstance(profile, dict):
            raise ValueError(
                f"Current resume pipeline result is missing '{key}'."
            )
        profile["candidate_id"] = candidate_id


def current_score(
    candidate_id: str,
    profile_result: dict[str, Any],
    baseline_score: dict[str, Any],
    parsed_jd_root: Path,
    embedding_generator: Any,
) -> dict[str, Any]:
    from embeddings.embedding_text_builder import (
        build_jd_embedding_text,
        profile_to_embedding_text,
    )
    from scoring.ats_scoring_engine import calculate_ats_score

    masked_profile = profile_result["masked_profile"]
    if "personal_information" in masked_profile:
        raise ValueError(
            f"Masked profile unexpectedly contains personal information: "
            f"{candidate_id}"
        )

    job_id = baseline_score["job_id"]
    jd_path = parsed_jd_root / f"{job_id}.json"
    if not jd_path.is_file():
        raise FileNotFoundError(
            f"Parsed JD snapshot not found for scoring case: {jd_path}"
        )
    job_description = load_json(jd_path)
    if not isinstance(job_description, dict):
        raise ValueError(f"Parsed JD must be a JSON object: {jd_path}")

    resume_text = profile_to_embedding_text(masked_profile)
    jd_text = build_jd_embedding_text(job_description)
    if not resume_text:
        raise ValueError(
            f"Current parsed profile produced empty embedding text: "
            f"{candidate_id}"
        )
    if not jd_text:
        raise ValueError(f"Parsed JD produced empty embedding text: {jd_path}")

    resume_embedding = embedding_generator.generate_embedding(resume_text)
    jd_embedding = embedding_generator.generate_embedding(jd_text)

    result = calculate_ats_score(
        candidate_profile=masked_profile,
        jd_profile=job_description,
        resume_embedding=resume_embedding,
        jd_embedding=jd_embedding,
        embedding_generator=embedding_generator,
    )
    if not isinstance(result, dict):
        raise ValueError(
            f"ATS scorer returned a non-object result for {candidate_id}."
        )

    candidate_score = result.get("candidate_score")
    final_score = (
        candidate_score.get("final_score")
        if isinstance(candidate_score, dict)
        else None
    )
    if not isinstance(final_score, (int, float)) or not 0 <= final_score <= 100:
        raise ValueError(
            f"ATS scorer returned an invalid final score for {candidate_id}."
        )

    original_profile = profile_result["original_profile"]
    personal_information = original_profile.get("personal_information", {})
    candidate_name = (
        personal_information.get("name", "")
        if isinstance(personal_information, dict)
        else ""
    )
    jd_id = Path(baseline_score["jd_id"]).stem
    jd_file = PROJECT_ROOT / "data" / "job_descriptions" / f"{jd_id}.pdf"
    if not jd_file.is_file():
        raise FileNotFoundError(f"JD source PDF not found: {jd_file}")

    result.update(
        {
            "candidate_id": candidate_id,
            "candidate_name": candidate_name,
            "jd_id": jd_id,
            "job_id": job_id,
            "jd_file": jd_file.name,
        }
    )
    return result


def install_snapshots(
    staged_root: Path,
    output_root: Path,
    overwrite: bool,
) -> None:
    existing_paths = [
        output_root / snapshot_type
        for snapshot_type in SNAPSHOT_TYPES
        if (output_root / snapshot_type).exists()
    ]
    has_existing_snapshots = any(
        not path.is_dir() or any(path.iterdir())
        for path in existing_paths
    )
    if has_existing_snapshots and not overwrite:
        raise FileExistsError(
            "Optimized snapshot data already exists. "
            "Use --overwrite to replace them: "
            + ", ".join(str(path) for path in existing_paths)
        )

    backup_root = staged_root / "previous"
    backup_root.mkdir()
    moved_old: list[tuple[Path, Path]] = []
    installed: list[Path] = []
    try:
        for target in existing_paths:
            backup = backup_root / target.name
            os.replace(target, backup)
            moved_old.append((backup, target))

        for snapshot_type in SNAPSHOT_TYPES:
            staged_dir = staged_root / snapshot_type
            target = output_root / snapshot_type
            os.replace(staged_dir, target)
            installed.append(target)
    except OSError:
        for target in installed:
            shutil.rmtree(target)
        for backup, target in reversed(moved_old):
            os.replace(backup, target)
        raise


def generate(
    baseline_root: Path,
    output_root: Path,
    resume_root: Path,
    parsed_jd_root: Path,
    overwrite: bool,
) -> tuple[int, int]:
    from document_processing.resume.resume_pipeline import resume_pipeline

    baseline_profiles = load_baseline_profiles(baseline_root)
    scoring_cases = load_baseline_scoring_cases(baseline_root)
    resumes_by_hash = discover_resumes(resume_root)

    resume_paths: dict[str, Path] = {}
    for candidate_id, baseline_profile in baseline_profiles.items():
        resume_hash = baseline_profile["resume_hash"]
        resume_path = resumes_by_hash.get(resume_hash)
        if resume_path is None:
            raise FileNotFoundError(
                f"No source resume matches baseline candidate "
                f"{candidate_id} (SHA-256 {resume_hash})."
            )
        resume_paths[candidate_id] = resume_path

    for relative_path, baseline_score in scoring_cases:
        if baseline_score["candidate_id"] not in baseline_profiles:
            raise ValueError(
                f"Scoring case references a candidate with no baseline "
                f"profile: {relative_path}"
            )
        if not (parsed_jd_root / f"{baseline_score['job_id']}.json").is_file():
            raise FileNotFoundError(
                "Parsed JD snapshot is missing for scoring case "
                f"{relative_path}: "
                f"{parsed_jd_root / (baseline_score['job_id'] + '.json')}"
            )

    output_root.mkdir(parents=True, exist_ok=True)
    has_existing_snapshots = any(
        path.exists() and (not path.is_dir() or any(path.iterdir()))
        for path in (
            output_root / snapshot_type
            for snapshot_type in SNAPSHOT_TYPES
        )
    )
    if not overwrite and has_existing_snapshots:
        raise FileExistsError(
            f"Optimized snapshot data already exists under {output_root}; "
            "rerun with --overwrite to replace it."
        )

    with tempfile.TemporaryDirectory(
        prefix=".optimized-regression-",
        dir=output_root.parent,
    ) as temporary_dir:
        staged_root = Path(temporary_dir)
        for snapshot_type in SNAPSHOT_TYPES:
            (staged_root / snapshot_type).mkdir()

        profiles: dict[str, dict[str, Any]] = {}
        for index, (candidate_id, resume_path) in enumerate(
            sorted(resume_paths.items()),
            start=1,
        ):
            print(
                f"[PARSE {index}/{len(resume_paths)}] "
                f"{candidate_id} <- {resume_path.name}"
            )
            result = resume_pipeline(
                str(resume_path),
                save_profile=False,
            )
            if not isinstance(result, dict):
                raise ValueError(
                    f"Resume pipeline returned invalid data for "
                    f"{candidate_id}."
                )
            set_candidate_id(result, candidate_id)
            result["resume_hash"] = baseline_profiles[candidate_id][
                "resume_hash"
            ]
            profiles[candidate_id] = result
            write_json(
                staged_root
                / "candidate_profile"
                / f"{candidate_id}.json",
                result,
            )

        from embeddings.embedding_generator import EmbeddingGenerator

        embedding_generator = EmbeddingGenerator()
        for index, (relative_path, baseline_score) in enumerate(
            scoring_cases,
            start=1,
        ):
            candidate_id = baseline_score["candidate_id"]
            print(
                f"[SCORE {index}/{len(scoring_cases)}] "
                f"{baseline_score['job_id']} / {candidate_id}"
            )
            result = current_score(
                candidate_id,
                profiles[candidate_id],
                baseline_score,
                parsed_jd_root,
                embedding_generator,
            )
            write_json(
                staged_root / "scoring_result" / relative_path,
                result,
            )

        install_snapshots(staged_root, output_root, overwrite)

    return len(profiles), len(scoring_cases)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the current resume parser and ATS scorer using the source "
            "resumes and JD snapshots referenced by the baseline."
        )
    )
    parser.add_argument(
        "--baseline-root",
        type=Path,
        default=DEFAULT_BASELINE_ROOT,
        help="Baseline directory containing candidate_profile/ and scoring_result/.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output directory for optimized snapshots.",
    )
    parser.add_argument(
        "--resume-root",
        type=Path,
        default=DEFAULT_RESUME_ROOT,
        help="Directory containing source resume files.",
    )
    parser.add_argument(
        "--parsed-jd-root",
        type=Path,
        default=DEFAULT_PARSED_JD_ROOT,
        help="Directory containing parsed JD JSON keyed by job_id.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing optimized snapshot directories after generation succeeds.",
    )
    args = parser.parse_args()

    try:
        profile_count, scoring_count = generate(
            args.baseline_root,
            args.output_root,
            args.resume_root,
            args.parsed_jd_root,
            args.overwrite,
        )
    except Exception as exc:
        parser.exit(2, f"Generation failed: {exc}\n")

    print("\nOptimized regression snapshots generated.")
    print(f"Candidate profiles: {profile_count}")
    print(f"Scoring results   : {scoring_count}")
    print(f"Output directory  : {args.output_root}")
    print("Baseline and live candidate/scoring data were not modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
