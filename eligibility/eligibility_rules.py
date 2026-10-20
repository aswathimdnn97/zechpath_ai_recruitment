
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class ExperienceRule(BaseModel):
    minimum_years: float | None = None
    maximum_years: float | None = None
    description: str | None = None

    @model_validator(mode="after")
    def validate_experience_range(self):
        if (
            self.minimum_years is not None
            and self.minimum_years < 0
        ):
            raise ValueError(
                "Minimum experience cannot be negative."
            )

        if (
            self.maximum_years is not None
            and self.maximum_years < 0
        ):
            raise ValueError(
                "Maximum experience cannot be negative."
            )

        if (
            self.minimum_years is not None
            and self.maximum_years is not None
            and self.minimum_years > self.maximum_years
        ):
            raise ValueError(
                "Minimum experience cannot exceed maximum experience."
            )

        return self


class EducationRule(BaseModel):
    description: str
    enforcement: Literal[
        "mandatory",
        "preferred",
        "unspecified",
    ] = "unspecified"


class ScoreCutoffRule(BaseModel):
    minimum_ats_score: float = Field(
        default=70.0,
        ge=0,
        le=100,
    )

    review_score_threshold: float = Field(
        default=60.0,
        ge=0,
        le=100,
    )

    @model_validator(mode="after")
    def validate_cutoffs(self):
        if self.review_score_threshold > self.minimum_ats_score:
            raise ValueError(
                "Review score threshold cannot exceed "
                "the minimum ATS score."
            )

        return self


class LocationRule(BaseModel):
    allowed_locations: list[str] = Field(
        default_factory=list
    )

    remote_allowed: bool | None = None

    enforcement: Literal[
        "mandatory",
        "preferred",
        "unspecified",
    ] = "unspecified"


class AvailabilityRule(BaseModel):
    maximum_notice_period_days: int | None = Field(
        default=None,
        ge=0,
    )

    available_from: str | None = None

    enforcement: Literal[
        "mandatory",
        "preferred",
        "unspecified",
    ] = "unspecified"


class EligibilityRuleSet(BaseModel):
    job_id: str | None = None
    jd_id: str | None = None
    role_category: str | None = None

    rule_version: str = "1.0"

    # Skill requirements
    required_skills: list[str] = Field(
        default_factory=list
    )

    preferred_skills: list[str] = Field(
        default_factory=list
    )

    mandatory_skills: list[str] = Field(
        default_factory=list
    )

    # Score-based eligibility
    cutoffs: ScoreCutoffRule = Field(
        default_factory=ScoreCutoffRule
    )

    # Experience requirements
    experience: ExperienceRule = Field(
        default_factory=ExperienceRule
    )

    # Education requirements
    education: list[EducationRule] = Field(
        default_factory=list
    )

    # Location and availability constraints
    location: LocationRule = Field(
        default_factory=LocationRule
    )

    availability: AvailabilityRule = Field(
        default_factory=AvailabilityRule
    )

    # Other requirements from the JD
    requirements: list[str] = Field(
        default_factory=list
    )

    generation_status: Literal[
        "generated",
        "failed",
    ] = "generated"



class LocationRule(BaseModel):
    job_location: str | None = None
    allowed_locations: list[str] = Field(default_factory=list)
    remote_allowed: bool | None = None
    enforcement: Literal[
        "mandatory", "preferred", "unspecified"
    ] = "unspecified"

