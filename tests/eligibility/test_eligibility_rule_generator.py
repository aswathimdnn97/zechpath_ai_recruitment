
from eligibility.eligibility_rule_generator import (
    generate_eligibility_rules,
)


def test_generate_python_developer_rules():
    parsed_jd = {
        "job_title": "Python Developer",
        "job_id": "JOB_BF2FEFE4A4A3",
        "jd_id": "PythonDeveloperFresher",
        "required_skills": [
            "Python",
            "Django",
            "FastAPI",
            "REST API",
            "PostgreSQL",
            "Git",
            "API Testing",
        ],
        "preferred_skills": [],
        "education": [
            "B.Tech / B.E. / equivalent technical degree preferred."
        ],
        "experience": [
            {
                "minimum_years": 0,
                "maximum_years": 1,
                "description": (
                    "0-1 year experience, internship or "
                    "relevant project experience acceptable."
                ),
            }
        ],
        "requirements": [],
    }

    result = generate_eligibility_rules(parsed_jd)

    assert result["job_id"] == "JOB_BF2FEFE4A4A3"
    assert result["jd_id"] == "PythonDeveloperFresher"

    assert result["mandatory_skills"] == [
        "Python",
        "Django",
        "FastAPI",
        "REST API",
        "PostgreSQL",
        "Git",
        "API Testing",
    ]

    assert result["experience"]["minimum_years"] == 0
    assert result["experience"]["maximum_years"] == 1

    assert result["education"][0]["enforcement"] == "preferred"
    assert result["generation_status"] == "generated"
    
    
def test_backend_policy_is_applied():
    parsed_jd = {
        "job_id": "JOB_TEST",
        "jd_id": "JD_TEST",
        "job_title": "Python Developer",
        "role_category": "backend",
        "required_skills": ["Python", "Django"],
        "experience": [{"minimum_years": 2}],
    }

    policies = {
        "default": {
            "minimum_ats_score": 70,
            "review_score_threshold": 60,
        },
        "backend": {
            "minimum_ats_score": 75,
            "review_score_threshold": 65,
        },
    }

    result = generate_eligibility_rules(
        parsed_jd,
        role_policies=policies,
    )

    assert result["cutoffs"]["minimum_ats_score"] == 75
    assert result["cutoffs"]["review_score_threshold"] == 65
    assert result["mandatory_skills"] == ["Python", "Django"]
    assert result["role_policy_key"] == "backend"


def test_senior_backend_policy_is_selected():
    parsed_jd = {
        "job_title": "Senior Python Developer",
        "role_category": "backend",
    }

    policies = {
        "default": {
            "minimum_ats_score": 70,
            "review_score_threshold": 60,
        },
        "backend": {
            "minimum_ats_score": 70,
            "review_score_threshold": 60,
        },
        "senior_backend": {
            "minimum_ats_score": 80,
            "review_score_threshold": 65,
        },
    }

    result = generate_eligibility_rules(
        parsed_jd,
        role_policies=policies,
    )

    assert result["cutoffs"]["minimum_ats_score"] == 80
    assert result["role_policy_key"] == "senior_backend"


def test_explicit_mandatory_skills_are_preserved():
    parsed_jd = {
        "required_skills": ["Python", "Django"],
        "mandatory_skills": ["Python"],
    }

    result = generate_eligibility_rules(
        parsed_jd,
        role_policies={"default": {}},
    )

    assert result["required_skills"] == ["Python", "Django"]
    assert result["mandatory_skills"] == ["Python"]


def test_missing_location_and_availability_stay_unspecified():
    result = generate_eligibility_rules(
        {"role_category": "backend"},
        role_policies={"default": {}},
    )

    assert result["location"]["allowed_locations"] == []
    assert result["location"]["remote_allowed"] is None
    assert result["availability"]["maximum_notice_period_days"] is None


def test_unknown_role_uses_default_policy():
    result = generate_eligibility_rules(
        {"role_category": "unknown"},
        role_policies={
            "default": {
                "minimum_ats_score": 72,
                "review_score_threshold": 62,
            }
        },
    )

    assert result["cutoffs"]["minimum_ats_score"] == 72
    assert result["role_policy_key"] == "default"


def test_explicit_role_policy_key_takes_precedence():
    parsed_jd = {
        "job_title": "Senior Python Developer",
        "role_category": "backend",
        "role_policy_key": "frontend",
    }

    policies = {
        "default": {
            "minimum_ats_score": 70,
            "review_score_threshold": 60,
        },
        "senior_backend": {
            "minimum_ats_score": 80,
            "review_score_threshold": 65,
        },
        "frontend": {
            "minimum_ats_score": 75,
            "review_score_threshold": 62,
        },
    }

    result = generate_eligibility_rules(
        parsed_jd,
        role_policies=policies,
    )

    assert result["role_policy_key"] == "frontend"
    assert result["cutoffs"]["minimum_ats_score"] == 75
    assert result["cutoffs"]["review_score_threshold"] == 62


def test_preferred_skills_are_not_promoted_to_mandatory():
    parsed_jd = {
        "required_skills": ["Python", "Django", "Git"],
        "mandatory_skills": ["Python", "Django"],
        "preferred_skills": ["Git"],
    }

    result = generate_eligibility_rules(
        parsed_jd,
        role_policies={"default": {}},
    )

    assert result["required_skills"] == ["Python", "Django", "Git"]
    assert result["mandatory_skills"] == ["Python", "Django"]
    assert result["preferred_skills"] == ["Git"]


def test_required_skills_become_mandatory_when_field_is_absent():
    parsed_jd = {
        "required_skills": ["Python", "Django"],
        "preferred_skills": ["Git"],
    }

    result = generate_eligibility_rules(
        parsed_jd,
        role_policies={"default": {}},
    )

    assert result["mandatory_skills"] == ["Python", "Django"]
    assert result["preferred_skills"] == ["Git"]


def test_duplicate_mandatory_skills_are_removed_case_insensitively():
    parsed_jd = {
        "mandatory_skills": ["Python", "python", " Django ", "Django"],
        "required_skills": ["Python", "Django"],
    }

    result = generate_eligibility_rules(
        parsed_jd,
        role_policies={"default": {}},
    )

    assert result["mandatory_skills"] == ["Python", "Django"]


def test_role_policy_selection_is_case_insensitive():
    parsed_jd = {
        "job_title": "Python Developer",
        "role_category": "BACKEND",
    }

    result = generate_eligibility_rules(
        parsed_jd,
        role_policies={
            "default": {
                "minimum_ats_score": 70,
                "review_score_threshold": 60,
            },
            "backend": {
                "minimum_ats_score": 75,
                "review_score_threshold": 65,
            },
        },
    )

    assert result["role_policy_key"] == "backend"
    assert result["cutoffs"]["minimum_ats_score"] == 75

