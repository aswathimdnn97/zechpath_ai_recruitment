import pytest
from scoring.semantic_scorer import (
    cosine_similarity,
    calculate_semantic_score,
)


# ============================================================
# Test 1: Identical vectors
# ============================================================

def test_cosine_similarity_identical_vectors():

    vector_a = [1.0, 2.0, 3.0]
    vector_b = [1.0, 2.0, 3.0]

    result = cosine_similarity(
        vector_a,
        vector_b
    )

    assert result == pytest.approx(
        1.0
    )


# ============================================================
# Test 2: Orthogonal vectors
# ============================================================

def test_cosine_similarity_orthogonal_vectors():

    vector_a = [1.0, 0.0]
    vector_b = [0.0, 1.0]

    result = cosine_similarity(
        vector_a,
        vector_b
    )

    assert result == pytest.approx(
        0.0
    )


# ============================================================
# Test 3: Opposite vectors
# ============================================================

def test_cosine_similarity_opposite_vectors():

    vector_a = [1.0, 0.0]
    vector_b = [-1.0, 0.0]

    result = cosine_similarity(
        vector_a,
        vector_b
    )

    assert result == pytest.approx(
        -1.0
    )


# ============================================================
# Test 4: Empty vectors
# ============================================================

def test_cosine_similarity_empty_vectors():

    result = cosine_similarity(
        [],
        []
    )

    assert result == 0.0


# ============================================================
# Test 5: Zero vector
# ============================================================

def test_cosine_similarity_zero_vector():

    result = cosine_similarity(
        [0.0, 0.0],
        [1.0, 2.0]
    )

    assert result == 0.0


# ============================================================
# Test 6: Different dimensions
# ============================================================

def test_cosine_similarity_dimension_mismatch():

    with pytest.raises(ValueError):

        cosine_similarity(
            [1.0, 2.0],
            [1.0, 2.0, 3.0]
        )


# ============================================================
# Test 7: Perfect semantic similarity
# ============================================================

def test_perfect_semantic_score():

    result = calculate_semantic_score(
        similarity=1.0
    )

    assert result["similarity"] == 1.0
    assert result["score"] == 100.0
    assert result["status"] == "calculated"


# ============================================================
# Test 8: Zero similarity
# ============================================================

def test_zero_semantic_similarity():

    result = calculate_semantic_score(
        similarity=0.0
    )

    assert result["similarity"] == 0.0
    assert result["score"] == 50.0


# ============================================================
# Test 9: Negative similarity
# ============================================================

def test_negative_semantic_similarity():

    result = calculate_semantic_score(
        similarity=-1.0
    )

    assert result["similarity"] == -1.0
    assert result["score"] == 0.0


# ============================================================
# Test 10: Similarity from embeddings
# ============================================================

def test_semantic_score_from_embeddings():

    resume_embedding = [
        1.0,
        2.0,
        3.0
    ]

    jd_embedding = [
        1.0,
        2.0,
        3.0
    ]

    result = calculate_semantic_score(
        resume_embedding=resume_embedding,
        jd_embedding=jd_embedding
    )

    assert result["similarity"] == 1.0
    assert result["score"] == 100.0
    assert result["status"] == "calculated"


# ============================================================
# Test 11: Missing embeddings
# ============================================================

def test_missing_embeddings():

    result = calculate_semantic_score(
        resume_embedding=None,
        jd_embedding=None
    )

    assert result["score"] is None
    assert result["similarity"] is None
    assert result["status"] == "no_data"


# ============================================================
# Test 12: Only resume embedding
# ============================================================

def test_only_resume_embedding():

    result = calculate_semantic_score(
        resume_embedding=[1.0, 2.0],
        jd_embedding=None
    )

    assert result["score"] is None
    assert result["similarity"] is None
    assert result["status"] == "no_data"


# ============================================================
# Test 13: Similarity above valid range
# ============================================================

def test_similarity_above_one_is_clamped():

    result = calculate_semantic_score(
        similarity=1.5
    )

    assert result["similarity"] == 1.0
    assert result["score"] == 100.0


# ============================================================
# Test 14: Similarity below valid range
# ============================================================

def test_similarity_below_minus_one_is_clamped():

    result = calculate_semantic_score(
        similarity=-1.5
    )

    assert result["similarity"] == -1.0
    assert result["score"] == 0.0


# ============================================================
# Test 15: Invalid similarity
# ============================================================

def test_invalid_similarity():

    result = calculate_semantic_score(
        similarity="invalid"
    )

    assert result["score"] is None
    assert result["similarity"] is None
    assert result["status"] == "invalid_data"


# ============================================================
# Test 16: Non-identical embeddings
# ============================================================

def test_non_identical_embeddings():

    resume_embedding = [
        1.0,
        0.0
    ]

    jd_embedding = [
        1.0,
        1.0
    ]

    result = calculate_semantic_score(
        resume_embedding=resume_embedding,
        jd_embedding=jd_embedding
    )

    assert result["similarity"] == pytest.approx(
        0.7071,
        abs=0.0001
    )

    assert result["score"] == pytest.approx(
        85.355,
        abs=0.01
    )

    assert result["status"] == "calculated"