from scoring.education_score import (
    normalize_text,
    detect_degree_level,
    calculate_degree_score,
    calculate_field_score,
    calculate_education_score,
)


# ============================================================
# Test 1: Text normalization
# ============================================================

def test_normalize_text():

    result = normalize_text(
        "Bachelor's Degree in Computer Science!"
    )

    assert result == (
        "bachelor s degree in computer science"
    )


# ============================================================
# Test 2: Bachelor degree detection
# ============================================================

def test_detect_bachelor_degree():

    result = detect_degree_level(
        "B.Tech in Electronics and Communication"
    )

    assert result == "bachelor"


# ============================================================
# Test 3: Master degree detection
# ============================================================

def test_detect_master_degree():

    result = detect_degree_level(
        "MCA"
    )

    assert result == "master"


# ============================================================
# Test 4: Matching degree
# ============================================================

def test_matching_degree():

    candidate_education = (
        "Bachelor of Technology in Electronics"
    )

    jd_education = [
        "Bachelor's degree in Computer Science, "
        "Information Technology, Electronics, "
        "or related field.",
        "B.Tech / B.E / MCA / M.Sc "
        "(Computer Science)"
    ]

    result = calculate_degree_score(
        candidate_education,
        jd_education
    )

    assert result == 100.0


# ============================================================
# Test 5: Different degree level
# ============================================================

def test_different_degree_level():

    candidate_education = (
        "Bachelor of Technology in Electronics"
    )

    jd_education = [
        "Master's degree in Computer Science"
    ]

    result = calculate_degree_score(
        candidate_education,
        jd_education
    )

    assert result == 40.0


# ============================================================
# Test 6: Missing candidate education
# ============================================================

def test_missing_candidate_education():

    candidate_education = ""

    jd_education = [
        "Bachelor's degree in Computer Science"
    ]

    result = calculate_degree_score(
        candidate_education,
        jd_education
    )

    assert result == 0.0


# ============================================================
# Test 7: No JD education requirement
# ============================================================

def test_no_jd_education_requirement():

    candidate_education = (
        "Bachelor of Technology"
    )

    jd_education = []

    result = calculate_degree_score(
        candidate_education,
        jd_education
    )

    assert result == 100.0


# ============================================================
# Test 8: Matching education field
# ============================================================

def test_matching_education_field():

    candidate_education = (
        "Bachelor of Technology "
        "in Electronics and Communication Engineering"
    )

    jd_education = [
        "Bachelor's degree in Computer Science, "
        "Information Technology, Electronics, "
        "or related field."
    ]

    result = calculate_field_score(
        candidate_education,
        jd_education
    )

    assert result == 100.0


# ============================================================
# Test 9: Non-matching education field
# ============================================================

def test_non_matching_education_field():

    candidate_education = (
        "Bachelor of Technology in Mechanical Engineering"
    )

    jd_education = [
        "Bachelor's degree in Computer Science, "
        "Information Technology, Electronics, "
        "or related field."
    ]

    result = calculate_field_score(
        candidate_education,
        jd_education
    )

    assert result == 40.0


# ============================================================
# Test 10: Full education score - perfect match
# ============================================================

def test_full_education_score():

    candidate_profile = {
        "resume_text": {
            "education": [
                {
                    "degree_type": "Bachelor of Technology",
                    "field_of_study": (
                        "Electronics and Communication Engineering"
                    ),
                    "institution": "ABC Engineering College",
                    "graduation_year": "2021"
                }
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "education": [
                "Bachelor's degree in Computer Science, "
                "Information Technology, Electronics, "
                "or related field.",
                "B.Tech / B.E / MCA / M.Sc "
                "(Computer Science)"
            ]
        }
    }

    result = calculate_education_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 100.0
    assert result["degree_score"] == 100.0
    assert result["field_score"] == 100.0

    assert result["status"] == "calculated"


# ============================================================
# Test 11: Full education score - degree match only
# ============================================================

def test_education_score_degree_match_only():

    candidate_profile = {
        "resume_text": {
            "education": [
                {
                    "degree_type": "Bachelor of Technology",
                    "field_of_study": (
                        "Mechanical Engineering"
                    ),
                    "institution": "ABC College",
                    "graduation_year": "2021"
                }
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "education": [
                "Bachelor's degree in Computer Science, "
                "Information Technology, Electronics, "
                "or related field."
            ]
        }
    }

    result = calculate_education_score(
        candidate_profile,
        jd_profile
    )

    # Degree = 100
    # Field  = 40
    #
    # 100 * 0.60 + 40 * 0.40 = 76

    assert result["degree_score"] == 100.0
    assert result["field_score"] == 40.0
    assert result["score"] == 76.0


# ============================================================
# Test 12: Missing candidate education
# ============================================================

def test_missing_candidate_education_profile():

    candidate_profile = {
        "resume_text": {
            "education": []
        }
    }

    jd_profile = {
        "resume_text": {
            "education": [
                "Bachelor's degree in Computer Science"
            ]
        }
    }

    result = calculate_education_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 0.0
    assert result["degree_score"] == 0.0
    assert result["field_score"] == 0.0
    assert result["status"] == "no_data"


# ============================================================
# Test 13: No JD education requirement
# ============================================================

def test_no_jd_education_profile():

    candidate_profile = {
        "resume_text": {
            "education": [
                {
                    "degree_type": "Bachelor of Technology",
                    "field_of_study": "Electronics",
                    "institution": "ABC College",
                    "graduation_year": "2021"
                }
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "education": []
        }
    }

    result = calculate_education_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 100.0
    assert result["status"] == "not_required"


# ============================================================
# Test 14: Multiple candidate education records
# ============================================================

def test_multiple_education_records():

    candidate_profile = {
        "resume_text": {
            "education": [
                {
                    "degree_type": "Bachelor of Technology",
                    "field_of_study": "Mechanical Engineering",
                    "institution": "ABC College",
                    "graduation_year": "2019"
                },
                {
                    "degree_type": "MCA",
                    "field_of_study": "Computer Science",
                    "institution": "XYZ University",
                    "graduation_year": "2022"
                }
            ]
        }
    }

    jd_profile = {
        "resume_text": {
            "education": [
                "Master's degree in Computer Science"
            ]
        }
    }

    result = calculate_education_score(
        candidate_profile,
        jd_profile
    )

    # The MCA / Computer Science record should
    # be selected as the best match.

    assert result["score"] == 100.0

    assert (
        result["best_matching_education"]
        ["degree_type"]
        == "MCA"
    )


# ============================================================
# Test 15: Empty profiles
# ============================================================

def test_empty_profiles():

    candidate_profile = {}
    jd_profile = {}

    result = calculate_education_score(
        candidate_profile,
        jd_profile
    )

    assert result["score"] == 0.0
    assert result["degree_score"] == 0.0
    assert result["field_score"] == 0.0
    assert result["status"] == "not_required"