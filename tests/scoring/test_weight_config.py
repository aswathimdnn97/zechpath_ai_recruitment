import pytest

from scoring.weight_config import (
    DEFAULT_WEIGHTS,
    ROLE_CATEGORY_WEIGHTS,
    normalize_job_title,
    detect_role_category,
    validate_weights,
    get_weights,
)


# ============================================================
# Test 1: Job title normalization
# ============================================================

def test_normalize_job_title():

    result = normalize_job_title(
        "  Python   Developer  "
    )

    assert result == "python developer"


# ============================================================
# Test 2: Empty / invalid job title
# ============================================================

def test_normalize_invalid_job_title():

    assert normalize_job_title(None) == ""
    assert normalize_job_title(123) == ""


# ============================================================
# Test 3: Default weights are valid
# ============================================================

def test_default_weights_are_valid():

    assert validate_weights(
        DEFAULT_WEIGHTS
    ) is True


# ============================================================
# Test 4: All role-category weights are valid
# ============================================================

def test_all_role_category_weights_are_valid():

    for category, weights in ROLE_CATEGORY_WEIGHTS.items():

        assert validate_weights(
            weights
        ) is True


# ============================================================
# Test 5: Python Developer → backend
# ============================================================

def test_python_developer_category():

    result = detect_role_category(
        "Python Developer"
    )

    assert result == "backend"


# ============================================================
# Test 6: Django Developer → backend
# ============================================================

def test_django_developer_category():

    result = detect_role_category(
        "Django Developer"
    )

    assert result == "backend"


# ============================================================
# Test 7: Java Developer → backend
# ============================================================

def test_java_developer_category():

    result = detect_role_category(
        "Java Developer"
    )

    assert result == "backend"


# ============================================================
# Test 8: Senior Python Developer → backend
# ============================================================

def test_senior_python_developer_category():

    result = detect_role_category(
        "Senior Python Developer"
    )

    assert result == "backend"


# ============================================================
# Test 9: React Developer → frontend
# ============================================================

def test_react_developer_category():

    result = detect_role_category(
        "React Developer"
    )

    assert result == "frontend"


# ============================================================
# Test 10: Frontend Engineer → frontend
# ============================================================

def test_frontend_engineer_category():

    result = detect_role_category(
        "Frontend Engineer"
    )

    assert result == "frontend"


# ============================================================
# Test 11: Data Scientist → data_ml
# ============================================================

def test_data_scientist_category():

    result = detect_role_category(
        "Data Scientist"
    )

    assert result == "data_ml"


# ============================================================
# Test 12: Machine Learning Engineer → data_ml
# ============================================================

def test_machine_learning_category():

    result = detect_role_category(
        "Machine Learning Engineer"
    )

    assert result == "data_ml"


# ============================================================
# Test 13: DevOps Engineer → devops
# ============================================================

def test_devops_category():

    result = detect_role_category(
        "DevOps Engineer"
    )

    assert result == "devops"


# ============================================================
# Test 14: Engineering Manager → management
# ============================================================

def test_management_category():

    result = detect_role_category(
        "Engineering Manager"
    )

    assert result == "management"


# ============================================================
# Test 15: Entry-level role
# ============================================================

def test_entry_level_category():

    result = detect_role_category(
        "Entry Level Python Developer"
    )

    assert result == "backend"