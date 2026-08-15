from typing import Any, Dict, List


def generate_recruiter_output(
    candidates: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Convert detailed ATS results into recruiter-friendly
    candidate summaries.
    """

    recruiter_results = []

    for candidate in candidates:

        candidate_score = candidate.get(
            "candidate_score",
            {}
        )

        component_scores = candidate.get(
            "component_scores",
            {}
        )

        # ----------------------------------------------------
        # Basic candidate information
        # ----------------------------------------------------

        candidate_id = candidate.get(
            "candidate_id",
            "UNKNOWN"
        )

        candidate_name = candidate.get(
            "candidate_name",
            candidate_id
        )

        rank = candidate.get(
            "rank",
            None
        )

        decision = candidate.get(
            "decision",
            "UNKNOWN"
        )

        final_score = candidate_score.get(
            "final_score",
            0.0
        )

        # ----------------------------------------------------
        # Component scores
        # ----------------------------------------------------

        skill_score = component_scores.get(
            "skill",
            {}
        ).get(
            "score",
            0.0
        )

        experience_score = component_scores.get(
            "experience",
            {}
        ).get(
            "score",
            0.0
        )

        education_score = component_scores.get(
            "education",
            {}
        ).get(
            "score",
            0.0
        )

        semantic_score = component_scores.get(
            "semantic",
            {}
        ).get(
            "score",
            0.0
        )

        # ----------------------------------------------------
        # Skill information
        # ----------------------------------------------------

        skill_data = component_scores.get(
            "skill",
            {}
        )

        required_total = skill_data.get(
            "required_total",
            0
        )

        required_matched = skill_data.get(
            "required_matched",
            0
        )

        required_match_percentage = skill_data.get(
            "required_match_percentage",
            0.0
        )

        matched_required_skills = skill_data.get(
            "matched_required_skills",
            []
        )

        missing_required_skills = skill_data.get(
            "missing_required_skills",
            []
        )

        # ----------------------------------------------------
        # Experience information
        # ----------------------------------------------------

        experience_data = component_scores.get(
            "experience",
            {}
        )

        candidate_years = experience_data.get(
            "candidate_years"
        )

        role_relevance = experience_data.get(
            "role_relevance_score",
            0.0
        )

        technology_relevance = experience_data.get(
            "technology_relevance_score",
            0.0
        )

        # ----------------------------------------------------
        # Strengths
        # ----------------------------------------------------

        strengths = []

        if skill_score >= 80:
            strengths.append(
                "Strong required skill match"
            )

        if experience_score >= 80:
            strengths.append(
                "Strong experience match"
            )

        if role_relevance >= 80:
            strengths.append(
                "Strong role relevance"
            )

        if education_score >= 80:
            strengths.append(
                "Strong education alignment"
            )

        if semantic_score >= 70:
            strengths.append(
                "Strong resume-JD semantic similarity"
            )

        # ----------------------------------------------------
        # Gaps
        # ----------------------------------------------------

        gaps = []

        if missing_required_skills:

            gaps.append(
                "Missing required skills: "
                + ", ".join(missing_required_skills)
            )

        if skill_score < 60:

            gaps.append(
                "Low overall skill match"
            )

        if experience_score < 60:

            gaps.append(
                "Low experience match"
            )

        if education_score < 60:

            gaps.append(
                "Low education alignment"
            )

        if semantic_score < 60:

            gaps.append(
                "Low semantic similarity with job description"
            )

        # ----------------------------------------------------
        # Recruiter-friendly result
        # ----------------------------------------------------

        recruiter_candidate = {

            "rank": rank,

            "candidate_id": candidate_id,

            "candidate_name": candidate_name,

            "overall_score": round(
                float(final_score),
                2
            ),

            "decision": decision,

            "score_breakdown": {

                "skill": round(
                    float(skill_score),
                    2
                ),

                "experience": round(
                    float(experience_score),
                    2
                ),

                "education": round(
                    float(education_score),
                    2
                ),

                "semantic": round(
                    float(semantic_score),
                    2
                )
            },

            "required_skill_match": {

                "matched": required_matched,

                "total": required_total,

                "percentage": round(
                    float(required_match_percentage),
                    2
                ),

                "matched_skills":
                    matched_required_skills,

                "missing_skills":
                    missing_required_skills
            },

            "experience": {

                "years": candidate_years,

                "role_relevance": round(
                    float(role_relevance),
                    2
                ),

                "technology_relevance": round(
                    float(technology_relevance),
                    2
                )
            },

            "strengths": strengths,

            "gaps": gaps
        }

        recruiter_results.append(
            recruiter_candidate
        )

    return recruiter_results