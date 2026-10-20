
# eligibility/eligibility_rule_generator.py

import json
from pathlib import Path
from typing import Any
import math
from eligibility.eligibility_rules import EligibilityRuleSet
import logging

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[1]
ROLE_POLICIES_PATH = (
    BASE_DIR / "data" / "eligibility_rules" / "role_policies.json"
)


def _normalize_skills(value: Any) -> list[str]:
    """Normalize skill names and remove case-insensitive duplicates."""
    if isinstance(value, str):
        value = [value]

    if not isinstance(value, (list, tuple, set)):
        return []

    skills = []
    seen = set()

    for item in value:
        if not isinstance(item, str):
            continue

        skill = item.strip()
        normalized = skill.casefold()

        if skill and normalized not in seen:
            skills.append(skill)
            seen.add(normalized)

    return skills


def _normalize_education(value: Any) -> list[dict[str, str]]:
    """Normalize education requirements."""
    if isinstance(value, (str, dict)):
        value = [value]

    if not isinstance(value, list):
        return []

    education_rules = []

    for item in value:
        if isinstance(item, str):
            description = item.strip()
            enforcement = (
                "preferred"
                if "preferred" in description.casefold()
                else "unspecified"
            )

        elif isinstance(item, dict):
            description = str(
                item.get("description")
                or item.get("degree")
                or item.get("qualification")
                or ""
            ).strip()

            explicit_enforcement = str(
                item.get("enforcement") or ""
            ).strip().casefold()

            if explicit_enforcement in {
                "mandatory",
                "preferred",
                "unspecified",
            }:
                enforcement = explicit_enforcement
            elif "preferred" in description.casefold():
                enforcement = "preferred"
            else:
                enforcement = "unspecified"

        else:
            continue

        if description:
            education_rules.append({
                "description": description,
                "enforcement": enforcement,
            })

    return education_rules


def _load_role_policies(
    policies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Load role policies, allowing explicit policies to be injected in tests."""
    if policies is not None:
        return policies

    if not ROLE_POLICIES_PATH.exists():
        return {}

    with ROLE_POLICIES_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("Role policies configuration must be a JSON object.")

    return data


def _validate_role_policy(
    policy_key: str,
    policy: Any,
) -> dict[str, Any]:
    """Validate the selected role policy and its ATS score cutoffs."""
    if not isinstance(policy, dict):
        raise ValueError(
            f"Role policy '{policy_key}' must be a JSON object."
        )

    validated_policy = dict(policy)

    minimum_score = validated_policy.get("minimum_ats_score", 70.0)
    review_threshold = validated_policy.get(
        "review_score_threshold", 60.0
    )

    def validate_cutoff(name: str, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"Role policy '{policy_key}': '{name}' must be numeric."
            )

        value = float(value)

        if not math.isfinite(value) or not 0 <= value <= 100:
            raise ValueError(
                f"Role policy '{policy_key}': '{name}' must be "
                "between 0 and 100."
            )

        return value

    minimum_score = validate_cutoff(
        "minimum_ats_score", minimum_score
    )
    review_threshold = validate_cutoff(
        "review_score_threshold", review_threshold
    )

    if review_threshold > minimum_score:
        raise ValueError(
            f"Role policy '{policy_key}': review_score_threshold "
            "cannot exceed minimum_ats_score."
        )

    validated_policy["minimum_ats_score"] = minimum_score
    validated_policy["review_score_threshold"] = review_threshold

    return validated_policy


def _validate_experience_range(
    minimum_years: float | None,
    maximum_years: float | None,
) -> None:
    """Reject contradictory minimum and maximum experience constraints."""
    if (
        minimum_years is not None
        and maximum_years is not None
        and minimum_years > maximum_years
    ):
        raise ValueError(
            "Invalid experience range: minimum_years "
            f"({minimum_years}) exceeds maximum_years "
            f"({maximum_years})."
        )


def _resolve_role_policy(
    parsed_jd: dict[str, Any],
    policies: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Resolve the most relevant policy, then fall back to default."""
    role_category = str(
        parsed_jd.get("role_category") or ""
    ).strip().casefold()

    job_title = str(
        parsed_jd.get("job_title")
        or parsed_jd.get("job_role")
        or parsed_jd.get("title")
        or ""
    ).strip().casefold()

    explicit_policy_key = str(
        parsed_jd.get("role_policy_key") or ""
    ).strip().casefold()

    if explicit_policy_key and explicit_policy_key in policies:
        return explicit_policy_key, policies[explicit_policy_key]

    # Prefer a senior-specific backend policy when configured.
    if (
        role_category == "backend"
        and "senior" in job_title
        and "senior_backend" in policies
    ):
        return "senior_backend", policies["senior_backend"]

    if role_category and role_category in policies:
        return role_category, policies[role_category]

    return "default", policies.get("default", {})



def _normalize_location(value: Any) -> dict[str, Any]:
    """Normalize a JD location or a location policy."""

    if isinstance(value, str):
        job_location = value.strip() or None

        return {
            "job_location": job_location,
            "allowed_locations": [],
            "remote_allowed": None,
            "enforcement": "unspecified",
        }

    if not isinstance(value, dict):
        return {
            "job_location": None,
            "allowed_locations": [],
            "remote_allowed": None,
            "enforcement": "unspecified",
        }

    job_location = value.get("job_location")

    if isinstance(job_location, str):
        job_location = job_location.strip() or None
    else:
        job_location = None

    allowed_locations = value.get("allowed_locations", [])

    if isinstance(allowed_locations, str):
        allowed_locations = [allowed_locations]

    if not isinstance(allowed_locations, (list, tuple, set)):
        allowed_locations = []

    enforcement = value.get("enforcement", "unspecified")

    if enforcement not in {"mandatory", "preferred", "unspecified"}:
        enforcement = "unspecified"

    remote_allowed = value.get("remote_allowed")

    if not isinstance(remote_allowed, bool):
        remote_allowed = None

    return {
        "job_location": job_location,
        "allowed_locations": _normalize_skills(allowed_locations),
        "remote_allowed": remote_allowed,
        "enforcement": enforcement,
    }

   
def _normalize_availability(value: Any) -> dict[str, Any]:
    """Normalize availability constraints when they are explicitly provided."""
    if not isinstance(value, dict):
        return {}

    return {
        "maximum_notice_period_days": value.get(
            "maximum_notice_period_days"
        ),
        "available_from": value.get("available_from"),
        "enforcement": value.get("enforcement", "unspecified"),
    }


def generate_eligibility_rules(
    parsed_jd: dict[str, Any],
    *,
    role_policies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate validated eligibility rules from a parsed job description.

    This function generates rules only. It does not evaluate candidates
    or calculate ATS scores.
    """
    logger.info(
    "Eligibility generation | job_id=%s | parsed_jd_location=%r",
    parsed_jd.get("job_id"),
    parsed_jd.get("location"),
        )
    
    policies = _load_role_policies(role_policies)
    policy_key, policy = _resolve_role_policy(parsed_jd, policies)
    policy = _validate_role_policy(policy_key, policy)


    experience_data = parsed_jd.get("experience") or []

    if isinstance(experience_data, dict):
        experience_data = [experience_data]

    minimum_years = None
    maximum_years = None
    descriptions = []

    for item in experience_data:
        if not isinstance(item, dict):
            continue

        minimum = item.get("minimum_years")
        maximum = item.get("maximum_years")

        if minimum is not None:
            minimum = float(minimum)
            minimum_years = (
                minimum
                if minimum_years is None
                else max(minimum_years, minimum)
            )

        if maximum is not None:
            maximum = float(maximum)
            maximum_years = (
                maximum
                if maximum_years is None
                else min(maximum_years, maximum)
            )

        description = item.get("description")
        if description:
            descriptions.append(str(description).strip())

    
    _validate_experience_range(minimum_years, maximum_years)

    required_skills = _normalize_skills(
        parsed_jd.get("required_skills")
    )
    preferred_skills = _normalize_skills(
        parsed_jd.get("preferred_skills")
    )

    # Preserve the existing policy:
    # required skills are mandatory unless the JD explicitly supplies
    # a mandatory_skills field.
    if "mandatory_skills" in parsed_jd:
        mandatory_skills = _normalize_skills(
            parsed_jd.get("mandatory_skills")
        )
    else:
        mandatory_skills = required_skills.copy()

    # Explicit JD constraints take precedence over policy defaults.
    jd_location = _normalize_location(parsed_jd.get("location"))
    policy_location = _normalize_location(policy.get("location"))

    location = {
        **policy_location,
        **{
            key: value
            for key, value in jd_location.items()
            if value not in (None, [], "")
        },
    }

    jd_availability = _normalize_availability(
        parsed_jd.get("availability")
    )
    policy_availability = _normalize_availability(
        policy.get("availability")
    )

    availability = {
        **policy_availability,
        **{
            key: value
            for key, value in jd_availability.items()
            if value not in (None, "")
        },
    }

    # ScoreCutoffRule supplies its own defaults when no policy is configured.
    cutoffs = {
        "minimum_ats_score": policy.get("minimum_ats_score", 70.0),
        "review_score_threshold": policy.get(
            "review_score_threshold", 60.0
        ),
    }

    
    rules = EligibilityRuleSet(
        job_id=parsed_jd.get("job_id"),
        jd_id=parsed_jd.get("jd_id"),
        role_category=parsed_jd.get("role_category"),
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        mandatory_skills=mandatory_skills,
        cutoffs=cutoffs,
        experience={
            "minimum_years": minimum_years,
            "maximum_years": maximum_years,
            "description": "; ".join(
                description
                for description in descriptions
                if description
            ) or None,
        },
        education=_normalize_education(
            parsed_jd.get("education")
        ),
        location=location,
        availability=availability,
        requirements=parsed_jd.get("requirements") or [],
        generation_status="generated",
    )

    result = rules.model_dump()

    # Preserve job_location explicitly in the serialized output.
    # This also helps diagnose a model that does not yet declare
    # the job_location field.
    result_location = dict(result.get("location") or {})
    result_location["job_location"] = location.get("job_location")
    result["location"] = result_location

    result["role_policy_key"] = policy_key

    return result
