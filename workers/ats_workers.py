from api.service.scoring_service import score_candidate

from api.service.job_service import (
    mark_job_processing,
    mark_job_completed,
    mark_job_failed,
)


def run_scoring_job(
    job_id: str,
    candidate_id: str,
    jd_id: str,
):

    print(
        f"[WORKER] Starting job "
        f"{job_id} "
        f"for candidate={candidate_id} "
        f"jd={jd_id}"
    )

    try:

        # --------------------------------------------
        # PROCESSING
        # --------------------------------------------

        processing_job = mark_job_processing(
            job_id,
            progress=10,
        )

        print(
            f"[WORKER] Job marked PROCESSING: "
            f"{processing_job}"
        )

        # --------------------------------------------
        # SCORING
        # --------------------------------------------

        print(
            f"[WORKER] Calling "
            f"score_candidate("
            f"candidate_id={candidate_id}, "
            f"jd_id={jd_id})"
        )

        result = score_candidate(
            candidate_id=candidate_id,
            jd_id=jd_id,
        )

        print(
            f"[WORKER] Scoring completed: "
            f"{result}"
        )

        # --------------------------------------------
        # COMPLETED
        # --------------------------------------------

        result_reference = (
            f"data/candidates/"
            f"scoring_results/"
            f"{candidate_id}/"
            f"{jd_id}.json"
        )

        completed_job = mark_job_completed(
            job_id,
            result_reference=result_reference,
        )

        print(
            f"[WORKER] Job marked COMPLETED: "
            f"{completed_job}"
        )

    except Exception as exc:

        print(
            f"[WORKER] Job FAILED: "
            f"{job_id} | {exc}"
        )

        failed_job = mark_job_failed(
            job_id,
            error_code="SCORING_FAILED",
            message=str(exc),
        )

        print(
            f"[WORKER] Failed job record: "
            f"{failed_job}"
        )