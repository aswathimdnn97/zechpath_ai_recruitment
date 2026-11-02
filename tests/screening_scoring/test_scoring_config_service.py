
import json

import pytest

from api.service.scoring_config_service import (
    ScoringConfigurationError,
    load_scoring_config,
)


@pytest.fixture
def valid_config():
    return {
        "scoring_version": "1.0",
        "score_scale": {
            "minimum": 0,
            "maximum": 100
        },
        "dimensions": {
            "clarity": {
                "weight": 0.20,
                "description": "Clarity"
            },
            "relevance": {
                "weight": 0.35,
                "description": "Relevance"
            },
            "completeness": {
                "weight": 0.30,
                "description": "Completeness"
            },
            "consistency": {
                "weight": 0.15,
                "description": "Consistency"
            }
        },
        "normalization": {
            "method": "percentage",
            "precision": 2
        },
        "review": {
            "flag_unanswered": True,
            "flag_vague_answers": True,
            "flag_off_topic_answers": True,
            "flag_possible_contradictions": True
        }
    }


def test_load_valid_scoring_config(tmp_path, valid_config):
    config_file = tmp_path / "scoring_weights.json"

    config_file.write_text(
        json.dumps(valid_config),
        encoding="utf-8"
    )

    config = load_scoring_config(config_file)

    assert config.scoring_version == "1.0"
    assert config.dimensions.clarity.weight == 0.20
    assert config.dimensions.relevance.weight == 0.35


def test_reject_invalid_total_weight(tmp_path, valid_config):
    valid_config["dimensions"]["clarity"]["weight"] = 0.50

    config_file = tmp_path / "scoring_weights.json"
    config_file.write_text(
        json.dumps(valid_config),
        encoding="utf-8"
    )

    with pytest.raises(ScoringConfigurationError):
        load_scoring_config(config_file)


def test_reject_missing_dimension(tmp_path, valid_config):
    del valid_config["dimensions"]["clarity"]

    config_file = tmp_path / "scoring_weights.json"
    config_file.write_text(
        json.dumps(valid_config),
        encoding="utf-8"
    )

    with pytest.raises(ScoringConfigurationError):
        load_scoring_config(config_file)


def test_reject_invalid_weight(tmp_path, valid_config):
    valid_config["dimensions"]["relevance"]["weight"] = 1.5

    config_file = tmp_path / "scoring_weights.json"
    config_file.write_text(
        json.dumps(valid_config),
        encoding="utf-8"
    )

    with pytest.raises(ScoringConfigurationError):
        load_scoring_config(config_file)


def test_reject_invalid_score_range(tmp_path, valid_config):
    valid_config["score_scale"] = {
        "minimum": 100,
        "maximum": 0
    }

    config_file = tmp_path / "scoring_weights.json"
    config_file.write_text(
        json.dumps(valid_config),
        encoding="utf-8"
    )

    with pytest.raises(ScoringConfigurationError):
        load_scoring_config(config_file)


def test_reject_missing_config(tmp_path):
    missing_file = tmp_path / "missing.json"

    with pytest.raises(ScoringConfigurationError):
        load_scoring_config(missing_file)
