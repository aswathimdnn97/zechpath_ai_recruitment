from typing import Any
from pydantic import BaseModel, Field, ConfigDict


class IntentSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str
    confidence: float = Field(ge=0, le=1)
    classification_method: str


class ExperienceEntity(BaseModel):
    years: float | None = None
    role: str | None = None
    company: str | None = None
    projects: list[str] = Field(default_factory=list)


class AvailabilityEntity(BaseModel):
    status: str | None = None
    notice_period: dict[str, Any] | None = None
    joining_date: str | None = None


class SalaryEntity(BaseModel):
    minimum: float | None = None
    maximum: float | None = None
    currency: str | None = None
    period: str | None = None


class SemanticEntities(BaseModel):
    skills: list[str] = Field(default_factory=list)
    experience: ExperienceEntity
    availability: AvailabilityEntity
    salary_expectation: SalaryEntity


class AnswerQuality(BaseModel):
    is_off_topic: bool = False
    is_missing: bool = False
    is_vague: bool = False
    review_required: bool = False
    issues: list[str] = Field(default_factory=list)


class SemanticAnswer(BaseModel):
    question_id: str | None = None
    intent: IntentSchema
    entities: SemanticEntities
    quality: AnswerQuality
    metadata: dict[str, Any]