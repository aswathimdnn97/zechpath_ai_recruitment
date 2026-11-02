
"""
scoring_config_service.py

Responsibilities:
1. Load centralized scoring configuration.
2. Validate scoring dimensions and weights.
3. Ensure all weights sum to 1.0.
4. Validate score range and normalization settings.
5. Provide validated configuration to scoring services.
"""

import json
import math

from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    model_validator,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

SCORING_CONFIG_PATH = (
    PROJECT_ROOT / "api" / "config" / "screening_scoring_weights.json"
)


class ScoringConfigurationError(Exception):
    """Raised when scoring configuration is invalid."""


class DimensionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weight: float = Field(
        gt=0,
        le=1,
        allow_inf_nan=False
    )

    description: str = Field(
        min_length=1,
        max_length=500
    )


class ScoringDimensions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clarity: DimensionConfig
    relevance: DimensionConfig
    completeness: DimensionConfig
    consistency: DimensionConfig

    @model_validator(mode="after")
    def validate_total_weight(self):
        total = sum(
            dimension.weight
            for dimension in (
                self.clarity,
                self.relevance,
                self.completeness,
                self.consistency,
            )
        )

        if not math.isclose(
            total,
            1.0,
            rel_tol=0.0,
            abs_tol=1e-9
        ):
            raise ValueError(
                f"Scoring weights must sum to 1.0. "
                f"Received: {total}"
            )

        return self
    
class ScoreScale(BaseModel):
    model_config = ConfigDict(extra="forbid")

    minimum: float = Field(allow_inf_nan=False)
    maximum: float = Field(allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_range(self):
        if self.maximum <= self.minimum:
            raise ValueError(
                "Maximum score must be greater than minimum score."
            )
        return self


class NormalizationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["percentage"]
    precision: int = Field(ge=0, le=6)


class ReviewConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    flag_unanswered: bool
    flag_vague_answers: bool
    flag_off_topic_answers: bool
    flag_possible_contradictions: bool


class ScoringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scoring_version: str = Field(min_length=1)

    score_scale: ScoreScale
    dimensions: ScoringDimensions
    normalization: NormalizationConfig
    review: ReviewConfig


def load_scoring_config(
    config_path: Path | None = None
) -> ScoringConfig:
    """
    Load and validate the scoring configuration.

    Args:
        config_path: Optional custom configuration path.

    Returns:
        Validated ScoringConfig object.

    Raises:
        ScoringConfigurationError:
            If the file is missing, invalid JSON,
            or contains invalid configuration.
    """

    path = config_path or SCORING_CONFIG_PATH

    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            raise ScoringConfigurationError(
                "Scoring configuration must be a JSON object."
            )

        return ScoringConfig.model_validate(data)

    except FileNotFoundError as exc:
        raise ScoringConfigurationError(
            f"Scoring configuration not found: {path}"
        ) from exc

    except json.JSONDecodeError as exc:
        raise ScoringConfigurationError(
            "Scoring configuration contains invalid JSON."
        ) from exc

    except ValidationError as exc:
        raise ScoringConfigurationError(
            f"Invalid scoring configuration: {exc}"
        ) from exc

    except OSError as exc:
        raise ScoringConfigurationError(
            "Unable to read scoring configuration."
        ) from exc
