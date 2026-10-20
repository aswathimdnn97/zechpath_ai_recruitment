
"""
hr_screening_schema.py

Pydantic schemas for ZechPath HR screening.

Responsibilities
-----------------
1. Validate screening session creation requests.
2. Validate candidate answers.
3. Represent screening session status.
4. Validate evaluation results.
5. Standardize API response structures.

Business logic belongs in service modules.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)


# ============================================================
# COMMON TYPES
# ============================================================

NonEmptyString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=200,
    ),
]

AnswerText = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=10_000,
    ),
]


class ScreeningSchema(BaseModel):
    """Common configuration for screening API models."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


# ============================================================
# ENUMS
# ============================================================

class ScreeningSessionStatus(str, Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    EVALUATED = "EVALUATED"
    CANCELLED = "CANCELLED"


class ScreeningEvaluationStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class AnswerType(str, Enum):
    TEXT = "TEXT"
    SINGLE_CHOICE = "SINGLE_CHOICE"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    BOOLEAN = "BOOLEAN"

    # Dataset answer types
    YES_NO_WITH_DETAILS = "YES_NO_WITH_DETAILS"
    MULTI_SELECT_WITH_DETAILS = "MULTI_SELECT_WITH_DETAILS"
    CURRENCY_RANGE = "CURRENCY_RANGE"
    DATE_OR_DURATION = "DATE_OR_DURATION"



# ============================================================
# SESSION REQUEST
# ============================================================

class ScreeningSessionCreateRequest(ScreeningSchema):
    """Request to create a screening session."""

    candidate_id: NonEmptyString
    job_id: NonEmptyString
    role_id: NonEmptyString

    language: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=2,
            max_length=10,
            pattern=r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
        ),
    ] = "en"

    categories: list[NonEmptyString] | None = None
    include_optional: bool = True

    @field_validator("categories")
    @classmethod
    def validate_categories(
        cls,
        categories: list[str] | None,
    ) -> list[str] | None:
        if categories is None:
            return None

        normalized = [category.upper() for category in categories]

        if len(normalized) != len(set(normalized)):
            raise ValueError("Duplicate screening categories are not allowed.")

        return normalized


# ============================================================
# CANDIDATE ANSWERS
# ============================================================

### 1. Replace `ScreeningAnswerSubmission`

class ScreeningAnswerSubmission(ScreeningSchema):
    """One candidate response, including supported structured fields."""

    question_id: NonEmptyString

    # Text answers and yes/no values ("yes" or "no").
    answer: AnswerText | None = None

    # Selectable answers.
    selected_options: list[NonEmptyString] | None = None

    # Additional context for answers that support details.
    details: Annotated[str, StringConstraints(max_length=10_000)] | None = None

    # Structured salary range.
    currency: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=3, max_length=3),
    ] | None = None
    minimum_amount: float | None = Field(default=None, ge=0)
    maximum_amount: float | None = Field(default=None, ge=0)

    # Joining availability.
    joining_date: datetime | None = None
    duration: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    ] | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @model_validator(mode="after")
    def validate_answer_content(self):
        has_text = self.answer is not None and bool(self.answer.strip())
        has_options = bool(self.selected_options)

        if self.selected_options is not None:
            if len(set(self.selected_options)) != len(self.selected_options):
                raise ValueError("Duplicate selected options are not allowed.")

        # Do not accept an empty answer object.
        has_salary = any(
            value is not None
            for value in (
                self.currency,
                self.minimum_amount,
                self.maximum_amount,
            )
        )
        has_joining_info = (
            self.joining_date is not None
            or self.duration is not None
        )
        has_details = self.details is not None and bool(self.details.strip())

        if not any((
            has_text,
            has_options,
            has_salary,
            has_joining_info,
            has_details,
        )):
            raise ValueError("Provide a meaningful answer.")

        if (
            self.minimum_amount is not None
            and self.maximum_amount is not None
            and self.maximum_amount < self.minimum_amount
        ):
            raise ValueError(
                "maximum_amount cannot be less than minimum_amount."
            )

        return self
    
### 2. Replace `ScreeningResponseSubmissionRequest`

class ScreeningResponseSubmissionRequest(ScreeningSchema):
    """Submit answers for an existing screening session."""

    answers: Annotated[
        list[ScreeningAnswerSubmission],
        Field(min_length=1, max_length=200),
    ]

    final_submission: bool = False

    @model_validator(mode="after")
    def validate_unique_question_ids(self):
        question_ids = [
            item.question_id.casefold()
            for item in self.answers
        ]

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                "Each question can appear only once per submission."
            )

        return self


# ============================================================
# ANSWER RESPONSE
# ============================================================

class ScreeningAnswerResponse(ScreeningSchema):
    """Candidate-safe representation of a saved answer."""

    question_id: NonEmptyString
    answered: bool
    updated_at: datetime | None = None


# ============================================================
# SESSION RESPONSE
# ============================================================

class ScreeningSessionResponse(ScreeningSchema):
    """Public representation of a screening session."""

    session_id: NonEmptyString
    candidate_id: NonEmptyString
    job_id: NonEmptyString
    role_id: NonEmptyString

    language: str = "en"
    status: ScreeningSessionStatus

    total_questions: int = Field(default=0, ge=0)
    mandatory_questions: int = Field(default=0, ge=0)
    answered_questions: int = Field(default=0, ge=0)
    answered_mandatory_questions: int = Field(default=0, ge=0)

    created_at: datetime
    updated_at: datetime | None = None
    submitted_at: datetime | None = None

    @model_validator(mode="after")
    def validate_question_counts(self):
        if self.answered_questions > self.total_questions:
            raise ValueError(
                "Answered questions cannot exceed total questions."
            )

        if self.mandatory_questions > self.total_questions:
            raise ValueError(
                "Mandatory questions cannot exceed total questions."
            )

        if (
            self.answered_mandatory_questions
            > self.mandatory_questions
        ):
            raise ValueError(
                "Answered mandatory questions cannot exceed "
                "mandatory questions."
            )

        return self


# ============================================================
# EVALUATION RESULT
# ============================================================

class ScreeningEvaluationResult(ScreeningSchema):
    """Candidate screening evaluation summary."""

    session_id: NonEmptyString
    candidate_id: NonEmptyString
    job_id: NonEmptyString

    status: ScreeningEvaluationStatus

    total_questions: int = Field(ge=0)
    answered_questions: int = Field(ge=0)
    mandatory_questions: int = Field(ge=0)
    unanswered_mandatory_questions: list[NonEmptyString] = Field(
        default_factory=list
    )

    score: float | None = Field(default=None, ge=0, le=100)

    # Keep the evaluation explanation auditable.
    summary: str | None = Field(default=None, max_length=2000)

    evaluated_at: datetime | None = None

    @model_validator(mode="after")
    def validate_evaluation_counts(self):
        if self.answered_questions > self.total_questions:
            raise ValueError(
                "Answered questions cannot exceed total questions."
            )

        if self.mandatory_questions > self.total_questions:
            raise ValueError(
                "Mandatory questions cannot exceed total questions."
            )

        if self.status == ScreeningEvaluationStatus.COMPLETED:
            if self.unanswered_mandatory_questions:
                raise ValueError(
                    "A completed evaluation cannot have unanswered "
                    "mandatory questions."
                )

            if self.evaluated_at is None:
                raise ValueError(
                    "Completed evaluations require evaluated_at."
                )

        return self


# ============================================================
# STANDARD API RESPONSE
# ============================================================

class ScreeningMessageResponse(ScreeningSchema):
    """Standard response for successful screening operations."""

    success: bool = True
    message: NonEmptyString


class ScreeningErrorResponse(ScreeningSchema):
    """Safe API error response."""

    success: bool = False
    detail: NonEmptyString



# ============================================================
# RECRUITER REVIEW REQUEST
# ============================================================

class RecruiterQuestionReviewRequest(ScreeningSchema):
    """Recruiter score and feedback for one screening answer."""

    question_id: NonEmptyString
    reviewer_id: NonEmptyString

    score: float = Field(ge=0, allow_inf_nan=False)
    max_score: float = Field(gt=0, allow_inf_nan=False)

    feedback: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
    ]

    @model_validator(mode="after")
    def validate_score_range(self):
        if self.score > self.max_score:
            raise ValueError(
                "score cannot exceed max_score."
            )
        return self
