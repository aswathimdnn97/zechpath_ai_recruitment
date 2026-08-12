from embeddings.embedding_generator import EmbeddingGenerator

from similarity.similarity import cosine_similarity

from similarity.section_similarity import (
    calculate_section_similarities
)

from similarity.hibrid_skill_similarity import (
    calculate_explicit_skill_similarity,
    calculate_hybrid_skill_similarity
)

from scoring.match_scorer import score_match


class Matcher:

    def __init__(self):

        self.embedding_generator = (
            EmbeddingGenerator()
        )

    def match(
        self,
        candidate,
        job
    ):
        """
        Match a candidate resume against a job description.
        """

        # ====================================================
        # 1. Generate overall resume embedding
        # ====================================================

        resume_embedding = (
            self.embedding_generator
            .generate_candidate_embedding(
                candidate
            )
        )

        # ====================================================
        # 2. Generate overall JD embedding
        # ====================================================

        jd_embedding = (
            self.embedding_generator
            .generate_jd_embedding(
                job
            )
        )

        # ====================================================
        # 3. Overall semantic similarity
        # ====================================================

        overall_similarity = cosine_similarity(
            resume_embedding,
            jd_embedding
        )

        # ====================================================
        # 4. Section-level similarity
        # ====================================================

        section_scores = (
            calculate_section_similarities(
                candidate,
                job
            )
        )

        # ====================================================
        # 5. Extract candidate skills
        # ====================================================

        candidate_skills = candidate.get(
            "skills",
            []
        )

        # ====================================================
        # 6. Extract JD skills
        # ====================================================

        required_skills = job.get(
            "required_skills",
            []
        )

        preferred_skills = job.get(
            "preferred_skills",
            []
        )

        # ====================================================
        # 7. Explicit skill matching
        # ====================================================

        explicit_skill_result = (
            calculate_explicit_skill_similarity(
                candidate_skills=candidate_skills,
                required_skills=required_skills,
                preferred_skills=preferred_skills
            )
        )

        # ====================================================
        # 8. Hybrid skill similarity
        # ====================================================

        hybrid_skill_result = (
            calculate_hybrid_skill_similarity(
                candidate_skills=candidate_skills,
                required_skills=required_skills,
                preferred_skills=preferred_skills
            )
        )
        print("\n===== SEMANTIC SKILL MATCHING =====")

        for item in hybrid_skill_result.get(
            "required_semantic_matches",
            []
            ):
            print(
            f"{item['required_skill']:<30}"
            f" -> "
            f"{str(item['best_candidate_skill']):<30}"
            f" similarity={item['similarity']}"
            f" matched={item['matched']}"
            )
        

        # ====================================================
        # 9. Replace section skill score
        #    with hybrid skill score
        # ====================================================

        section_scores["skills"] = (
            hybrid_skill_result["score"]
        )

        # ====================================================
        # 10. Calculate final match score
        # ====================================================

        scoring_result = score_match(
            overall_similarity=overall_similarity,
            section_similarity=section_scores
        )

        # ====================================================
        # 11. Final result
        # ====================================================

        return {

            "overall_similarity": round(
                float(overall_similarity),
                4
            ),

            "section_similarity": {
                "skills": round(
                    float(section_scores.get("skills", 0.0)),
                    4
                ),

                "experience": (
                    round(
                        float(section_scores["experience"]),
                        4
                    )
                    if section_scores.get("experience")
                    is not None
                    else None
                ),

                "projects": (
                    round(
                        float(section_scores["projects"]),
                        4
                    )
                    if section_scores.get("projects")
                    is not None
                    else None
                )
            },

            # Detailed skill analysis
            "skill_similarity": {
                "score": hybrid_skill_result[
                    "score"
                ],

                "explicit_score":
                    hybrid_skill_result[
                        "explicit_score"
                    ],

                "semantic_score":
                    hybrid_skill_result[
                        "semantic_score"
                    ],

                "required_coverage":
                    hybrid_skill_result[
                        "required_coverage"
                    ],

                "preferred_coverage":
                    hybrid_skill_result[
                        "preferred_coverage"
                    ],

                "matched_required":
                    hybrid_skill_result[
                        "matched_required"
                    ],

                "missing_required":
                    hybrid_skill_result[
                        "missing_required"
                    ],

                "matched_preferred":
                    hybrid_skill_result[
                        "matched_preferred"
                    ],

                "missing_preferred":
                    hybrid_skill_result[
                        "missing_preferred"
                    ]
            },

            # Final scoring
            "match_score":
                scoring_result[
                    "match_score"
                ],

            "match_percentage":
                scoring_result[
                    "match_percentage"
                ],

            "match_category":
                scoring_result[
                    "match_category"
                ],

            # Embeddings
            "resume_embedding":
                resume_embedding,

            "jd_embedding":
                jd_embedding
        }