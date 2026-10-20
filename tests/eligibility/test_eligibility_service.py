
# tests/eligibility/test_eligibility_service.py

import copy

import pytest

from api.service.eligibility_service import (
    evaluate_candidate_eligibility,
)


# ---------------------------------------------------------
# Test data factories
# ---------------------------------------------------------


def make_candidate(
    *,
    candidate_id="CAN_TEST_001",
    skills=None,
    total_experience_years=0.5,
    experience=None,
    location=None,
    notice_period_days=None,
):
    """Create a minimal eligible candidate by default."""
    profile = {
        "skills": (
            skills
            if skills is not None
            else ["Python", "Django"]
        ),
    }

    if total_experience_years is not None:
        profile["total_experience_years"] = total_experience_years

    if experience is not None:
        profile["experience"] = experience

    if location is not None:
        profile["location"] = location

    if notice_period_days is not None:
        profile["notice_period_days"] = notice_period_days

    return {
        "candidate_id": candidate_id,
        "masked_profile": profile,
    }


def make_rules(
    *,
    job_id="JOB_TEST_001",
    jd_id="JD_TEST_001",
    mandatory_skills=None,
    minimum_score=70,
    review_threshold=60,
    minimum_years=0,
    maximum_years=1,
    education=None,
    location=None,
    availability=None,
):
    """Create eligibility rules using the service's actual schema."""
    return {
        "job_id": job_id,
        "jd_id": jd_id,
        "rule_version": "1.0",
        "mandatory_skills": (
            mandatory_skills
            if mandatory_skills is not None
            else ["Python", "Django"]
        ),
        "cutoffs": {
            "minimum_ats_score": minimum_score,
            "review_score_threshold": review_threshold,
        },
        "experience": {
            "minimum_years": minimum_years,
            "maximum_years": maximum_years,
        },
        "education": education if education is not None else [],
        "location": location if location is not None else {},
        "availability": (
            availability if availability is not None else {}
        ),
    }


def evaluate(candidate, rules, score=None):
    """Call the public eligibility service."""
    return evaluate_candidate_eligibility(
        candidate_profile=candidate,
        generated_rules=rules,
        ats_score=score,
    )


# ---------------------------------------------------------
# 1. ATS score tests
# ---------------------------------------------------------

@pytest.mark.parametrize(
    ("score", "expected_check", "expected_eligibility"),
    [
        (100, "PASS", "ELIGIBLE"),
        (70, "PASS", "ELIGIBLE"),
        (69.99, "REVIEW_REQUIRED", "REVIEW_REQUIRED"),
        (60, "REVIEW_REQUIRED", "REVIEW_REQUIRED"),
        (59.99, "FAIL", "REJECTED"),
        (0, "FAIL", "REJECTED"),
    ],
)
def test_ats_score_thresholds(
    score,
    expected_check,
    expected_eligibility,
):
    candidate = make_candidate()
    rules = make_rules()

    result = evaluate(candidate, rules, score)

    assert result["checks"]["ats_score"]["status"] == expected_check
    assert result["eligibility_status"] == expected_eligibility


def test_missing_ats_score_is_reported():
    candidate = make_candidate()
    rules = make_rules()

    result = evaluate(candidate, rules)

    assert result["checks"]["ats_score"]["status"] == "NOT_PROVIDED"


@pytest.mark.parametrize("invalid_score", [-1, 101, True])
def test_invalid_ats_score_requires_review(invalid_score):
    candidate = make_candidate()
    rules = make_rules()

    result = evaluate(candidate, rules, invalid_score)

    assert result["checks"]["ats_score"]["status"] == "UNKNOWN"
    assert result["eligibility_status"] == "REVIEW_REQUIRED"


# ---------------------------------------------------------
# 2. Mandatory skill tests
# ---------------------------------------------------------

def test_all_mandatory_skills_pass():
    candidate = make_candidate(
        skills=["Python", "Django"],
    )
    rules = make_rules()

    result = evaluate(candidate, rules)

    assert result["checks"]["skills"]["status"] == "PASS"
    assert result["checks"]["skills"]["missing_skills"] == []


def test_skill_matching_is_case_insensitive():
    candidate = make_candidate(
        skills=["PYTHON", "django"],
    )
    rules = make_rules(
        mandatory_skills=["Python", "Django"],
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["skills"]["status"] == "PASS"


def test_skill_matching_normalizes_whitespace():
    candidate = make_candidate(
        skills=["  Python   Programming ", " Django "],
    )
    rules = make_rules(
        mandatory_skills=["Python Programming", "Django"],
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["skills"]["status"] == "PASS"


def test_dictionary_skill_entries_are_supported():
    candidate = make_candidate(
        skills=[
            {"skill": "Python"},
            {"name": "Django"},
        ],
    )
    rules = make_rules()

    result = evaluate(candidate, rules)

    assert result["checks"]["skills"]["status"] == "PASS"


def test_skill_dictionary_grouping_is_supported():
    candidate = make_candidate(
        skills={
            "programming": ["Python"],
            "frameworks": ["Django"],
        },
    )
    rules = make_rules()

    result = evaluate(candidate, rules)

    assert result["checks"]["skills"]["status"] == "PASS"


def test_missing_mandatory_skill_requires_review():
    candidate = make_candidate(
        skills=["Python"],
    )
    rules = make_rules(
        mandatory_skills=["Python", "Django"],
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["skills"]["status"] == "REVIEW_REQUIRED"
    assert result["checks"]["skills"]["missing_skills"] == ["Django"]
    assert result["eligibility_status"] == "REVIEW_REQUIRED"


def test_no_mandatory_skills_are_configured():
    candidate = make_candidate()
    rules = make_rules(mandatory_skills=[])

    result = evaluate(candidate, rules)

    assert result["checks"]["skills"]["status"] == "NOT_SPECIFIED"


def test_malformed_skill_entries_are_ignored():
    candidate = make_candidate(
        skills=[
            None,
            123,
            "",
            {"other": "Python"},
            {"skill": "Django"},
        ],
    )
    rules = make_rules()

    result = evaluate(candidate, rules)

    assert result["checks"]["skills"]["status"] == "REVIEW_REQUIRED"
    assert result["checks"]["skills"]["missing_skills"] == ["Python"]


# ---------------------------------------------------------
# 3. Experience tests
# ---------------------------------------------------------

def test_experience_within_range_passes():
    candidate = make_candidate(total_experience_years=0.5)
    rules = make_rules(minimum_years=0, maximum_years=1)

    result = evaluate(candidate, rules)

    assert result["checks"]["experience"]["status"] == "PASS"
    assert result["checks"]["experience"]["candidate_years"] == 0.5


def test_experience_at_minimum_boundary_passes():
    candidate = make_candidate(total_experience_years=1)
    rules = make_rules(minimum_years=1, maximum_years=3)

    result = evaluate(candidate, rules)

    assert result["checks"]["experience"]["status"] == "PASS"


def test_experience_at_maximum_boundary_passes():
    candidate = make_candidate(total_experience_years=3)
    rules = make_rules(minimum_years=1, maximum_years=3)

    result = evaluate(candidate, rules)

    assert result["checks"]["experience"]["status"] == "PASS"


def test_experience_below_minimum_requires_review():
    candidate = make_candidate(total_experience_years=0.5)
    rules = make_rules(minimum_years=1, maximum_years=3)

    result = evaluate(candidate, rules)

    assert result["checks"]["experience"]["status"] == "REVIEW_REQUIRED"
    assert result["eligibility_status"] == "REVIEW_REQUIRED"


def test_experience_above_maximum_requires_review():
    candidate = make_candidate(total_experience_years=4)
    rules = make_rules(minimum_years=1, maximum_years=3)

    result = evaluate(candidate, rules)

    assert result["checks"]["experience"]["status"] == "REVIEW_REQUIRED"
    assert result["eligibility_status"] == "REVIEW_REQUIRED"


def test_missing_experience_requires_review():
    candidate = make_candidate(total_experience_years=None)
    rules = make_rules()

    result = evaluate(candidate, rules)

    assert result["checks"]["experience"]["status"] == "UNKNOWN"
    assert result["eligibility_status"] == "REVIEW_REQUIRED"


def test_experience_date_ranges_are_supported():
    candidate = make_candidate(
        total_experience_years=None,
        experience=[
            {
                "duration": {
                    "start_date": "January 2022",
                    "end_date": "June 2022",
                }
            }
        ],
    )
    rules = make_rules(minimum_years=0, maximum_years=1)

    result = evaluate(candidate, rules)

    assert result["checks"]["experience"]["status"] == "PASS"
    assert result["checks"]["experience"]["candidate_years"] == 0.5


def test_overlapping_experience_is_not_double_counted():
    candidate = make_candidate(
        total_experience_years=None,
        experience=[
            {
                "duration": {
                    "start_date": "January 2022",
                    "end_date": "December 2022",
                }
            },
            {
                "duration": {
                    "start_date": "July 2022",
                    "end_date": "June 2023",
                }
            },
        ],
    )
    rules = make_rules(minimum_years=1, maximum_years=2)

    result = evaluate(candidate, rules)

    # The overlapping periods together cover January 2022 to June 2023:
    # 18 calendar months, not 24.
    assert result["checks"]["experience"]["candidate_years"] == 1.5
    assert result["checks"]["experience"]["status"] == "PASS"


# ---------------------------------------------------------
# 4. Location tests
# ---------------------------------------------------------

def test_location_rule_not_enforced_by_default():
    candidate = make_candidate(location="Chennai")
    rules = make_rules(
        location={
            "allowed_locations": ["Kochi"],
            "enforcement": "unspecified",
        },
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["location"]["status"] == "NOT_SPECIFIED"


def test_matching_mandatory_location_passes():
    candidate = make_candidate(location="Kochi, Kerala")
    rules = make_rules(
        location={
            "allowed_locations": ["Kochi"],
            "enforcement": "mandatory",
        },
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["location"]["status"] == "PASS"


def test_nonmatching_mandatory_location_rejects():
    candidate = make_candidate(location="Chennai, Tamil Nadu")
    rules = make_rules(
        location={
            "allowed_locations": ["Kochi"],
            "enforcement": "mandatory",
        },
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["location"]["status"] == "FAIL"
    assert result["eligibility_status"] == "REJECTED"


def test_missing_mandatory_location_requires_review():
    candidate = make_candidate()
    rules = make_rules(
        location={
            "allowed_locations": ["Kochi"],
            "enforcement": "mandatory",
        },
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["location"]["status"] == "UNKNOWN"
    assert result["eligibility_status"] == "REVIEW_REQUIRED"


# ---------------------------------------------------------
# 5. Availability / notice period tests
# ---------------------------------------------------------

def test_availability_rule_not_enforced_by_default():
    candidate = make_candidate(notice_period_days=90)
    rules = make_rules(
        availability={
            "maximum_notice_period_days": 30,
            "enforcement": "unspecified",
        },
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["availability"]["status"] == "NOT_SPECIFIED"


def test_notice_period_within_limit_passes():
    candidate = make_candidate(notice_period_days=30)
    rules = make_rules(
        availability={
            "maximum_notice_period_days": 30,
            "enforcement": "mandatory",
        },
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["availability"]["status"] == "PASS"


def test_notice_period_above_mandatory_limit_rejects():
    candidate = make_candidate(notice_period_days=60)
    rules = make_rules(
        availability={
            "maximum_notice_period_days": 30,
            "enforcement": "mandatory",
        },
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["availability"]["status"] == "FAIL"
    assert result["eligibility_status"] == "REJECTED"


def test_missing_mandatory_notice_period_requires_review():
    candidate = make_candidate()
    rules = make_rules(
        availability={
            "maximum_notice_period_days": 30,
            "enforcement": "mandatory",
        },
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["availability"]["status"] == "UNKNOWN"
    assert result["eligibility_status"] == "REVIEW_REQUIRED"


# ---------------------------------------------------------
# 6. Education behavior
# ---------------------------------------------------------

def test_education_rules_are_non_enforcing():
    candidate = make_candidate()
    rules = make_rules(
        education=["B.Tech in Computer Science"],
    )

    result = evaluate(candidate, rules)

    assert result["checks"]["education"]["status"] == "PREFERRED"

    # Education alone does not change eligibility status.
    assert result["eligibility_status"] == "ELIGIBLE"


# ---------------------------------------------------------
# 7. Input compatibility and data integrity
# ---------------------------------------------------------

def test_wrapped_eligibility_rules_are_supported():
    candidate = make_candidate()
    rules = make_rules()

    result = evaluate(
        candidate,
        {"eligibility_rules": rules},
        score=85,
    )

    assert result["job_id"] == rules["job_id"]
    assert result["jd_id"] == rules["jd_id"]
    assert result["eligibility_status"] == "ELIGIBLE"


def test_result_contains_expected_fields():
    candidate = make_candidate()
    rules = make_rules()

    result = evaluate(candidate, rules, score=85)

    assert set(result) == {
        "job_id",
        "jd_id",
        "candidate_id",
        "eligibility_status",
        "ats_score",
        "rule_version",
        "checks",
        "reasons",
    }


def test_evaluation_does_not_modify_candidate_or_rules():
    candidate = make_candidate(
        skills=["Python", "Django"],
    )
    rules = make_rules()

    original_candidate = copy.deepcopy(candidate)
    original_rules = copy.deepcopy(rules)

    evaluate(candidate, rules, score=85)

    assert candidate == original_candidate
    assert rules == original_rules


def test_candidate_without_wrapper_is_supported():
    candidate = {
        "candidate_id": "CAN_TEST_002",
        "skills": ["Python", "Django"],
        "total_experience_years": 0.5,
    }
    rules = make_rules()

    result = evaluate(candidate, rules, score=85)

    assert result["candidate_id"] == "CAN_TEST_002"
    assert result["checks"]["skills"]["status"] == "PASS"
    assert result["eligibility_status"] == "ELIGIBLE"



@pytest.fixture
def candidate_with_different_degree():
    """Candidate whose education does not match the mandatory degree."""
    return {
        "candidate_id": "CAN_TEST_EDUCATION_001",
        "masked_profile": {
            "skills": ["Python", "Django", "REST API"],
            "experience": [
                {
                    "duration": {
                        "start_date": "January 2025",
                        "end_date": "October 2025",
                    }
                }
            ],
            "education": [
                {
                    "degree": "Bachelor of Commerce",
                    "field": "Accounting",
                }
            ],
        },
    }



def test_missing_mandatory_degree_requires_review(
    candidate_with_different_degree,
):
    """A mandatory degree mismatch must require manual review."""

    generated_rules = {
        "eligibility_rules": {
            "job_id": "JOB_TEST_EDUCATION",
            "jd_id": "PythonDeveloperFresher",
            "rule_version": "1.0",
            "cutoffs": {
                "minimum_ats_score": 70,
                "review_score_threshold": 60,
            },
            "mandatory_skills": [
                "Python",
                "Django",
                "REST API",
            ],
            "experience": {
                "minimum_years": 0,
                "maximum_years": 1,
            },
            "education": [
                {
                    "description": "B.Tech degree is mandatory.",
                    "degree": "Bachelor of Technology",
                    "enforcement": "mandatory",
                }
            ],
            "location": {
                "enforcement": "unspecified",
            },
            "availability": {
                "enforcement": "unspecified",
            },
        }
    }

    result = evaluate_candidate_eligibility(
        candidate_profile=candidate_with_different_degree,
        generated_rules=generated_rules,
        ats_score=90.0,
    )

    # Overall eligibility must require review.
    assert result["eligibility_status"] == "REVIEW_REQUIRED"

    # The education check must identify the mismatch.
    education_check = result["checks"]["education"]

    assert education_check["status"] == "REVIEW_REQUIRED"
    assert education_check["rules"][0]["enforcement"] == "mandatory"
    assert education_check["rules"][0]["status"] == "REVIEW_REQUIRED"

    # Verify that the mismatch is explained.
    assert "mandatory education requirement" in (
        education_check["rules"][0]["reason"].casefold()
    )
