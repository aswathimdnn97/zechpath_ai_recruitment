from utils.logger import logger
from document_processing.resume.resume_pipeline import resume_pipeline
from document_processing.job_description.job_description_pipeline import job_description_pipeline
from pipelines.recruiter_pipeline import recruitment_pipeline
from matching.matcher import Matcher
from scoring.ats_scoring_engine import calculate_ats_score
from embeddings.embedding_generator import EmbeddingGenerator
from scoring.ranking.ranking_pipeline import rank_and_shortlist
from scoring.ranking.top_candidates import get_top_candidates
from scoring.ranking.recruiters_output import generate_recruiter_output
from pathlib import Path

logger.info("Resume Uploaded")

RESUME_FOLDER = Path("data/resume/pdf")

JOB_DESCRIPTION_FILE = (
    "data/job_descriptions/jd_python_developer.pdf"
)

TOP_N = 5

SHORTLIST_THRESHOLD = 80.0
REVIEW_THRESHOLD = 60.0


logger.info("Recruitment pipeline started")


# ============================================================
# 1. Job Description Parsing
# ============================================================

print("\n================ JOB DESCRIPTION PARSING ================")

jd_json = job_description_pipeline(
    JOB_DESCRIPTION_FILE
)

print("\n================ JD JSON ================")
print(jd_json)


# ============================================================
# 2. Initialize Matching / Embedding
# ============================================================

matcher = Matcher()

embedding_generator = EmbeddingGenerator()


# ============================================================
# 3. Process Multiple Resumes
# ============================================================

resume_files = sorted(
    RESUME_FOLDER.glob("*.pdf")
)

print(
    f"\nFound {len(resume_files)} resume(s)"
)


if not resume_files:

    print(
        f"No PDF resumes found in {RESUME_FOLDER}"
    )

    raise SystemExit(1)


# This list will contain the ATS result
# of EVERY candidate.
ats_results = []


# ============================================================
# 4. Process Each Candidate
# ============================================================

for resume_file in resume_files:

    print("\n")
    print("=" * 70)
    print(
        f"PROCESSING RESUME: {resume_file.name}"
    )
    print("=" * 70)

    try:

        # ----------------------------------------------------
        # Resume Parsing
        # ----------------------------------------------------

        logger.info(
            f"Resume uploaded: {resume_file.name}"
        )

        resume_json = resume_pipeline(
            str(resume_file)
        )

        print(
            "\n================ RESUME JSON ================"
        )

        print(resume_json)


        # ----------------------------------------------------
        # Existing Matching
        # ----------------------------------------------------

        matching_result = matcher.match(
            resume_json,
            jd_json
        )

        print(
            "\n================ MATCHING RESULT ================"
        )

        print(matching_result)


        # ----------------------------------------------------
        # Generate Embeddings
        # ----------------------------------------------------

        resume_embedding = (
            embedding_generator.generate_embedding(
                resume_json
            )
        )

        jd_embedding = (
            embedding_generator.generate_embedding(
                jd_json
            )
        )


        # ----------------------------------------------------
        # ATS Scoring
        # ----------------------------------------------------

        ats_result = calculate_ats_score(
            candidate_profile=resume_json,
            jd_profile=jd_json,
            resume_embedding=resume_embedding,
            jd_embedding=jd_embedding
        )


        # ----------------------------------------------------
        # Add Candidate Information
        # ----------------------------------------------------

        ats_result["candidate_id"] = resume_file.stem

        ats_result["candidate_name"] = (
            resume_json
            .get("personal_information", {})
            .get("name")
            or resume_file.stem
        )


        # ----------------------------------------------------
        # Display ATS Result
        # ----------------------------------------------------

        print(
            "\n================ ATS SCORE ================"
        )

        final_score = (
            ats_result
            ["candidate_score"]
            ["final_score"]
        )

        print(
            "Candidate:",
            ats_result["candidate_name"]
        )

        print(
            "Final ATS Score:",
            final_score
        )

        print("\nComponent Scores:")

        print(
            "Skill:",
            ats_result
            ["component_scores"]
            ["skill"]
            ["score"]
        )

        print(
            "Experience:",
            ats_result
            ["component_scores"]
            ["experience"]
            ["score"]
        )

        print(
            "Education:",
            ats_result
            ["component_scores"]
            ["education"]
            ["score"]
        )

        print(
            "Semantic:",
            ats_result
            ["component_scores"]
            ["semantic"]
            ["score"]
        )


        # ----------------------------------------------------
        # Store Result
        # ----------------------------------------------------
        #
        # IMPORTANT:
        # We DON'T rank here.
        #
        # First we score ALL candidates.
        #

        ats_results.append(
            ats_result
        )


        print(
            "\nCandidate scoring completed."
        )


    except Exception as error:

        logger.exception(
            f"Error processing {resume_file.name}"
        )

        print(
            f"\nERROR processing "
            f"{resume_file.name}: {error}"
        )

        continue


# ============================================================
# 5. Check ATS Results
# ============================================================

print(
    "\n================ SCORING ENGINE ================"
)

print(
    f"Successfully scored candidates: "
    f"{len(ats_results)}"
)


if not ats_results:

    print(
        "No candidates were successfully scored."
    )

    raise SystemExit(1)


# ============================================================
# 6. Ranking + Shortlisting
# ============================================================
#
# IMPORTANT:
#
# This is where ALL candidates are passed together.
#
# ============================================================

print(
    "\n================ RANKING & SHORTLISTING ================"
)

ranked_results = rank_and_shortlist(
    ats_results,
    shortlist_threshold=SHORTLIST_THRESHOLD,
    review_threshold=REVIEW_THRESHOLD
)


# ============================================================
# 7. Display Complete Ranking
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

print("-" * 75)


for candidate in ranked_results:

    rank = candidate.get(
        "rank",
        "-"
    )

    candidate_name = candidate.get(
        "candidate_name",
        candidate.get(
            "candidate_id",
            "Unknown"
        )
    )

    score = (
        candidate
        .get("candidate_score", {})
        .get("final_score", 0.0)
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
# 8. Generate Top Candidates
# ============================================================

top_candidates = get_top_candidates(
    ranked_results,
    top_n=TOP_N
)


# ============================================================
# 9. Display Top Candidates
# ============================================================

print(
    f"\n================ TOP {TOP_N} CANDIDATES ================"
)


for candidate in top_candidates:

    rank = candidate.get(
        "rank",
        "-"
    )

    candidate_name = candidate.get(
        "candidate_name",
        candidate.get(
            "candidate_id",
            "Unknown"
        )
    )

    score = (
        candidate
        .get("candidate_score", {})
        .get("final_score", 0.0)
    )

    decision = candidate.get(
        "decision",
        "UNKNOWN"
    )

    print(
        f"Rank {rank} | "
        f"{candidate_name} | "
        f"Score: {score:.2f} | "
        f"{decision}"
    )


# ============================================================
# 10. Separate Candidate Zones
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
# 11. Recruitment Summary
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
# 12. Shortlisted Candidates
# ============================================================

print(
    "\n================ SHORTLISTED CANDIDATES ================"
)

for candidate in shortlisted_candidates:

    score = (
        candidate
        .get("candidate_score", {})
        .get("final_score", 0.0)
    )

    print(
        f"Rank {candidate['rank']} | "
        f"{candidate.get('candidate_name')} | "
        f"{score:.2f}"
    )


# ============================================================
# 13. Review Candidates
# ============================================================

print(
    "\n================ REVIEW CANDIDATES ================"
)

for candidate in review_candidates:

    score = (
        candidate
        .get("candidate_score", {})
        .get("final_score", 0.0)
    )

    print(
        f"Rank {candidate['rank']} | "
        f"{candidate.get('candidate_name')} | "
        f"{score:.2f}"
    )


# ============================================================
# 14. Final Output
# ============================================================
recruiter_results = generate_recruiter_output(
    top_candidates
)
print(
    "\n================ RECRUITER-FRIENDLY OUTPUT ================"
)

for candidate in recruiter_results:

    print("\n" + "=" * 60)

    print(
        f"Rank: {candidate['rank']}"
    )

    print(
        f"Candidate: {candidate['candidate_name']}"
    )

    print(
        f"ATS Score: {candidate['overall_score']}"
    )

    print(
        f"Decision: {candidate['decision']}"
    )

    print("\nScore Breakdown:")

    breakdown = candidate[
        "score_breakdown"
    ]

    print(
        f"  Skill:       {breakdown['skill']}"
    )

    print(
        f"  Experience:  {breakdown['experience']}"
    )

    print(
        f"  Education:   {breakdown['education']}"
    )

    print(
        f"  Semantic:    {breakdown['semantic']}"
    )

    skill_match = candidate[
        "required_skill_match"
    ]

    print("\nRequired Skills:")

    print(
        f"  Matched: "
        f"{skill_match['matched']}/"
        f"{skill_match['total']}"
    )

    print(
        f"  Match: "
        f"{skill_match['percentage']}%"
    )

    if skill_match["matched_skills"]:

        print(
            "  Matched Skills: "
            + ", ".join(
                skill_match["matched_skills"]
            )
        )

    if skill_match["missing_skills"]:

        print(
            "  Missing Skills: "
            + ", ".join(
                skill_match["missing_skills"]
            )
        )

    experience = candidate[
        "experience"
    ]

    print("\nExperience:")

    print(
        f"  Years: "
        f"{experience['years']}"
    )

    print(
        f"  Role Relevance: "
        f"{experience['role_relevance']}%"
    )

    print(
        f"  Technology Relevance: "
        f"{experience['technology_relevance']}%"
    )

    print("\nStrengths:")

    for strength in candidate["strengths"]:

        print(
            f"  + {strength}"
        )

    print("\nGaps:")

    for gap in candidate["gaps"]:

        print(
            f"  - {gap}"
        )

print(
    "\n============================================================"
)

print(
    "              RECRUITMENT PIPELINE COMPLETED"
)

print(
    "============================================================"
)
