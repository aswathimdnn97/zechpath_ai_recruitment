from fastapi import APIRouter, Query

from api.service.ranking_service import (
    rank_all_candidates,
    get_candidate_ranking,
)


router = APIRouter(
    prefix="/ranking",
    tags=["Ranking"],
)


@router.get("")
def get_ranking(
    shortlist_threshold: float = Query(
        80.0,
        ge=0,
        le=100,
    ),
    review_threshold: float = Query(
        60.0,
        ge=0,
        le=100,
    ),
):
    return rank_all_candidates(
        shortlist_threshold=shortlist_threshold,
        review_threshold=review_threshold,
    )


@router.get("/{candidate_id}")
def get_candidate_rank(
    candidate_id: str,
    shortlist_threshold: float = Query(
        80.0,
        ge=0,
        le=100,
    ),
    review_threshold: float = Query(
        60.0,
        ge=0,
        le=100,
    ),
):
    return get_candidate_ranking(
        candidate_id=candidate_id,
        shortlist_threshold=shortlist_threshold,
        review_threshold=review_threshold,
    )