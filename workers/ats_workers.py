from api.service.scoring_service import score_candidate

from api.service.job_service import (
    mark_task_processing,
    mark_task_completed,
    mark_task_failed,
)


def run_scoring_job(
    task_id: str,
    candidate_id: str,
    jd_id: str,
    recruitment_job_id: str,
):
    """
    Execute candidate scoring as an asynchronous task.

    task_id:
        Unique ID for this scoring execution.

    recruitment_job_id:
        Persistent recruitment/job ID shared by all candidates
        being evaluated against the same recruitment job.
    """

    print(
        f"[WORKER] Starting task "
        f"{task_id} "
        f"for candidate={candidate_id} "
        f"jd={jd_id} "
        f"recruitment_job_id={recruitment_job_id}"
    )

    try:

        # --------------------------------------------
        # PROCESSING
        # --------------------------------------------

        processing_task = mark_task_processing(
            task_id,
            progress=10,
        )

        print(
            f"[WORKER] Task marked PROCESSING: "
            f"{processing_task}"
        )

        # --------------------------------------------
        # SCORING
        # --------------------------------------------

        print(
            f"[WORKER] Calling score_candidate("
            f"candidate_id={candidate_id}, "
            f"jd_id={jd_id}, "
            f"job_id={recruitment_job_id})"
        )

        result = score_candidate(
            candidate_id=candidate_id,
            jd_id=jd_id,
            job_id=recruitment_job_id,
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
            f"{recruitment_job_id}/"
            f"{candidate_id}.json"
        )

        completed_task = mark_task_completed(
            task_id,
            result_reference=result_reference,
        )

        print(
            f"[WORKER] Task marked COMPLETED: "
            f"{completed_task}"
        )

    except Exception as exc:

        print(
            f"[WORKER] Task FAILED: "
            f"{task_id} | {exc}"
        )

        failed_task = mark_task_failed(
            task_id,
            error_code="SCORING_FAILED",
            message=str(exc),
        )

        print(
            f"[WORKER] Failed task record: "
            f"{failed_task}"
        )