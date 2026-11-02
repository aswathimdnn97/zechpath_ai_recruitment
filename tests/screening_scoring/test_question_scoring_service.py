
import pytest

from api.service.question_scoring_service import (
    QuestionScoringError,
    score_question,
)
from api.service.scoring_config_service import load_scoring_config


@pytest.fixture
def config():
    return load_scoring_config()


@pytest.fixture
def dimension_scores():
    return {
        "clarity": 80,
        "relevance": 90,
        "completeness": 70,
        "consistency": 100,
    }


def test_calculate_question_score(config, dimension_scores):

    result = score_question(
        question_id="PYF_EXP_001",
        dimension_scores=dimension_scores,
        config=config,
    )

    # (80 * 0.20) + (90 * 0.35)
    # + (70 * 0.30) + (100 * 0.15) = 83.5

    assert result["total_score"] == 83.5
    assert result["score_percentage"] == 83.5
    assert result["max_score"] == 100


def test_dimension_breakdown_is_generated(
    config,
    dimension_scores,
):

    result = score_question(
        question_id="PYF_EXP_001",
        dimension_scores=dimension_scores,
        config=config,
    )

    assert len(result["dimension_scores"]) == 4

    assert result["dimension_scores"]["clarity"]["score"] == 80
    assert result["dimension_scores"]["relevance"]["score"] == 90


def test_weighted_contributions(config, dimension_scores):

    result = score_question(
        question_id="PYF_EXP_001",
        dimension_scores=dimension_scores,
        config=config,
    )

    breakdown = result["dimension_scores"]

    assert breakdown["clarity"]["weighted_contribution"] == 16
    assert breakdown["relevance"]["weighted_contribution"] == 31.5
    assert breakdown["completeness"]["weighted_contribution"] == 21
    assert breakdown["consistency"]["weighted_contribution"] == 15


def test_explanations_are_included(config, dimension_scores):

    explanations = {
        "clarity": "Answer is clearly structured.",
        "relevance": "Answer directly addresses the question.",
    }

    result = score_question(
        question_id="PYF_EXP_001",
        dimension_scores=dimension_scores,
        explanations=explanations,
        config=config,
    )

    assert (
        result["dimension_scores"]["clarity"]["explanation"]
        == "Answer is clearly structured."
    )


def test_reject_score_above_100(config, dimension_scores):

    dimension_scores["clarity"] = 120

    with pytest.raises(QuestionScoringError):
        score_question(
            "PYF_EXP_001",
            dimension_scores,
            config=config,
        )


def test_reject_missing_dimension(config):

    scores = {
        "clarity": 80,
        "relevance": 90,
        "completeness": 70,
    }

    with pytest.raises(QuestionScoringError):
        score_question(
            "PYF_EXP_001",
            scores,
            config=config,
        )


def test_reject_negative_score(config, dimension_scores):

    dimension_scores["clarity"] = -10

    with pytest.raises(QuestionScoringError):
        score_question(
            "PYF_EXP_001",
            dimension_scores,
            config=config,
        )


def test_reject_empty_question_id(config, dimension_scores):

    with pytest.raises(QuestionScoringError):
        score_question(
            "",
            dimension_scores,
            config=config,
        )
