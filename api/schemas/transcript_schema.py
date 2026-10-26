
"""
transcript_schema.py

Responsibilities
----------------
1. Validate voice transcript metadata.
2. Define timestamped transcript segments.
3. Validate transcription confidence.
4. Track processing and recruiter review status.
5. Preserve original text separately from normalized text.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class TranscriptStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class TranscriptReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    CORRECTED = "CORRECTED"


class TranscriptSource(str, Enum):
    VOICE = "VOICE"


class TranscriptSegment(BaseModel):
    """One timestamped portion of a transcript."""

    model_config = ConfigDict(extra="forbid")

    start_ms: int = Field(ge=0)
    end_ms: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=10000)
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0
    )

    @model_validator(mode="after")
    def validate_timestamps(self):
        if self.end_ms <= self.start_ms:
            raise ValueError(
                "end_ms must be greater than start_ms"
            )
        return self


class TranscriptMetadata(BaseModel):
    """Speech-to-text provider metadata."""

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(min_length=1, max_length=100)
    model_version: str | None = Field(
        default=None, max_length=100
    )
    confidence: float | None = Field(
        default=None, ge=0.0, le=1.0
    )


class TranscriptTiming(BaseModel):
    """Recording and transcription timestamps."""

    model_config = ConfigDict(extra="forbid")

    recorded_at: datetime | None = None
    transcribed_at: datetime | None = None
    duration_ms: int | None = Field(default=None, ge=0)

    @field_validator("recorded_at", "transcribed_at")
    @classmethod
    def require_timezone(cls, value):
        if value is not None and (
            value.tzinfo is None or value.utcoffset() is None
        ):
            raise ValueError(
                "Timestamps must include a timezone"
            )
        return value


class TranscriptNormalization(BaseModel):
    """Records how the transcript was normalized."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="1.0", max_length=20)
    language_preserved: bool = True
    pii_redacted: bool = False


class TranscriptReview(BaseModel):
    """Recruiter review metadata."""

    model_config = ConfigDict(extra="forbid")

    status: TranscriptReviewStatus = (
        TranscriptReviewStatus.PENDING
    )
    corrected_text: str | None = Field(
        default=None, max_length=50000
    )
    reviewer_id: str | None = Field(
        default=None, max_length=100
    )
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_review(self):
        if self.status == TranscriptReviewStatus.CORRECTED:
            if not self.corrected_text or not self.reviewer_id:
                raise ValueError(
                    "Corrected text and reviewer_id are required "
                    "for CORRECTED status"
                )
            if self.reviewed_at is None:
                raise ValueError(
                    "reviewed_at is required for CORRECTED status"
                )

        if self.reviewed_at is not None:
            if (
                self.reviewed_at.tzinfo is None
                or self.reviewed_at.utcoffset() is None
            ):
                raise ValueError(
                    "reviewed_at must include a timezone"
                )

        return self


class TranscriptCreate(BaseModel):
    """Input for creating a transcript."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(
        min_length=1, max_length=40
    )
    candidate_id: str = Field(
        min_length=1, max_length=40
    )
    job_id: str = Field(
        min_length=1, max_length=40
    )
    question_id: str = Field(
        min_length=1, max_length=100
    )

    source: TranscriptSource = TranscriptSource.VOICE
    language: Literal["en", "ml", "hi"]

    original_text: str = Field(
        min_length=1, max_length=50000
    )
    normalized_text: str | None = Field(
        default=None, max_length=50000
    )

    segments: list[TranscriptSegment] = Field(
        default_factory=list, max_length=1000
    )
    transcription: TranscriptMetadata
    timing: TranscriptTiming = Field(
        default_factory=TranscriptTiming
    )
    normalization: TranscriptNormalization = Field(
        default_factory=TranscriptNormalization
    )

    @field_validator("original_text", "normalized_text")
    @classmethod
    def reject_blank_text(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Transcript text cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_segment_order(self):
        previous_end = 0

        for segment in self.segments:
            if segment.start_ms < previous_end:
                raise ValueError(
                    "Transcript segments must be ordered "
                    "and must not overlap"
                )
            previous_end = segment.end_ms

        duration = self.timing.duration_ms
        if duration is not None and previous_end > duration:
            raise ValueError(
                "Segment timestamps cannot exceed duration_ms"
            )

        return self


class TranscriptRecord(TranscriptCreate):
    """Complete stored transcript record."""

    transcript_id: str = Field(
        min_length=1, max_length=40
    )
    status: TranscriptStatus = TranscriptStatus.PENDING
    review: TranscriptReview = Field(
        default_factory=TranscriptReview
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

