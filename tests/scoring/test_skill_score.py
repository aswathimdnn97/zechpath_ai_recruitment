from scoring.skill_score import calculate_skill_score


# ============================================================
# Test 1: All required skills matched
# ============================================================

def test_all_required_skills_matched():

    candidate_profile = {
        "skills": [
            {"skill": "Python"},
            {"skill": "Django"},
            {"skill": "PostgreSQL"},
            {"skill": "Git"},
        ]
    }

    jd_profile = {
        "required_skills": [
            "Python",
            "Django",
            "PostgreSQL",
            "Git",
        ],
        "preferred_skills": [],
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    assert result["score"] == 100.0

    assert (
        result["required"]["match_percentage"]
        == 100.0
    )

    assert len(
        result["required"]["matched"]
    ) == 4

    assert result["required"]["missing"] == []

    assert {
        item["matched_skill"].lower()
        for item in result["required"]["matched"]
    } == {
        "python",
        "django",
        "postgresql",
        "git",
    }


# ============================================================
# Test 2: Some required skills are missing
# ============================================================

def test_some_required_skills_missing():

    candidate_profile = {
        "skills": [
            {"skill": "Python"},
            {"skill": "Django"},
        ]
    }

    jd_profile = {
        "required_skills": [
            "Python",
            "Django",
            "PostgreSQL",
            "Git",
        ],
        "preferred_skills": [],
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    assert (
        result["required"]["match_percentage"]
        == 50.0
    )

    assert len(
        result["required"]["matched"]
    ) == 2

    assert {
        item["required_skill"].lower()
        for item in result["required"]["missing"]
    } == {
        "postgresql",
        "git",
    }


# ============================================================
# Test 3: Preferred skills affect final score
# ============================================================

def test_preferred_skills():

    candidate_profile = {
        "skills": [
            {"skill": "Python"},
            {"skill": "Django"},
            {"skill": "Docker"},
        ]
    }

    jd_profile = {
        "required_skills": [
            "Python",
            "Django",
        ],
        "preferred_skills": [
            "Docker",
            "AWS",
            "Redis",
            "Kubernetes",
        ],
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    # Required = 100
    assert (
        result["required"]["match_percentage"]
        == 100.0
    )

    # Preferred = 25
    assert (
        result["preferred"]["match_percentage"]
        == 25.0
    )

    # Final:
    # 100 * 0.80 + 25 * 0.20 = 85
    assert result["score"] == 85.0

    assert [
        item["matched_skill"].lower()
        for item in result["preferred"]["matched"]
    ] == ["docker"]


# ============================================================
# Test 4: Case-insensitive matching
# ============================================================

def test_skill_matching_is_case_insensitive():

    candidate_profile = {
        "skills": [
            {"skill": "PYTHON"},
            {"skill": "Django"},
        ]
    }

    jd_profile = {
        "required_skills": [
            "python",
            "django",
        ]
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    assert result["score"] == 100.0

    assert (
        result["required"]["match_percentage"]
        == 100.0
    )

    assert {
        item["matched_skill"].lower()
        for item in result["required"]["matched"]
    } == {
        "python",
        "django",
    }


# ============================================================
# Test 5: Duplicate candidate skills
# ============================================================

def test_duplicate_candidate_skills():

    candidate_profile = {
        "skills": [
            {"skill": "Python"},
            {"skill": "python"},
            {"skill": " Python "},
            {"skill": "Django"},
        ]
    }

    jd_profile = {
        "required_skills": [
            "Python",
            "Django",
        ]
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    assert result["score"] == 100.0

    assert len(
        result["candidate_skills"]
    ) == 2


# ============================================================
# Test 6: No candidate skills
# ============================================================

def test_no_candidate_skills():

    candidate_profile = {
        "skills": []
    }

    jd_profile = {
        "required_skills": [
            "Python",
            "Django",
        ],
        "preferred_skills": [
            "Docker",
        ],
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    assert result["score"] == 0.0

    assert (
        result["required"]["match_percentage"]
        == 0.0
    )

    assert (
        result["preferred"]["match_percentage"]
        == 0.0
    )

    assert result["required"]["matched"] == []

    assert len(
        result["required"]["missing"]
    ) == 2

    assert result["preferred"]["matched"] == []

    assert len(
        result["preferred"]["missing"]
    ) == 1


# ============================================================
# Test 7: No JD skill requirements
# ============================================================

def test_no_jd_skill_requirements():

    candidate_profile = {
        "skills": [
            {"skill": "Python"},
            {"skill": "Django"},
        ]
    }

    jd_profile = {
        "required_skills": [],
        "preferred_skills": [],
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    # Current scorer treats an empty requirement category
    # as 100% satisfied.
    assert result["score"] == 100.0

    assert (
        result["required"]["match_percentage"]
        == 100.0
    )

    assert (
        result["preferred"]["match_percentage"]
        == 100.0
    )


# ============================================================
# Test 8: Candidate skills as strings
# ============================================================

def test_candidate_skills_as_strings():

    candidate_profile = {
        "skills": [
            "Python",
            "Django",
            "PostgreSQL",
        ]
    }

    jd_profile = {
        "required_skills": [
            "Python",
            "Django",
            "PostgreSQL",
        ]
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    assert result["score"] == 100.0


# ============================================================
# Test 9: Missing required skills are correctly reported
# ============================================================

def test_missing_required_skills():

    candidate_profile = {
        "skills": [
            {"skill": "Python"}
        ]
    }

    jd_profile = {
        "required_skills": [
            "Python",
            "Django",
            "PostgreSQL",
        ]
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    assert [
        item["required_skill"].lower()
        for item in result["required"]["missing"]
    ] == [
        "django",
        "postgresql",
    ]


# ============================================================
# Test 10: Empty profiles
# ============================================================

def test_empty_profiles():

    candidate_profile = {}

    jd_profile = {}

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    # With no requirements, the current scoring contract
    # treats both required and preferred categories as
    # 100% satisfied.
    assert result["score"] == 100.0

    assert (
        result["required"]["match_percentage"]
        == 100.0
    )

    assert (
        result["preferred"]["match_percentage"]
        == 100.0
    )
    
def test_related_skill_does_not_count_as_match():

    candidate_profile = {
        "skills": [
            "PostgreSQL",
        ]
    }

    jd_profile = {
        "required_skills": [
            "MySQL",
        ]
    }

    result = calculate_skill_score(
        candidate_profile,
        jd_profile,
    )

    assert (
        result["required"]["match_percentage"]
        == 0.0
    )

    assert result["required"]["matched"] == []

    assert len(
        result["required"]["missing"]
    ) == 1

    missing = result["required"]["missing"][0]

    assert missing["match_type"] == "missing"

    assert "related_skill_context" in missing