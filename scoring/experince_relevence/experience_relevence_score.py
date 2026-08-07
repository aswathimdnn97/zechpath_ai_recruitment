from scoring.experince_relevence.title_matcher import score_title
from scoring.experince_relevence.experience_matcher import score_experience_years
from scoring.experince_relevence.skill_matcher import score_skills
from scoring.experince_relevence.responsibility_matcher import score_responsibilities


def experience_relevance_score(
    candidate_experience,
    parsed_jd
):

    exp_score = score_experience_years(
        candidate_experience,
        parsed_jd
    )

    skill_score = score_skills(
        candidate_experience,
        parsed_jd
    )
    title_score = score_title(
            candidate_experience,
            parsed_jd
        )

    responsibility_score = score_responsibilities(
        candidate_experience,
        parsed_jd
    )

    total = (
        title_score
        + exp_score
        + skill_score
        + responsibility_score
    )

    return {

        "experience_relevance_score": total,

        "breakdown": {

            "title": title_score,

            "experience": exp_score,

            "skills": skill_score,

            "responsibilities": responsibility_score

        }

    }