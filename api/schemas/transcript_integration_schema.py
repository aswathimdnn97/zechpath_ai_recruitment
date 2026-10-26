"""Request/response schemas for transcript-to-screening-response integration."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TranscriptResponseLinkRequest(BaseModel):
    """Authorize linking a transcript to its candidate's screening answer."""

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1, max_length=40)
    replace_existing: bool = False


class TranscriptReviewUpdate(BaseModel):
    """Recruiter decision for a processed transcript."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["APPROVED", "CORRECTED"]
    reviewer_id: str = Field(min_length=1, max_length=100)
    corrected_text: str | None = Field(default=None, min_length=1, max_length=50000)

    @model_validator(mode="after")
    def validate_review_fields(self):
        if not self.reviewer_id.strip():
            raise ValueError("reviewer_id cannot be blank.")
        if self.status == "CORRECTED":
            if self.corrected_text is None or not self.corrected_text.strip():
                raise ValueError("corrected_text is required for CORRECTED status.")
        elif self.corrected_text is not None:
            raise ValueError("corrected_text must only be supplied for CORRECTED status.")
        return self
