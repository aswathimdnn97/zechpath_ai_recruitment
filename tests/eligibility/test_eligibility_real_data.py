
import json
from pathlib import Path

import pytest

from eligibility.eligibility_rule_generator import (
    generate_eligibility_rules,
)
from api.service.eligibility_service import (
    evaluate_candidate_eligibility,
)


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parents[2]

EXTRACTED_DIR = (
    BASE_DIR
    / "data"
    / "extracted"
    / "jd"
)

CANDIDATE_DIR = (
    BASE_DIR
    / "data"
    / "candidates"
    / "candidate_profile"
)

CANDIDATE_IDS = [
    "CAN_18CF07232472",
    "CAN_1CA3DA4F0062",
]

EXPECTED_JD_ID = "PythonDeveloperFresher"
EXPECTED_JD_FILE = "PythonDeveloperFresher.pdf"


# ---------------------------------------------------------
# JSON utilities
# ---------------------------------------------------------

def load_json(path: Path) -> dict:
    """Load a JSON file and return its dictionary."""
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"Expected a JSON object in {path}, "
            f"received {type(data).__name__}"
        )

    return data


def normalize_text(value) -> str:
    """Normalize text for case-insensitive comparison."""
    if not isinstance(value, str):
        return ""

    return " ".join(value.casefold().split())



EXPECTED_JD_ID = "PythonDeveloperFresher"


def find_python_developer_jd() -> tuple[Path, dict]:
    """Load the Python Developer Fresher JD by its unique jd_id."""

    if not EXTRACTED_DIR.exists():
        raise FileNotFoundError(
            f"Parsed JD directory not found: {EXTRACTED_DIR}"
        )

    json_files = sorted(EXTRACTED_DIR.glob("*.json"))

    for path in json_files:
        jd = load_json(path)

        if jd.get("jd_id") == EXPECTED_JD_ID:
            assert jd.get("job_id") == "JOB_BF2FEFE4A4A3", (
                f"Unexpected job_id in {path.name}: "
                f"{jd.get('job_id')}"
            )

            return path, jd

    raise FileNotFoundError(
        f"JD with jd_id={EXPECTED_JD_ID!r} "
        f"not found in {EXTRACTED_DIR}"
    )

# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------

@pytest.fixture(scope="module")
def parsed_jd():
    """Load the actual parsed JD from the extracted data."""
    path, jd = find_python_developer_jd()

    print(f"\nUsing parsed JD: {path}")
    print(f"job_id: {jd.get('job_id')}")
    print(f"jd_id: {jd.get('jd_id')}")

    return jd


@pytest.fixture(scope="module")
def generated_rules(parsed_jd):
    """Generate eligibility rules from the real parsed JD."""
    rules = generate_eligibility_rules(parsed_jd)

    assert isinstance(rules, dict)
    assert rules.get("generation_status") == "generated"

    return rules


@pytest.fixture(scope="module")
def candidate_profiles():
    """Load real candidate profiles without modifying source files."""
    profiles = {}

    for candidate_id in CANDIDATE_IDS:
        path = CANDIDATE_DIR / f"{candidate_id}.json"

        assert path.is_file(), (
            f"Candidate profile not found: {path}"
        )

        profile = load_json(path)

        assert profile.get("candidate_id") == candidate_id
        assert isinstance(profile.get("masked_profile"), dict), (
            f"{candidate_id} must contain a masked_profile object"
        )

        profiles[candidate_id] = profile

    return profiles


# ---------------------------------------------------------
# Skill utilities
# ---------------------------------------------------------

def extract_candidate_skills(candidate_profile: dict) -> set[str]:
    """
    Extract skill names from a candidate's masked profile.

    Supports skill entries represented as strings or dictionaries.
    """
    masked_profile = candidate_profile.get(
        "masked_profile",
        candidate_profile,
    )

    raw_skills = masked_profile.get("skills", [])
    normalized_skills = set()

    if not isinstance(raw_skills, list):
        return normalized_skills

    for item in raw_skills:
        if isinstance(item, str):
            skill = item

        elif isinstance(item, dict):
            skill = item.get("skill") or item.get("name")

        else:
            continue

        if isinstance(skill, str) and skill.strip():
            normalized_skills.add(normalize_text(skill))

    return normalized_skills


# ---------------------------------------------------------
# Rule generation tests
# ---------------------------------------------------------

def test_real_jd_contains_required_identifiers(parsed_jd):
    """Verify that the parsed JD contains its processing job ID."""
    assert parsed_jd.get("job_id")

    # jd_id may be absent in older parsed JD records.
    # If present, it must be a non-empty string.
    if "jd_id" in parsed_jd:
        assert isinstance(parsed_jd["jd_id"], str)
        assert parsed_jd["jd_id"].strip()


def test_real_jd_generates_expected_eligibility_rules(
    parsed_jd,
    generated_rules,
):
    """Check that JD requirements survive rule generation."""
    assert generated_rules["job_id"] == parsed_jd["job_id"]

    # Validate jd_id only when the parsed JD supplies it.
    if parsed_jd.get("jd_id"):
        assert generated_rules["jd_id"] == parsed_jd["jd_id"]

    expected_required_skills = parsed_jd.get(
        "required_skills",
        [],
    )

    assert isinstance(expected_required_skills, list)

    assert generated_rules["required_skills"] == (
        expected_required_skills
    )

    assert generated_rules["mandatory_skills"] == (
        generated_rules["required_skills"]
    )

    assert generated_rules["preferred_skills"] == (
        parsed_jd.get("preferred_skills", [])
    )

   
    experience_entries = parsed_jd.get("experience", [])

    minimum_values = [
        item["minimum_years"]
        for item in experience_entries
        if isinstance(item, dict)
        and item.get("minimum_years") is not None
    ]

    if minimum_values:
        expected_minimum = max(minimum_values)

        assert (
            generated_rules["experience"]["minimum_years"]
            == float(expected_minimum)
        )


    assert generated_rules["generation_status"] == "generated"


# ---------------------------------------------------------
# Candidate evaluation tests
# ---------------------------------------------------------

@pytest.mark.parametrize("candidate_id", CANDIDATE_IDS)
def test_real_candidate_can_be_evaluated(
    candidate_id,
    candidate_profiles,
    generated_rules,
):
    """Evaluate each real profile without writing production data."""
    candidate = candidate_profiles[candidate_id]

    result = evaluate_candidate_eligibility(
        candidate_profile=candidate,
        generated_rules=generated_rules,
        ats_score=None,
    )

    assert isinstance(result, dict)
    assert result["candidate_id"] == candidate_id
    assert result["job_id"] == generated_rules["job_id"]

    if generated_rules.get("jd_id"):
        assert result["jd_id"] == generated_rules["jd_id"]

    assert result["eligibility_status"] in {
        "ELIGIBLE",
        "REVIEW_REQUIRED",
        "REJECTED",
    }

    expected_check_names = {
        "ats_score",
        "skills",
        "experience",
        "education",
        "location",
        "availability",
    }

    assert set(result["checks"]) == expected_check_names
    assert result["checks"]["ats_score"]["status"] == "NOT_PROVIDED"


def test_technical_candidate_skill_check(
    candidate_profiles,
    generated_rules,
):
    """Check skill evaluation for the candidate with technical skills."""
    candidate = candidate_profiles["CAN_18CF07232472"]

    result = evaluate_candidate_eligibility(
        candidate_profile=candidate,
        generated_rules=generated_rules,
    )

    skill_check = result["checks"]["skills"]

    assert skill_check["status"] in {
        "PASS",
        "REVIEW_REQUIRED",
    }

    assert isinstance(skill_check["missing_skills"], list)

    candidate_skills = extract_candidate_skills(candidate)

    assert "python" in candidate_skills
    assert "django" in candidate_skills
    assert "git" in candidate_skills


def test_hr_candidate_requires_skill_review(
    candidate_profiles,
    generated_rules,
):
    """An HR candidate should require review for a Python Developer role."""
    candidate = candidate_profiles["CAN_1CA3DA4F0062"]

    result = evaluate_candidate_eligibility(
        candidate_profile=candidate,
        generated_rules=generated_rules,
    )

    skill_check = result["checks"]["skills"]

    assert skill_check["status"] == "REVIEW_REQUIRED"
    assert skill_check["missing_skills"]
    assert result["eligibility_status"] == "REVIEW_REQUIRED"


# ---------------------------------------------------------
# Data integrity test
# ---------------------------------------------------------

def test_evaluation_does_not_modify_candidate_or_jd(
    parsed_jd,
    candidate_profiles,
    generated_rules,
):
    """Ensure evaluation does not mutate loaded source data."""
    original_jd = json.loads(json.dumps(parsed_jd))
    original_candidates = json.loads(
        json.dumps(candidate_profiles)
    )
    original_rules = json.loads(
        json.dumps(generated_rules)
    )

    for candidate in candidate_profiles.values():
        evaluate_candidate_eligibility(
            candidate_profile=candidate,
            generated_rules=generated_rules,
        )

    assert parsed_jd == original_jd
    assert candidate_profiles == original_candidates
    assert generated_rules == original_rules



@pytest.mark.parametrize(
    ("ats_score", "expected_check_status"),
    [
        (0, "FAIL"),
        (59.99, "FAIL"),
        (60, "REVIEW_REQUIRED"),
        (69.99, "REVIEW_REQUIRED"),
        (70, "PASS"),
        (100, "PASS"),
    ],
)
def test_real_candidate_ats_score_thresholds(
    ats_score,
    expected_check_status,
    candidate_profiles,
    generated_rules,
):
    """Verify ATS score threshold boundaries with real candidate data."""
    candidate = candidate_profiles["CAN_18CF07232472"]

    result = evaluate_candidate_eligibility(
        candidate_profile=candidate,
        generated_rules=generated_rules,
        ats_score=ats_score,
    )

    assert (
        result["checks"]["ats_score"]["status"]
        == expected_check_status
    )

    if expected_check_status == "FAIL":
        assert result["eligibility_status"] == "REJECTED"
    elif expected_check_status == "REVIEW_REQUIRED":
        assert result["eligibility_status"] == "REVIEW_REQUIRED"



SCORING_DIR = (
    BASE_DIR
    / "data"
    / "candidates"
    / "scoring_results"
)

SCORED_CANDIDATE_EXPECTATIONS = {
    "CAN_CB63A04EDA0B": {
        "ats_score": 78.55,
        "missing_skills": {"git", "api testing"},
    },
    "CAN_4CFB167D7487": {
        "ats_score": 87.04,
        "missing_skills": {"api testing"},
    },
}


@pytest.mark.parametrize(
    "candidate_id",
    list(SCORED_CANDIDATE_EXPECTATIONS),
)
def test_real_ats_score_and_eligibility_decision(
    candidate_id,
    generated_rules,
):
    """Validate real ATS scores against eligibility decisions."""
    expectation = SCORED_CANDIDATE_EXPECTATIONS[candidate_id]

    profile_path = CANDIDATE_DIR / f"{candidate_id}.json"
    score_path = (
        SCORING_DIR
        / generated_rules["job_id"]
        / f"{candidate_id}.json"
    )

    assert profile_path.is_file(), (
        f"Candidate profile not found: {profile_path}"
    )
    assert score_path.is_file(), (
        f"ATS scoring result not found: {score_path}"
    )

    candidate = load_json(profile_path)
    scoring_result = load_json(score_path)

    assert candidate.get("candidate_id") == candidate_id
    assert scoring_result.get("candidate_id") == candidate_id
    assert scoring_result.get("job_id") == generated_rules["job_id"]
    assert scoring_result.get("jd_id") == generated_rules["jd_id"]

    ats_score = scoring_result["candidate_score"]["final_score"]

    assert ats_score == pytest.approx(expectation["ats_score"])

    result = evaluate_candidate_eligibility(
        candidate_profile=candidate,
        generated_rules=generated_rules,
        ats_score=ats_score,
    )

    # Both real ATS scores are above the configured 70-point
    # pass threshold.
    assert result["checks"]["ats_score"]["status"] == "PASS"

    skill_check = result["checks"]["skills"]

    assert skill_check["status"] == "REVIEW_REQUIRED"

    actual_missing_skills = {
        normalize_text(skill)
        for skill in skill_check["missing_skills"]
    }

    assert actual_missing_skills == expectation["missing_skills"]

    # Passing ATS score alone must not override missing mandatory skills.
    assert result["eligibility_status"] == "REVIEW_REQUIRED"


def test_generated_rules_match_parsed_jd(parsed_jd, generated_rules):
    # Validate job identifiers.
    assert generated_rules["job_id"] == parsed_jd["job_id"]
    assert generated_rules["jd_id"] == parsed_jd["jd_id"]

    # Validate skill requirements.
    assert generated_rules["required_skills"] == parsed_jd["required_skills"]
    assert generated_rules["preferred_skills"] == parsed_jd["preferred_skills"]

    # All required skills are mandatory under the current policy.
    assert generated_rules["mandatory_skills"] == parsed_jd["required_skills"]

    # Validate experience constraints.
    jd_experience = parsed_jd["experience"][0]
    rules_experience = generated_rules["experience"]

    assert rules_experience["minimum_years"] == jd_experience["minimum_years"]
    assert rules_experience["maximum_years"] == jd_experience["maximum_years"]
    assert rules_experience["description"] == jd_experience["description"]

    # Validate education without making it mandatory.
    assert generated_rules["education"] == [
        {
            "description": parsed_jd["education"][0],
            "enforcement": "preferred",
        }
    ]

    # Location and availability are not currently enforced.
    assert generated_rules["location"]["enforcement"] == "unspecified"
    assert generated_rules["availability"]["enforcement"] == "unspecified"

    assert generated_rules["generation_status"] == "generated"



def test_real_jd_uses_expected_default_policy(parsed_jd, generated_rules):
    # The parsed JD may omit role_category entirely.
    assert parsed_jd.get("role_category") is None

    # No explicit policy is configured, so default is selected.
    assert parsed_jd.get("role_policy_key") is None
    assert generated_rules["role_policy_key"] == "default"

    # Cutoffs match data/eligibility_rules/role_policies.json.
    assert generated_rules["cutoffs"]["minimum_ats_score"] == 70.0
    assert generated_rules["cutoffs"]["review_score_threshold"] == 60.0



def test_conflicting_experience_ranges_are_rejected():
    parsed_jd = {
        "job_id": "JOB_TEST123",
        "jd_id": "JD_EXPERIENCE_CONFLICT",
        "experience": [
            {"minimum_years": 5},
            {"maximum_years": 2},
        ],
    }

    with pytest.raises(ValueError, match="minimum_years"):
        generate_eligibility_rules(
            parsed_jd,
            role_policies={
                "default": {
                    "minimum_ats_score": 70,
                    "review_score_threshold": 60,
                }
            },
        )


def test_compatible_experience_ranges_are_accepted():
    parsed_jd = {
        "job_id": "JOB_TEST123",
        "jd_id": "JD_VALID_EXPERIENCE",
        "experience": [
            {"minimum_years": 2, "maximum_years": 5},
            {"minimum_years": 3, "maximum_years": 4},
        ],
    }

    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies={
            "default": {
                "minimum_ats_score": 70,
                "review_score_threshold": 60,
            }
        },
    )

    assert rules["experience"]["minimum_years"] == 3.0
    assert rules["experience"]["maximum_years"] == 4.0


@pytest.mark.parametrize(
    "invalid_policy",
    [
        None,
        [],
        {"minimum_ats_score": 101, "review_score_threshold": 60},
        {"minimum_ats_score": -1, "review_score_threshold": 0},
        {"minimum_ats_score": float("nan"), "review_score_threshold": 0},
        {"minimum_ats_score": 70, "review_score_threshold": 80},
        {"minimum_ats_score": "seventy", "review_score_threshold": 60},
        {"minimum_ats_score": True, "review_score_threshold": 0},
    ],
)
def test_invalid_default_policy_is_rejected(invalid_policy):
    parsed_jd = {
        "job_id": "JOB_TEST123",
        "jd_id": "JD_POLICY_VALIDATION",
        "required_skills": ["Python"],
    }

    with pytest.raises(ValueError):
        generate_eligibility_rules(
            parsed_jd,
            role_policies={"default": invalid_policy},
        )


def test_valid_default_policy_is_accepted():
    parsed_jd = {
        "job_id": "JOB_TEST123",
        "jd_id": "JD_VALID_POLICY",
    }

    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies={
            "default": {
                "minimum_ats_score": 70,
                "review_score_threshold": 60,
            }
        },
    )

    assert rules["cutoffs"] == {
        "minimum_ats_score": 70.0,
        "review_score_threshold": 60.0,
    }
