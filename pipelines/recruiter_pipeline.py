from  scoring.experince_relevence.experience_relevence_score import  experience_relevance_score
def recruitment_pipeline(candidate_profile, parsed_jd):

    experience_score = experience_relevance_score(
    candidate_profile,
    parsed_jd
    )

    return {
        "candidate_profile": candidate_profile,
        "parsed_jd": parsed_jd,
        "experience_score": experience_score
    }