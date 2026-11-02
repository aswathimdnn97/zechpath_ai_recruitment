
import pytest

from api.service.salary_expectation_intent_service import (
    extract_salary_expectation_intent,
    process_salary_expectation_intent,
)


def test_empty_transcript():
    result = extract_salary_expectation_intent("")

    assert result["intent"] == "SALARY_EXPECTATION"
    assert result["status"] == "MISSING"
    assert result["expected_salary_min"] is None


def test_inr_salary_in_lpa():
    result = extract_salary_expectation_intent(
        "My expected salary is 6 LPA."
    )

    assert result["expected_salary_min"] == 600000
    assert result["expected_salary_max"] == 600000
    assert result["currency"] == "INR"
    assert result["pay_frequency"] == "ANNUAL"
    assert result["status"] == "EXTRACTED"


def test_salary_range_in_lpa():
    result = extract_salary_expectation_intent(
        "I am expecting 8 to 10 LPA."
    )

    assert result["expected_salary_min"] == 800000
    assert result["expected_salary_max"] == 1000000
    assert result["is_salary_range"] is True
    assert result["currency"] == "INR"
    assert result["pay_frequency"] == "ANNUAL"


def test_salary_range_with_hyphen():
    result = extract_salary_expectation_intent(
        "My expected package is 8-10 LPA."
    )

    assert result["expected_salary_min"] == 800000
    assert result["expected_salary_max"] == 1000000
    assert result["is_salary_range"] is True


def test_salary_in_lakhs_per_annum():
    result = extract_salary_expectation_intent(
        "I expect 5 lakhs per annum."
    )

    assert result["expected_salary_min"] == 500000
    assert result["currency"] == "INR"
    assert result["pay_frequency"] == "ANNUAL"


def test_salary_in_lacs():
    result = extract_salary_expectation_intent(
        "My salary expectation is 7 lacs."
    )

    assert result["expected_salary_min"] == 700000
    assert result["currency"] == "INR"
    assert result["pay_frequency"] == "ANNUAL"


def test_salary_in_crores():
    result = extract_salary_expectation_intent(
        "I expect 1 crore per annum."
    )

    assert result["expected_salary_min"] == 10000000
    assert result["currency"] == "INR"
    assert result["pay_frequency"] == "ANNUAL"


def test_monthly_salary_with_inr_symbol():
    result = extract_salary_expectation_intent(
        "I expect ₹50,000 per month."
    )

    assert result["expected_salary_min"] == 50000
    assert result["currency"] == "INR"
    assert result["pay_frequency"] == "MONTHLY"


def test_monthly_salary_with_rupees():
    result = extract_salary_expectation_intent(
        "My expected salary is Rs. 45000 monthly."
    )

    assert result["expected_salary_min"] == 45000
    assert result["currency"] == "INR"
    assert result["pay_frequency"] == "MONTHLY"


def test_monthly_salary_range():
    result = extract_salary_expectation_intent(
        "I am looking for 40000 to 50000 per month."
    )

    assert result["expected_salary_min"] == 40000
    assert result["expected_salary_max"] == 50000
    assert result["pay_frequency"] == "MONTHLY"
    assert result["is_salary_range"] is True


def test_salary_in_thousands():
    result = extract_salary_expectation_intent(
        "My expected package is 8k per month."
    )

    assert result["expected_salary_min"] == 8000
    assert result["pay_frequency"] == "MONTHLY"


def test_salary_amount_in_words():
    result = extract_salary_expectation_intent(
        "I expect five LPA."
    )

    assert result["expected_salary_min"] == 500000
    assert result["currency"] == "INR"


def test_salary_with_usd():
    result = extract_salary_expectation_intent(
        "I expect USD 5000 per month."
    )

    assert result["expected_salary_min"] == 5000
    assert result["currency"] == "USD"
    assert result["pay_frequency"] == "MONTHLY"


def test_salary_negotiable_without_amount():
    result = extract_salary_expectation_intent(
        "My salary expectation is negotiable."
    )

    assert result["status"] == "VAGUE"
    assert result["negotiable"] is True
    assert "expected_salary" in result["vague_fields"]


def test_salary_amount_and_negotiable():
    result = extract_salary_expectation_intent(
        "I expect 6 LPA, but it is negotiable."
    )

    assert result["expected_salary_min"] == 600000
    assert result["negotiable"] is True
    assert result["status"] == "EXTRACTED"


def test_flexible_salary_expectation():
    result = extract_salary_expectation_intent(
        "I am flexible with the salary depending on the role."
    )

    assert result["negotiable"] is True
    assert result["status"] == "VAGUE"


def test_current_salary_is_not_expected_salary():
    result = extract_salary_expectation_intent(
        "My current salary is 5 LPA."
    )

    assert result["expected_salary_min"] is None
    assert result["status"] == "MISSING"


def test_unrelated_answer():
    result = extract_salary_expectation_intent(
        "I have completed my Python training."
    )

    assert result["expected_salary_min"] is None
    assert result["status"] == "MISSING"


def test_ambiguous_amount_without_frequency_or_currency():
    result = extract_salary_expectation_intent(
        "My expected salary is 50000."
    )

    assert result["expected_salary_min"] == 50000
    assert result["currency"] == "UNKNOWN"
    assert result["pay_frequency"] == "UNKNOWN"
    assert result["status"] == "PARTIAL"


def test_reversed_salary_range_is_not_accepted():
    result = extract_salary_expectation_intent(
        "My expected salary is 10 to 8 LPA."
    )

    assert result["expected_salary_min"] is None
    assert result["status"] == "MISSING"


def test_invalid_input():
    result = extract_salary_expectation_intent(None)

    assert result["status"] == "MISSING"
    assert result["expected_salary_min"] is None


def test_compatibility_function():
    result = process_salary_expectation_intent(
        "I expect 6 LPA."
    )

    assert result["intent"] == "SALARY_EXPECTATION"
    assert result["expected_salary_min"] == 600000


def test_evidence_is_preserved():
    result = extract_salary_expectation_intent(
        "My expected salary is 6 LPA."
    )

    assert result["evidence"]["salary"] is not None
    assert result["evidence"]["salary_amount"] is not None


def test_unknown_currency_and_frequency_are_not_guessed():
    result = extract_salary_expectation_intent(
        "I expect 50000."
    )

    assert result["currency"] == "UNKNOWN"
    assert result["pay_frequency"] == "UNKNOWN"
