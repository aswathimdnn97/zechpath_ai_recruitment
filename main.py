from pathlib import Path

from utils.logger import logger

from document_processing.resume.resume_pipeline import (
    resume_pipeline,
)

from document_processing.job_description.job_description_pipeline import (
    job_description_pipeline,
)

from scoring.ats_scoring_engine import (
    calculate_ats_score,
)

from embeddings.embedding_generator import (
    EmbeddingGenerator,
)

from embeddings.embedding_text_builder import (
    profile_to_embedding_text,
    build_jd_embedding_text,
)

from scoring.ranking.candidate_ranker import (
    get_candidate_score,
)

from scoring.ranking.ranking_pipeline import (
    rank_and_shortlist,
)

from scoring.ranking.top_candidates import (
    get_top_candidates,
)

from scoring.ranking.recruiters_output import (
    generate_recruiter_output,
)


# ============================================================
# CONFIGURATION
# ============================================================

RESUME_FOLDER = Path(
    "data/resume/pdf"
)

JOB_DESCRIPTION_FILE = (
    "data/job_descriptions/"
    "jd_python_developer.pdf"
)

TOP_N = 5

SHORTLIST_THRESHOLD = 80.0

REVIEW_THRESHOLD = 60.0


# ============================================================
# APPLICATION START
# ============================================================

logger.info(
    "Recruitment pipeline started"
)


# ============================================================
# 1. PARSE JOB DESCRIPTION
# ============================================================

print(
    "\n================ JOB DESCRIPTION PARSING ================"
)

jd_json = job_description_pipeline(
    JOB_DESCRIPTION_FILE
)

print(
    "\n================ JD JSON ================"
)

print(jd_json)


# ============================================================
# 2. INITIALIZE EMBEDDING GENERATOR
# ============================================================

embedding_generator = EmbeddingGenerator()


# ============================================================
# 3. GENERATE JD EMBEDDING
# ============================================================

jd_embedding_text = build_jd_embedding_text(
    jd_json
)

print(
    "\n================ JD EMBEDDING TEXT ================"
)

print(jd_embedding_text)


if not jd_embedding_text:
    raise ValueError(
        "Cannot generate JD embedding: "
        "JD produced empty embedding text. "
        "Check job_description_pipeline() output."
    )


jd_embedding = (
    embedding_generator.generate_embedding(
        jd_embedding_text
    )
)


# ============================================================
# 4. FIND RESUMES
# ============================================================

resume_files = sorted(
    RESUME_FOLDER.glob("*.pdf")
)

print(
    f"\nFound {len(resume_files)} resume(s)"
)


if not resume_files:

    print(
        f"No PDF resumes found in "
        f"{RESUME_FOLDER}"
    )

    raise SystemExit(1)


# ============================================================
# 5. ATS RESULTS
# ============================================================

ats_results = []


# ============================================================
# 6. PROCESS EACH RESUME
# ============================================================

for resume_file in resume_files:

    print("\n")
    print("=" * 70)

    print(
        f"PROCESSING RESUME: "
        f"{resume_file.name}"
    )

    print("=" * 70)

    try:

        # ====================================================
        # 6.1 PARSE RESUME
        # ====================================================

        logger.info(
            f"Resume uploaded: "
            f"{resume_file.name}"
        )

        resume_json = resume_pipeline(
            str(resume_file)
        )

        print(
            "\n================ PERSONAL INFORMATION DEBUG ================"
        )

        print(resume_json)

        if not isinstance(
            resume_json,
            dict
        ):
            raise ValueError(
                "resume_pipeline() "
                "did not return a dictionary."
            )


       # ====================================================
        # 6.2 EXTRACT PROFILE DATA
        # ====================================================

        original_profile = resume_json.get(
            "original_profile",
            {}
        )

        masked_profile = resume_json.get(
            "masked_profile",
            {}
        )

        if not isinstance(original_profile, dict):
            original_profile = {}

        if not isinstance(masked_profile, dict):
            masked_profile = {}


        # ====================================================
        # 6.3 GET CANDIDATE ID
        # ====================================================

        candidate_id = resume_json.get("candidate_id")

        if not candidate_id:
            raise ValueError(
                "resume_pipeline() did not return candidate_id."
            )

        candidate_id = str(candidate_id).strip()


        # ====================================================
        # 6.4 GET CANDIDATE NAME
        # ====================================================

        personal_information = original_profile.get(
            "personal_information",
            {}
        )

        if not isinstance(personal_information, dict):
            personal_information = {}

        candidate_name = personal_information.get(
            "name"
        )

        if isinstance(candidate_name, str):
            candidate_name = candidate_name.strip()

        if not candidate_name:
            candidate_name = candidate_id


        # ====================================================
        # 6.5 IDENTITY DEBUG
        # ====================================================

        print(
            "\n================ CANDIDATE IDENTITY ================"
        )

        print(
            "Candidate Name:",
            candidate_name
        )

        print(
            "Candidate ID:",
            candidate_id
        )


        # ====================================================
        # 6.6 BIAS REPORT
        # ====================================================

        bias_report = resume_json.get(
            "bias_report",
            {}
        )

        print(
            "\n================ BIAS REPORT ================"
        )

        print(bias_report)


        # ====================================================
        # 6.7 VALIDATE MASKED PROFILE
        # ====================================================

        if not masked_profile:
            raise ValueError(
                "resume_pipeline() did not return "
                "a valid masked_profile."
            )

        if "personal_information" in masked_profile:
            raise ValueError(
                "Masked profile contains personal_information. "
                "Personal attributes must not be passed to ATS scoring."
            )

        print(
            "\n================ MASKING VALIDATION ================"
        )

        print(
            "Candidate ID:",
            candidate_id
        )

        print(
            "Candidate Name:",
            candidate_name
        )

        print(
            "Personal information in masked profile:",
            "personal_information" in masked_profile
        )


        # ====================================================
        # 6.8 RESUME EMBEDDING TEXT
        # ====================================================

        resume_embedding_text = (
            profile_to_embedding_text(
                masked_profile
            )
        )

        if not resume_embedding_text:

            raise ValueError(
                "Cannot generate resume embedding: "
                "masked profile produced empty text."
            )


        # ====================================================
        # 6.9 RESUME EMBEDDING
        # ====================================================

        resume_embedding = (
            embedding_generator.generate_embedding(
                resume_embedding_text
            )
        )


        # ====================================================
        # 6.10 ATS SCORING
        # ====================================================

        ats_result = calculate_ats_score(
            candidate_profile=masked_profile,
            jd_profile=jd_json,
            resume_embedding=resume_embedding,
            jd_embedding=jd_embedding,
            embedding_generator=embedding_generator,
        )

        if not isinstance(
            ats_result,
            dict
        ):
            raise ValueError(
                "calculate_ats_score() "
                "did not return a dictionary."
            )


        # ====================================================
        # 6.11 ATTACH IDENTITY AFTER SCORING
        # ====================================================

        ats_result["candidate_id"] = candidate_id

        ats_result["candidate_name"] = candidate_name

        ats_result["bias_report"] = bias_report


        # ====================================================
        # 6.12 DISPLAY ATS RESULT
        # ====================================================

        print(
            "\n================ ATS SCORE ================"
        )

        print(
            "Candidate:",
            candidate_name
        )

        print(
            "Candidate ID:",
            candidate_id
        )

        print(
            "Final ATS Score:",
            get_candidate_score(
                ats_result
            )
        )

        component_scores = ats_result.get(
            "component_scores",
            {}
        )

        print("\nComponent Scores:")

        print(
            "Skill:",
            component_scores
            .get("skill", {})
            .get("score", 0.0)
        )

        print(
            "Experience:",
            component_scores
            .get("experience", {})
            .get("score", 0.0)
        )

        print(
            "Education:",
            component_scores
            .get("education", {})
            .get("score", 0.0)
        )

        print(
            "Semantic:",
            component_scores
            .get("semantic", {})
            .get("score", 0.0)
        )


        # ====================================================
        # 6.13 STORE RESULT
        # ====================================================

        print(
            "\nDEBUG - ATS RESULT IDENTITY"
        )

        print(
            "candidate_id:",
            ats_result.get("candidate_id")
        )

        print(
            "candidate_name:",
            ats_result.get("candidate_name")
        )

        ats_results.append(
            ats_result
        )

        print(
            "\nCandidate scoring completed."
        )

    except Exception as error:

        logger.exception(
            f"Error processing "
            f"{resume_file.name}"
        )

        print(
            f"\nERROR processing "
            f"{resume_file.name}: "
            f"{error}"
        )

        continue


# ============================================================
# 7. CHECK ATS RESULTS
# ============================================================

print(
    "\n================ SCORING ENGINE ================"
)

print(
    "Successfully scored candidates:",
    len(ats_results)
)

if not ats_results:

    print(
        "No candidates were successfully scored."
    )

    raise SystemExit(1)


# ============================================================
# 8. RANKING + SHORTLISTING
# ============================================================

print(
    "\n================ RANKING & SHORTLISTING ================"
)

ranked_results = rank_and_shortlist(
    ats_results,
    shortlist_threshold=SHORTLIST_THRESHOLD,
    review_threshold=REVIEW_THRESHOLD,
)


# ============================================================
# 9. FINAL RANKING
# ============================================================

print(
    "\n================ FINAL CANDIDATE RANKING ================"
)

print(
    f"{'Rank':<8}"
    f"{'Candidate':<30}"
    f"{'Score':<12}"
    f"{'Decision'}"
)

print("-" * 80)

for candidate in ranked_results:


    rank = candidate.get("rank", "-")

    candidate_name = (
        candidate.get("candidate_name")
        or candidate.get("candidate_id")
        or "Unknown"
    )

    score = get_candidate_score(
        candidate
    )

    decision = candidate.get(
        "decision",
        "UNKNOWN"
    )

    print(
        f"{rank:<8}"
        f"{candidate_name:<30}"
        f"{score:<12.2f}"
        f"{decision}"
    )


# ============================================================
# 10. TOP N CANDIDATES
# ============================================================

top_candidates = get_top_candidates(
    ranked_results,
    top_n=TOP_N
)

print(
    f"\n================ TOP {TOP_N} CANDIDATES ================"
)

for candidate in top_candidates:

    rank = candidate.get("rank", "-")

    candidate_name = (
        candidate.get("candidate_name")
        or candidate.get("candidate_id")
        or "Unknown"
    )

    candidate_id = (
        candidate.get("candidate_id")
        or "UNKNOWN"
    )

    score = get_candidate_score(
        candidate
    )

    decision = candidate.get(
        "decision",
        "UNKNOWN"
    )

    print(
        f"Rank {rank} | "
        f"{candidate_name} | "
        f"ID: {candidate_id} | "
        f"Score: {score:.2f} | "
        f"{decision}"
    )


# ============================================================
# 11. CANDIDATE ZONES
# ============================================================

shortlisted_candidates = [
    candidate
    for candidate in ranked_results
    if candidate.get("decision") == "SHORTLIST"
]

review_candidates = [
    candidate
    for candidate in ranked_results
    if candidate.get("decision") == "REVIEW"
]

rejected_candidates = [
    candidate
    for candidate in ranked_results
    if candidate.get("decision") == "REJECT"
]


# ============================================================
# 12. RECRUITMENT SUMMARY
# ============================================================

print(
    "\n================ RECRUITMENT SUMMARY ================"
)

print(
    "Total candidates:",
    len(ranked_results)
)

print(
    "Shortlisted:",
    len(shortlisted_candidates)
)

print(
    "Review:",
    len(review_candidates)
)

print(
    "Rejected:",
    len(rejected_candidates)
)


# ============================================================
# 13. SHORTLISTED CANDIDATES
# ============================================================

print(
    "\n================ SHORTLISTED CANDIDATES ================"
)

for candidate in shortlisted_candidates:

    candidate_name = (
        candidate.get("candidate_name")
        or candidate.get("candidate_id")
        or "Unknown"
    )

    candidate_id = (
        candidate.get("candidate_id")
        or "UNKNOWN"
    )

    print(
        f"Rank {candidate.get('rank', '-')}"
        f" | {candidate_name}"
        f" | ID: {candidate_id}"
        f" | {get_candidate_score(candidate):.2f}"
    )


# ============================================================
# 14. REVIEW CANDIDATES
# ============================================================

print(
    "\n================ REVIEW CANDIDATES ================"
)

for candidate in review_candidates:

    candidate_name = (
        candidate.get("candidate_name")
        or candidate.get("candidate_id")
        or "Unknown"
    )

    candidate_id = (
        candidate.get("candidate_id")
        or "UNKNOWN"
    )

    print(
        f"Rank {candidate.get('rank', '-')}"
        f" | {candidate_name}"
        f" | ID: {candidate_id}"
        f" | {get_candidate_score(candidate):.2f}"
    )


# ============================================================
# 15. RECRUITER-FRIENDLY OUTPUT
# ============================================================

recruiter_results = (
    generate_recruiter_output(
        top_candidates
    )
)

print(
    "\n================ RECRUITER-FRIENDLY OUTPUT ================"
)

for candidate in recruiter_results:

    candidate_name = (
        candidate.get("candidate_name")
        or candidate.get("candidate_id")
        or "Unknown"
    )

    candidate_id = (
        candidate.get("candidate_id")
        or "UNKNOWN"
    )

    print("\n" + "=" * 60)

    print(
        f"Rank: "
        f"{candidate.get('rank', '-')}"
    )

    print(
        f"Candidate: "
        f"{candidate_name}"
    )

    print(
        f"Candidate ID: "
        f"{candidate_id}"
    )

    print(
        f"ATS Score: "
        f"{candidate.get('overall_score', 0.0)}"
    )

    print(
        f"Decision: "
        f"{candidate.get('decision', 'UNKNOWN')}"
    )

    # Score Breakdown
    print("\nScore Breakdown:")

    breakdown = candidate.get(
        "score_breakdown",
        {}
    )

    print(
        f"  Skill:       "
        f"{breakdown.get('skill', 0.0)}"
    )

    print(
        f"  Experience:  "
        f"{breakdown.get('experience', 0.0)}"
    )

    print(
        f"  Education:   "
        f"{breakdown.get('education', 0.0)}"
    )

    print(
        f"  Semantic:    "
        f"{breakdown.get('semantic', 0.0)}"
    )

    # Required Skills
    skill_match = candidate.get(
        "required_skill_match",
        {}
    )

    print("\nRequired Skills:")

    print(
        f"  Matched: "
        f"{skill_match.get('matched', 0)}/"
        f"{skill_match.get('total', 0)}"
    )

    print(
        f"  Match: "
        f"{skill_match.get('percentage', 0)}%"
    )

    matched_skills = skill_match.get(
        "matched_skills",
        []
    )

    if matched_skills:
        print(
            "  Matched Skills: "
            + ", ".join(matched_skills)
        )

    missing_skills = skill_match.get(
        "missing_skills",
        []
    )

    if missing_skills:
        print(
            "  Missing Skills: "
            + ", ".join(missing_skills)
        )

    # Experience
    experience = candidate.get(
        "experience",
        {}
    )

    print("\nExperience:")

    print(
        f"  Years: "
        f"{experience.get('years', 0)}"
    )

    print(
        f"  Role Relevance: "
        f"{experience.get('role_relevance', 0)}%"
    )

    print(
        f"  Technology Relevance: "
        f"{experience.get('technology_relevance', 0)}%"
    )

    # Strengths
    print("\nStrengths:")

    for strength in candidate.get(
        "strengths",
        []
    ):
        print(
            f"  + {strength}"
        )

    # Gaps
    print("\nGaps:")

    for gap in candidate.get(
        "gaps",
        []
    ):
        print(
            f"  - {gap}"
        )


# ============================================================
# 16. PIPELINE COMPLETED
# ============================================================

print(
    "\n============================================================"
)

print(
    "              RECRUITMENT PIPELINE COMPLETED"
)

print(
    "============================================================"
)