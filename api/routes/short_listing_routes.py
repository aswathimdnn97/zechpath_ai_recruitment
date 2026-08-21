from fastapi import APIRouter, Query

from api.service.shortlisting_service import (
    shortlist_all_candidates,
)


router = APIRouter(
    prefix="/shortlisting",
    tags=["Shortlisting"],
)


@router.post("")
def shortlist_candidates_api(
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
    """
    Shortlist candidates based on
    their ATS scores.
    """

    return shortlist_all_candidates(
        shortlist_threshold=shortlist_threshold,
        review_threshold=review_threshold,
    )