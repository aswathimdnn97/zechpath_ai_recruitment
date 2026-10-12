from pathlib import Path
import shutil


# ============================================================
# PROJECT DIRECTORIES
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent

SOURCE_PROFILE_DIR = (
    PROJECT_ROOT
    / "data"
    / "candidates"
    / "candidate_profile"
)

SOURCE_SCORING_DIR = (
    PROJECT_ROOT
    / "data"
    / "candidates"
    / "scoring_results"
)


BASELINE_PROFILE_DIR = (
    PROJECT_ROOT
    / "data"
    / "regression"
    / "baseline"
    / "candidate_profile"
)

BASELINE_SCORING_DIR = (
    PROJECT_ROOT
    / "data"
    / "regression"
    / "baseline"
    / "scoring_results"
)


# ============================================================
# CREATE BASELINE DIRECTORIES
# ============================================================

BASELINE_PROFILE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

BASELINE_SCORING_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# COPY CANDIDATE PROFILE FILES
# ============================================================

profile_count = 0

for source_file in SOURCE_PROFILE_DIR.glob("*.json"):

    destination_file = (
        BASELINE_PROFILE_DIR
        / source_file.name
    )

    shutil.copy2(
        source_file,
        destination_file,
    )

    profile_count += 1

    print(
        f"[PROFILE COPIED] "
        f"{source_file.name}"
    )


# ============================================================
# COPY SCORING RESULTS
#
# Preserve the existing JOB_xxx folder structure.
# ============================================================

scoring_count = 0

for source_job_dir in SOURCE_SCORING_DIR.iterdir():

    if not source_job_dir.is_dir():
        continue

    destination_job_dir = (
        BASELINE_SCORING_DIR
        / source_job_dir.name
    )

    destination_job_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for source_file in source_job_dir.glob("*.json"):

        destination_file = (
            destination_job_dir
            / source_file.name
        )

        shutil.copy2(
            source_file,
            destination_file,
        )

        scoring_count += 1

        print(
            f"[SCORING COPIED] "
            f"{source_job_dir.name}\\"
            f"{source_file.name}"
        )


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 80)
print("BASELINE REGRESSION DATA CREATED")
print("=" * 80)

print(
    f"Candidate profiles copied : "
    f"{profile_count}"
)

print(
    f"Scoring results copied    : "
    f"{scoring_count}"
)

print()
print("Source data was NOT moved or deleted.")
print("Original data/candidates files remain unchanged.")

print()
print("Baseline location:")
print(
    BASELINE_PROFILE_DIR
)

print(
    BASELINE_SCORING_DIR
)

print("=" * 80)
