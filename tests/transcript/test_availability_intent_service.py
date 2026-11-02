
import pytest
from datetime import date

from api.service.availability_intent_service import (
    extract_availability_intent,
    process_availability_intent,
)


REFERENCE_DATE = date(2026, 10, 31)


def test_empty_transcript():
    result = extract_availability_intent("")

    assert result["intent"] == "AVAILABILITY"
    assert result["status"] == "MISSING"
    assert result["availability_status"] == "UNKNOWN"


def test_immediate_availability():
    result = extract_availability_intent(
        "I am available immediately."
    )

    assert result["availability_status"] == "IMMEDIATE"
    assert result["status"] == "EXTRACTED"


def test_can_join_immediately():
    result = extract_availability_intent(
        "I can join immediately."
    )

    assert result["availability_status"] == "IMMEDIATE"


def test_no_notice_period():
    result = extract_availability_intent(
        "I don't have a notice period."
    )

    assert result["availability_status"] == "IMMEDIATE"
    assert result["notice_period_status"] == "NOT_REQUIRED"


def test_notice_period_in_days():
    result = extract_availability_intent(
        "I have a notice period of 30 days."
    )

    assert result["notice_period_days"] == 30
    assert result["notice_period_status"] == "NOT_STARTED"
    assert result["availability_status"] == "AFTER_NOTICE_PERIOD"


def test_notice_period_in_words():
    result = extract_availability_intent(
        "I have a notice period of two months."
    )

    assert result["notice_period_days"] == 60


def test_notice_period_in_weeks():
    result = extract_availability_intent(
        "I have a notice period of two weeks."
    )

    assert result["notice_period_days"] == 14


def test_currently_serving_notice():
    result = extract_availability_intent(
        "I am currently serving my notice period."
    )

    assert result["notice_period_status"] == "SERVING"
    assert result["availability_status"] == "AFTER_NOTICE_PERIOD"


def test_remaining_notice_period():
    result = extract_availability_intent(
        "I am serving my notice period and only 15 days are remaining."
    )

    assert result["notice_period_status"] == "SERVING"
    assert result["remaining_notice_period_days"] == 15


def test_explicit_joining_date():
    result = extract_availability_intent(
        "I can join from 15 November 2026.",
        reference_date=REFERENCE_DATE,
    )

    assert result["earliest_joining_date"] == "2026-11-15"
    assert result["availability_status"] == "AVAILABLE_FROM_DATE"


def test_joining_date_without_year():
    result = extract_availability_intent(
        "I will be available from 15 November.",
        reference_date=REFERENCE_DATE,
    )

    assert result["earliest_joining_date"] == "2026-11-15"


def test_joining_date_in_future():
    result = extract_availability_intent(
        "I can join in 2 weeks.",
        reference_date=REFERENCE_DATE,
    )

    assert result["earliest_joining_in_days"] == 14
    assert result["earliest_joining_date"] == "2026-11-14"


def test_joining_after_one_month():
    result = extract_availability_intent(
        "I can join after one month.",
        reference_date=REFERENCE_DATE,
    )

    assert result["earliest_joining_in_days"] == 30
    assert result["earliest_joining_date"] == "2026-11-30"


def test_not_available():
    result = extract_availability_intent(
        "I am not available to join currently."
    )

    assert result["availability_status"] == "NOT_AVAILABLE"


def test_vague_availability():
    result = extract_availability_intent(
        "I will be available soon."
    )

    assert result["status"] == "VAGUE"
    assert "availability_status" in result["vague_fields"]


def test_missing_availability():
    result = extract_availability_intent(
        "I completed my degree last year."
    )

    assert result["availability_status"] == "UNKNOWN"
    assert result["status"] == "MISSING"


def test_invalid_input():
    result = extract_availability_intent(None)

    assert result["status"] == "MISSING"
    assert result["availability_status"] == "UNKNOWN"


def test_compatibility_function():
    result = process_availability_intent(
        "I am available immediately."
    )

    assert result["intent"] == "AVAILABILITY"
    assert result["availability_status"] == "IMMEDIATE"


def test_invalid_calendar_date_is_not_extracted():
    result = extract_availability_intent(
        "I can join from 35 November 2026.",
        reference_date=REFERENCE_DATE,
    )

    assert result["earliest_joining_date"] is None


def test_conflicting_availability():
    result = extract_availability_intent(
        "I am not available, but I can join immediately."
    )

    assert result["availability_status"] == "UNKNOWN"
