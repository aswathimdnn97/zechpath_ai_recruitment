
from typing import Literal

from pydantic import BaseModel, Field, ConfigDict


class RecruiterDecisionRequest(BaseModel):
    """Request body for a session-level recruiter decision."""

    model_config = ConfigDict(extra="forbid")

    reviewer_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="ID of the recruiter making the decision.",
    )

    decision: Literal[
        "SHORTLIST",
        "REJECT",
        "HOLD",
        "NEEDS_FURTHER_REVIEW",
    ] = Field(
        ...,
        description="Recruiter's final decision for the screening session.",
    )

    comments: str | None = Field(
        default=None,
        max_length=5000,
        description="Optional comments explaining the decision.",
    )
