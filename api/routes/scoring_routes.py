from fastapi import APIRouter

from api.service.scoring_service import score_candidate


router = APIRouter(
    prefix="/scoring",
    tags=["Scoring"],
)


@router.post("/{candidate_id}")
def score_candidate_api(
    candidate_id: str,
):
    return score_candidate(candidate_id)