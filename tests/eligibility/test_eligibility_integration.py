
from copy import deepcopy

import pytest

from eligibility.eligibility_rule_generator import (
    generate_eligibility_rules,
)
from api.service.eligibility_service import (
    evaluate_candidate_eligibility,
)


@pytest.fixture
def role_policies():
    return {
        "backend": {
            "minimum_ats_score": 70,
            "review_score_threshold": 60,
            "location": {},
            "availability": {},
        },
        "senior_backend": {
            "minimum_ats_score": 80,
            "review_score_threshold": 65,
            "location": {},
            "availability": {},
        },
        "default": {
            "minimum_ats_score": 70,
            "review_score_threshold": 60,
            "location": {},
            "availability": {},
        },
    }


@pytest.fixture
def parsed_jd():
    return {
        "job_id": "JOB_INTEGRATION_001",
        "jd_id": "PythonDeveloperFresher",
        "job_title": "Python Developer",
        "role_category": "backend",
        "required_skills": [
            "Python",
            "Django",
            "REST API",
            "Git",
        ],
        "preferred_skills": ["Docker"],
        "experience": [
            {
                "minimum_years": 0,
                "maximum_years": 1,
                "description": "Fresher or up to 1 year",
            }
        ],
        "education": [],
        "requirements": [],
    }


def make_candidate(
    *,
    skills=None,
    experience_years=0.5,
    candidate_id="CAN_INTEGRATION_001",
):
    return {
        "candidate_id": candidate_id,
        "masked_profile": {
            "skills": (
                skills
                if skills is not None
                else ["Python", "Django", "REST API", "Git"]
            ),
            "total_experience_years": experience_years,
        },
    }


def test_generator_preserves_job_identifiers(
    parsed_jd,
    role_policies,
):
    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )

    assert rules["job_id"] == parsed_jd["job_id"]
    assert rules["jd_id"] == parsed_jd["jd_id"]
    assert rules["generation_status"] == "generated"


def test_required_skills_become_mandatory_by_default(
    parsed_jd,
    role_policies,
):
    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )

    assert rules["required_skills"] == [
        "Python",
        "Django",
        "REST API",
        "Git",
    ]
    assert rules["mandatory_skills"] == rules["required_skills"]
    assert rules["preferred_skills"] == ["Docker"]


def test_explicit_mandatory_skills_override_required_skills(
    parsed_jd,
    role_policies,
):
    parsed_jd = deepcopy(parsed_jd)
    parsed_jd["mandatory_skills"] = ["Python"]

    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )

    assert rules["required_skills"] == [
        "Python",
        "Django",
        "REST API",
        "Git",
    ]
    assert rules["mandatory_skills"] == ["Python"]


def test_duplicate_skills_are_removed_case_insensitively(
    parsed_jd,
    role_policies,
):
    parsed_jd = deepcopy(parsed_jd)
    parsed_jd["required_skills"] = [
        "Python",
        " python ",
        "Django",
        "DJANGO",
    ]

    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )

    assert rules["required_skills"] == ["Python", "Django"]


def test_backend_policy_sets_score_cutoffs(
    parsed_jd,
    role_policies,
):
    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )

    assert rules["role_policy_key"] == "backend"
    assert rules["cutoffs"]["minimum_ats_score"] == 70
    assert rules["cutoffs"]["review_score_threshold"] == 60


def test_senior_backend_policy_is_selected(
    parsed_jd,
    role_policies,
):
    parsed_jd = deepcopy(parsed_jd)
    parsed_jd["job_title"] = "Senior Python Developer"

    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )

    assert rules["role_policy_key"] == "senior_backend"
    assert rules["cutoffs"]["minimum_ats_score"] == 80


def test_jd_location_constraints_override_policy(
    parsed_jd,
    role_policies,
):
    role_policies["backend"]["location"] = {
        "allowed_locations": ["Bengaluru"],
        "remote_allowed": False,
        "enforcement": "mandatory",
    }

    parsed_jd = deepcopy(parsed_jd)
    parsed_jd["location"] = {
        "allowed_locations": ["Kochi"],
        "remote_allowed": True,
        "enforcement": "preferred",
    }

    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )

    assert rules["location"]["allowed_locations"] == ["Kochi"]
    assert rules["location"]["remote_allowed"] is True
    assert rules["location"]["enforcement"] == "preferred"


def test_generated_rules_can_evaluate_a_matching_candidate(
    parsed_jd,
    role_policies,
):
    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )
    candidate = make_candidate()

    result = evaluate_candidate_eligibility(
        candidate_profile=candidate,
        generated_rules=rules,
        ats_score=90,
    )

    assert result["job_id"] == parsed_jd["job_id"]
    assert result["jd_id"] == parsed_jd["jd_id"]
    assert result["candidate_id"] == candidate["candidate_id"]
    assert result["eligibility_status"] == "ELIGIBLE"


def test_generated_rules_flag_missing_mandatory_skills(
    parsed_jd,
    role_policies,
):
    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )
    candidate = make_candidate(
        skills=["Python", "Git"],
    )

    result = evaluate_candidate_eligibility(
        candidate_profile=candidate,
        generated_rules=rules,
        ats_score=90,
    )

    assert result["eligibility_status"] == "REVIEW_REQUIRED"
    assert any(
        check.get("status") == "REVIEW_REQUIRED"
        for check in result["checks"].values()
    )


def test_generated_rules_flag_experience_outside_range(
    parsed_jd,
    role_policies,
):
    rules = generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )
    candidate = make_candidate(experience_years=3)

    result = evaluate_candidate_eligibility(
        candidate_profile=candidate,
        generated_rules=rules,
        ats_score=90,
    )

    assert result["eligibility_status"] == "REVIEW_REQUIRED"


def test_generator_does_not_modify_parsed_jd(
    parsed_jd,
    role_policies,
):
    original_jd = deepcopy(parsed_jd)

    generate_eligibility_rules(
        parsed_jd,
        role_policies=role_policies,
    )

    assert parsed_jd == original_jd
