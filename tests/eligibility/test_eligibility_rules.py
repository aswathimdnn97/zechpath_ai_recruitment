
import pytest
from pydantic import ValidationError

from eligibility.eligibility_rules import (
    EligibilityRuleSet,
    ScoreCutoffRule,
    ExperienceRule,
)


def test_default_eligibility_rules():
    rules = EligibilityRuleSet()

    assert rules.cutoffs.minimum_ats_score == 70.0
    assert rules.cutoffs.review_score_threshold == 60.0
    assert rules.location.allowed_locations == []
    assert rules.location.remote_allowed is None
    assert rules.availability.maximum_notice_period_days is None


def test_custom_role_cutoffs():
    rules = EligibilityRuleSet(
        role_category="backend",
        cutoffs={
            "minimum_ats_score": 80,
            "review_score_threshold": 65,
        },
    )

    assert rules.cutoffs.minimum_ats_score == 80
    assert rules.cutoffs.review_score_threshold == 65


def test_invalid_score_cutoffs():
    with pytest.raises(ValidationError):
        ScoreCutoffRule(
            minimum_ats_score=50,
            review_score_threshold=60,
        )


def test_invalid_experience_range():
    with pytest.raises(ValidationError):
        ExperienceRule(
            minimum_years=6,
            maximum_years=3,
        )


def test_location_and_availability_rules():
    rules = EligibilityRuleSet(
        location={
            "allowed_locations": ["Kochi", "Bengaluru"],
            "remote_allowed": True,
            "enforcement": "mandatory",
        },
        availability={
            "maximum_notice_period_days": 30,
            "enforcement": "preferred",
        },
    )

    assert rules.location.remote_allowed is True
    assert "Kochi" in rules.location.allowed_locations
    assert rules.availability.maximum_notice_period_days == 30
