from scoring.scoring_normalizer import (
    normalize_score,
    normalize_percentage,
    normalize_similarity,
)


def test_normalize_score():
    assert normalize_score(0, 0, 100) == 0.0
    assert normalize_score(50, 0, 100) == 50.0
    assert normalize_score(100, 0, 100) == 100.0


def test_normalize_similarity():
    assert normalize_similarity(-1) == 0.0
    assert normalize_similarity(-0.5) == 25.0
    assert normalize_similarity(0) == 50.0
    assert normalize_similarity(0.5) == 75.0
    assert normalize_similarity(1) == 100.0


def test_normalize_percentage():
    assert normalize_percentage(0) == 0.0
    assert normalize_percentage(50) == 50.0
    assert normalize_percentage(100) == 100.0


def test_percentage_clamping():
    assert normalize_percentage(-10) == 0.0
    assert normalize_percentage(150) == 100.0


def test_similarity_clamping():
    assert normalize_similarity(-2) == 0.0
    assert normalize_similarity(2) == 100.0


def test_none_values():
    assert normalize_percentage(None) == 0.0
    assert normalize_similarity(None) == 0.0


def test_invalid_values():
    assert normalize_percentage("invalid") == 0.0
    assert normalize_similarity("invalid") == 0.0


def test_invalid_range():
    try:
        normalize_score(50, 100, 0)
        assert False
    except ValueError:
        assert True