from scoring.skill_semantic_matcher import (
    find_semantic_skill_matches,
)


class FakeEmbeddingModel:

    def encode(
        self,
        text,
        convert_to_numpy=True,
    ):
        vectors = {
            "django rest framework":
                [1.0, 0.0, 0.0],

            "rest api development":
                [0.95, 0.05, 0.0],

            "python":
                [0.0, 1.0, 0.0],

            "java":
                [0.0, 0.0, 1.0],
        }

        return vectors[text]


class FakeEmbeddingGenerator:

    def __init__(self):
        self.model = FakeEmbeddingModel()


def test_semantic_skill_match():

    result = find_semantic_skill_matches(
        candidate_skills=[
            "django rest framework",
        ],
        jd_skills=[
            "rest api development",
        ],
        embedding_generator=
            FakeEmbeddingGenerator(),
        threshold=0.70,
    )

    assert len(result) == 1

    assert (
        result[0]["jd_skill"]
        == "rest api development"
    )

    assert (
        result[0]["candidate_skill"]
        == "django rest framework"
    )

    assert (
        result[0]["match_type"]
        == "semantic"
    )

    assert result[0]["similarity"] >= 0.70


def test_semantic_skill_no_match():

    result = find_semantic_skill_matches(
        candidate_skills=[
            "java",
        ],
        jd_skills=[
            "python",
        ],
        embedding_generator=
            FakeEmbeddingGenerator(),
        threshold=0.70,
    )

    assert result == []