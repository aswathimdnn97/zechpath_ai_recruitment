
"""
Eligibility evaluation service.

Responsibilities
----------------
1. Evaluate ATS score against configured thresholds.
2. Check mandatory skills.
3. Evaluate candidate experience against configured limits.
4. Evaluate mandatory and preferred education requirements.
5. Evaluate explicitly configured location restrictions.
6. Evaluate explicitly configured availability requirements.
7. Return a consistent eligibility result dictionary.

Design principles
-----------------
- Missing information is not automatically treated as a failure.
- Mandatory requirements requiring verification trigger review.
- Preferred requirements do not independently block eligibility.
- Only explicit mandatory failures cause rejection.
- Education helpers remain separate from the main evaluator.
"""

import logging
import re
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_skill(value: str) -> str:
    """Normalize a skill for case-insensitive comparison."""
    return re.sub(r"\s+", " ", value.strip().casefold())


def _normalize_location(value: str) -> str:
    """Normalize a location for case-insensitive comparison."""
    value = value.strip().casefold()
    value = re.sub(r"[^\w\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _get_profile(
    candidate_profile: dict[str, Any],
) -> dict[str, Any]:
    """Return the candidate profile, supporting wrapped profiles."""
    profile = candidate_profile.get("masked_profile", candidate_profile)
    return profile if isinstance(profile, dict) else {}


# ============================================================
# SKILLS
# ============================================================

def _extract_skill_names(
    candidate_profile: dict[str, Any],
) -> set[str]:
    """Extract skill names from supported profile structures."""
    profile = _get_profile(candidate_profile)
    skills = profile.get("skills", [])

    if isinstance(skills, dict):
        skill_values = [
            skill
            for values in skills.values()
            for skill in (
                values if isinstance(values, list) else [values]
            )
        ]
    elif isinstance(skills, list):
        skill_values = skills
    else:
        skill_values = []

    result: set[str] = set()

    for skill in skill_values:
        if isinstance(skill, str) and skill.strip():
            result.add(_normalize_skill(skill))

        elif isinstance(skill, dict):
            name = skill.get("name") or skill.get("skill")

            if isinstance(name, str) and name.strip():
                result.add(_normalize_skill(name))

    return result


# ============================================================
# EXPERIENCE
# ============================================================

def _parse_experience_month(value: str) -> int | None:
    """Convert supported month/year values into a month index."""
    if not isinstance(value, str):
        return None

    value = value.strip()

    if not value:
        return None

    if value.casefold() in {"present", "current", "now"}:
        today = date.today()
        return today.year * 12 + today.month - 1

    value = value.replace("\uFFFD", " ").strip()

    for date_format in (
        "%B %Y",
        "%b %Y",
        "%m/%Y",
        "%m-%Y",
        "%Y",
    ):
        try:
            parsed = datetime.strptime(value, date_format)
            return parsed.year * 12 + parsed.month - 1
        except ValueError:
            continue

    return None


def _extract_experience_years(
    candidate_profile: dict[str, Any],
) -> float | None:
    """Calculate non-overlapping experience from extracted date ranges."""
    profile = _get_profile(candidate_profile)
    experiences = profile.get("experience")

    if not isinstance(experiences, list) or not experiences:
        total = profile.get("total_experience_years")

        if isinstance(total, (int, float)) and not isinstance(total, bool):
            return float(total) if total >= 0 else None

        return None

    intervals: list[tuple[int, int]] = []

    for item in experiences:
        if not isinstance(item, dict):
            continue

        duration = item.get("duration")

        if not isinstance(duration, dict):
            continue

        start = _parse_experience_month(duration.get("start_date"))
        end = _parse_experience_month(duration.get("end_date"))

        if start is None or end is None or end < start:
            continue

        intervals.append((start, end))

    if not intervals:
        total = profile.get("total_experience_years")

        if isinstance(total, (int, float)) and not isinstance(total, bool):
            return float(total) if total >= 0 else None

        return None

    intervals.sort()
    merged: list[tuple[int, int]] = []

    start, end = intervals[0]

    for next_start, next_end in intervals[1:]:
        if next_start <= end + 1:
            end = max(end, next_end)
        else:
            merged.append((start, end))
            start, end = next_start, next_end

    merged.append((start, end))

    total_months = sum(
        end - start + 1
        for start, end in merged
    )

    return round(total_months / 12, 2)


# ============================================================
# CANDIDATE LOCATION
# ============================================================


def _extract_candidate_location(
    candidate_profile: dict[str, Any],
) -> str | None:
    """Extract location from direct or wrapped candidate profiles."""
    profile = _get_profile(candidate_profile)

    sources = [profile]

    original_profile = candidate_profile.get("original_profile")
    if isinstance(original_profile, dict):
        sources.append(original_profile)

    for source in sources:
        personal_info = source.get("personal_information")

        candidates = [
            source.get("location"),
            source.get("current_location"),
        ]

        if isinstance(personal_info, dict):
            candidates.extend([
                personal_info.get("location"),
                personal_info.get("city"),
            ])

        for value in candidates:
            if isinstance(value, str) and value.strip():
                return value.strip()

    return None

def _location_matches(
    candidate_location: str,
    allowed_location: str,
) -> bool:
    """
    Match complete location phrases.

    Example:
        Candidate: Kochi, Kerala
        Allowed: Kochi
    """
    candidate = _normalize_location(candidate_location)
    allowed = _normalize_location(allowed_location)

    if not candidate or not allowed:
        return False

    if candidate == allowed:
        return True

    return (
        re.search(
            rf"(?<!\w){re.escape(allowed)}(?!\w)",
            candidate,
        )
        is not None
    )


# ============================================================
# CANDIDATE AVAILABILITY
# ============================================================


def _extract_notice_period(
    candidate_profile: dict[str, Any],
) -> int | None:
    """Read a numeric notice period from direct or wrapped profiles."""
    profile = _get_profile(candidate_profile)
    sources = [profile]

    original_profile = candidate_profile.get("original_profile")
    if isinstance(original_profile, dict):
        sources.append(original_profile)

    for source in sources:
        availability = source.get("availability")
        values = [source.get("notice_period_days")]

        if isinstance(availability, dict):
            values.append(availability.get("notice_period_days"))

        for value in values:
            if (
                isinstance(value, int)
                and not isinstance(value, bool)
                and value >= 0
            ):
                return value

    return None

# ============================================================
# ATS SCORE
# ============================================================

def _evaluate_score(
    ats_score: float | None,
    cutoffs: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate ATS score against configured thresholds."""
    minimum_score = float(cutoffs.get("minimum_ats_score", 70))
    review_threshold = float(cutoffs.get("review_score_threshold", 60))

    if ats_score is None:
        return {
            "status": "NOT_PROVIDED",
            "ats_score": None,
            "minimum_ats_score": minimum_score,
            "review_score_threshold": review_threshold,
            "reason": "ATS score was not supplied.",
        }

    if (
        isinstance(ats_score, bool)
        or not isinstance(ats_score, (int, float))
        or not 0 <= ats_score <= 100
    ):
        return {
            "status": "UNKNOWN",
            "ats_score": ats_score,
            "reason": "ATS score must be between 0 and 100.",
        }

    if ats_score < review_threshold:
        status = "FAIL"
        reason = "ATS score is below the review threshold."
    elif ats_score < minimum_score:
        status = "REVIEW_REQUIRED"
        reason = "ATS score is below the minimum eligibility cutoff."
    else:
        status = "PASS"
        reason = "ATS score meets the minimum eligibility cutoff."

    return {
        "status": status,
        "ats_score": ats_score,
        "minimum_ats_score": minimum_score,
        "review_score_threshold": review_threshold,
        "reason": reason,
    }


# ============================================================
# LOCATION EVALUATION
# ============================================================

def _evaluate_location(
    profile: dict[str, Any],
    location_rule: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate explicit geographic restrictions."""
    candidate_location = _extract_candidate_location(profile)

    job_location = location_rule.get("job_location")
    if not isinstance(job_location, str) or not job_location.strip():
        job_location = None
    else:
        job_location = job_location.strip()

    allowed_locations = location_rule.get("allowed_locations") or []

    if isinstance(allowed_locations, str):
        allowed_locations = [allowed_locations]

    if not isinstance(allowed_locations, list):
        allowed_locations = []

    allowed_locations = [
        value.strip()
        for value in allowed_locations
        if isinstance(value, str) and value.strip()
    ]

    enforcement = str(
        location_rule.get("enforcement", "unspecified")
    ).strip().casefold()

    remote_allowed = location_rule.get("remote_allowed")

    details = {
        "job_location": job_location,
        "candidate_location": candidate_location,
        "allowed_locations": allowed_locations,
        "remote_allowed": remote_allowed,
    }

    if enforcement == "unspecified":
        return {
            **details,
            "status": "NOT_SPECIFIED",
            "reason": "No enforced geographic restriction is configured.",
        }

    if not allowed_locations:
        if enforcement == "mandatory":
            return {
                **details,
                "status": "UNKNOWN",
                "reason": (
                    "Location enforcement is mandatory, but no allowed "
                    "locations are configured. Verify the job rule."
                ),
            }

        return {
            **details,
            "status": "NOT_SPECIFIED",
            "reason": "No allowed locations are configured for comparison.",
        }

    if candidate_location is None:
        if enforcement == "mandatory":
            status = "UNKNOWN"
            reason = (
                "Candidate location is unavailable. Verify the "
                "candidate's location before making a decision."
            )
        else:
            status = "PREFERRED"
            reason = (
                "Candidate location is unavailable; the preference "
                "cannot be verified."
            )

        return {
            **details,
            "status": status,
            "reason": reason,
        }

    matches = any(
        _location_matches(candidate_location, allowed)
        for allowed in allowed_locations
    )

    if matches:
        return {
            **details,
            "status": "PASS",
            "reason": (
                "Candidate location matches a configured allowed location."
            ),
        }

    if enforcement == "mandatory":
        return {
            **details,
            "status": "FAIL",
            "reason": (
                "Candidate location does not match the configured "
                "mandatory locations. Verify relocation or other "
                "approved arrangements before final rejection."
            ),
        }

    return {
        **details,
        "status": "PREFERRED",
        "reason": (
            "Candidate location does not match the preferred locations."
        ),
    }


# ============================================================
# AVAILABILITY EVALUATION
# ============================================================

def _evaluate_availability(
    profile: dict[str, Any],
    availability_rule: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate configured notice-period requirements."""
    maximum_notice = availability_rule.get(
        "maximum_notice_period_days"
    )
    available_from = availability_rule.get("available_from")

    enforcement = str(
        availability_rule.get("enforcement", "unspecified")
    ).strip().casefold()

    candidate_notice = _extract_notice_period(profile)

    details = {
        "notice_period_days": candidate_notice,
        "maximum_notice_period_days": maximum_notice,
        "available_from": available_from,
    }

    if maximum_notice is None and not available_from:
        return {
            **details,
            "status": "NOT_SPECIFIED",
            "reason": "No availability requirement is configured.",
        }

    if maximum_notice is None and available_from:
        return {
            **details,
            "status": (
                "UNKNOWN" if enforcement == "mandatory" else "PREFERRED"
            ),
            "reason": (
                "An availability date is configured, but date-based "
                "eligibility comparison is not implemented."
            ),
        }

    if (
        isinstance(maximum_notice, bool)
        or not isinstance(maximum_notice, (int, float))
        or maximum_notice < 0
    ):
        return {
            **details,
            "status": "UNKNOWN",
            "reason": "The configured maximum notice period is invalid.",
        }

    if enforcement == "unspecified":
        return {
            **details,
            "status": "NOT_SPECIFIED",
            "reason": (
                "A notice-period value exists, but no enforcement "
                "policy is configured."
            ),
        }

    if candidate_notice is None:
        if enforcement == "mandatory":
            status = "UNKNOWN"
            reason = (
                "Candidate notice period is unavailable. Verify "
                "availability with the candidate."
            )
        else:
            status = "PREFERRED"
            reason = (
                "Candidate notice period is unavailable; the "
                "availability preference cannot be verified."
            )

        return {
            **details,
            "status": status,
            "reason": reason,
        }

    if candidate_notice <= maximum_notice:
        return {
            **details,
            "status": "PASS",
            "reason": "Candidate notice period meets the configured limit.",
        }

    if enforcement == "mandatory":
        return {
            **details,
            "status": "FAIL",
            "reason": (
                "Candidate notice period exceeds the configured "
                "mandatory limit."
            ),
        }

    return {
        **details,
        "status": "PREFERRED",
        "reason": "Candidate notice period exceeds the preferred limit.",
    }


# ============================================================
# EDUCATION NORMALIZATION AND EXTRACTION
# ============================================================

def _normalize_education_text(value: str) -> str:
    """Normalize education text for case-insensitive comparison."""
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _extract_candidate_education(
    candidate_profile: dict[str, Any],
) -> list[str]:
    """Extract education values from supported profile structures."""
    profile = _get_profile(candidate_profile)
    sources = [profile]

    original_profile = candidate_profile.get("original_profile")
    if isinstance(original_profile, dict):
        sources.append(original_profile)

    education_texts: list[str] = []
    seen: set[str] = set()

    education_fields = (
        "degree",
        "degree_type",
        "qualification",
        "education_level",
        "field",
        "field_of_study",
        "specialization",
        "course",
        "program",
        "title",
    )

    def add_value(value: Any) -> None:
        if isinstance(value, str) and value.strip():
            cleaned = value.strip()
            normalized = _normalize_education_text(cleaned)

            if normalized and normalized not in seen:
                seen.add(normalized)
                education_texts.append(cleaned)

    for source in sources:
        education = source.get("education")

        if isinstance(education, str):
            add_value(education)

        elif isinstance(education, list):
            for item in education:
                if isinstance(item, str):
                    add_value(item)
                elif isinstance(item, dict):
                    for field in education_fields:
                        add_value(item.get(field))

        elif isinstance(education, dict):
            if any(field in education for field in education_fields):
                for field in education_fields:
                    add_value(education.get(field))
            else:
                for value in education.values():
                    if isinstance(value, str):
                        add_value(value)
                    elif isinstance(value, list):
                        for item in value:
                            if isinstance(item, str):
                                add_value(item)
                            elif isinstance(item, dict):
                                for field in education_fields:
                                    add_value(item.get(field))
                    elif isinstance(value, dict):
                        for field in education_fields:
                            add_value(value.get(field))

    return education_texts


def _education_alias_group(value: str) -> str | None:
    """Identify supported equivalent degree names."""
    normalized = _normalize_education_text(value)

    aliases = {
        "technical_bachelors": (
            "b tech",
            "btech",
            "bachelor of technology",
            "b e",
            "be",
            "bachelor of engineering",
            "b eng",
            "beng",
        ),
    }

    for group, phrases in aliases.items():
        for phrase in phrases:
            if re.search(
                rf"(?<!\w){re.escape(phrase)}(?!\w)",
                normalized,
            ):
                return group

    return None


def _education_requirement_values(
    rule: dict[str, Any],
) -> list[str]:
    """Collect structured education requirements and descriptions."""
    values: list[str] = []

    fields = (
        "degree",
        "degree_type",
        "required_degree",
        "qualification",
        "education_level",
        "description",
    )

    for field in fields:
        value = rule.get(field)

        if isinstance(value, str) and value.strip():
            values.append(value.strip())
        elif isinstance(value, list):
            values.extend(
                item.strip()
                for item in value
                if isinstance(item, str) and item.strip()
            )

    for field in ("degrees", "required_degrees", "accepted_degrees"):
        value = rule.get(field)

        if isinstance(value, str) and value.strip():
            values.append(value.strip())
        elif isinstance(value, list):
            values.extend(
                item.strip()
                for item in value
                if isinstance(item, str) and item.strip()
            )

    return list(dict.fromkeys(values))



def _education_requirement_matches(
    candidate_education: list[str],
    rule: dict[str, Any],
) -> bool | None:
    """
    Return True for a match, False for a known mismatch,
    or None when the available information is insufficient.
    """
    if not candidate_education:
        return None

    requirements = _education_requirement_values(rule)

    if not requirements:
        return None

    candidate_text = [
        _normalize_education_text(value)
        for value in candidate_education
    ]

    # Prefer structured degree fields over descriptive JD text.
    structured_fields = (
        "degree",
        "degree_type",
        "required_degree",
        "qualification",
        "education_level",
        "degrees",
        "required_degrees",
        "accepted_degrees",
    )

    structured_requirements: list[str] = []

    for field in structured_fields:
        value = rule.get(field)

        if isinstance(value, str) and value.strip():
            structured_requirements.append(value.strip())
        elif isinstance(value, list):
            structured_requirements.extend(
                item.strip()
                for item in value
                if isinstance(item, str) and item.strip()
            )

    if structured_requirements:
        for requirement in structured_requirements:
            normalized_requirement = _normalize_education_text(
                requirement
            )

            if not normalized_requirement:
                continue

            requirement_group = _education_alias_group(requirement)

            for candidate_value in candidate_education:
                normalized_candidate = _normalize_education_text(
                    candidate_value
                )

                if normalized_candidate == normalized_requirement:
                    return True

                candidate_group = _education_alias_group(
                    candidate_value
                )

                if (
                    requirement_group is not None
                    and candidate_group == requirement_group
                ):
                    return True

        # Explicit degree requirements exist and candidate education
        # is known, but none of the required qualifications matched.
        return False

    # Fall back to descriptive requirements when no structured
    # degree or qualification field is supplied.
    requirement_text = " ".join(requirements)
    normalized_requirement = _normalize_education_text(
        requirement_text
    )

    requirement_group = _education_alias_group(requirement_text)

    if requirement_group is not None:
        candidate_groups = [
            _education_alias_group(value)
            for value in candidate_education
        ]

        if requirement_group in candidate_groups:
            return True

        # Do not assume that an unrelated degree is equivalent.
        return None

    for requirement in requirements:
        normalized = _normalize_education_text(requirement)

        if not normalized:
            continue

        for value in candidate_text:
            if (
                normalized == value
                or re.search(
                    rf"(?<!\w){re.escape(normalized)}(?!\w)",
                    value,
                )
            ):
                return True

    return False

# ============================================================
# EDUCATION EVALUATION
# ============================================================

def _evaluate_education(
    candidate_profile: dict[str, Any],
    education_rules: Any,
) -> dict[str, Any]:
    """
    Evaluate education requirements.

    Mandatory:
        Match       -> PASS
        Mismatch    -> REVIEW_REQUIRED
        Unverifiable -> UNKNOWN

    Preferred:
        Match       -> PASS
        Mismatch or unverifiable -> PREFERRED

    Unspecified:
        -> NOT_SPECIFIED
    """
    if not education_rules:
        return {
            "status": "NOT_SPECIFIED",
            "candidate_education": [],
            "rules": [],
            "reason": "No education requirement is configured.",
        }

    if isinstance(education_rules, dict):
        education_rules = [education_rules]

    if not isinstance(education_rules, list):
        return {
            "status": "UNKNOWN",
            "candidate_education": [],
            "rules": [],
            "reason": "Education rules have an invalid format.",
        }

    candidate_education = _extract_candidate_education(candidate_profile)
    evaluated_rules: list[dict[str, Any]] = []
    mandatory_statuses: list[str] = []

    
    for rule in education_rules:
        if isinstance(rule, str) and rule.strip():
            # A plain-string education rule has no explicit mandatory
            # enforcement, so treat it as a preference.
            rule = {
                "description": rule.strip(),
                "enforcement": "preferred",
            }

        if not isinstance(rule, dict):
            evaluated_rules.append({
                "status": "UNKNOWN",
                "reason": "Education rule has an invalid format.",
            })
            continue


        enforcement = str(
            rule.get("enforcement", "unspecified")
        ).strip().casefold()

        if enforcement not in {"mandatory", "preferred", "unspecified"}:
            evaluated_rules.append({
                **rule,
                "status": "UNKNOWN",
                "reason": "Education enforcement value is invalid.",
            })
            mandatory_statuses.append("UNKNOWN")
            continue

        match = _education_requirement_matches(candidate_education, rule)

        if enforcement == "unspecified":
            status = "NOT_SPECIFIED"
            reason = "Education requirement is not enforced."

        elif match is True:
            status = "PASS"
            reason = (
                "Candidate education matches the configured qualification."
            )
            if enforcement == "mandatory":
                mandatory_statuses.append("PASS")

        elif enforcement == "preferred":
            status = "PREFERRED"
            reason = (
                "Preferred qualification could not be confirmed as a match. "
                "This does not block eligibility."
            )

        elif match is None:
            status = "UNKNOWN"
            reason = (
                "Candidate education or the requirement could not "
                "be verified reliably."
            )
            mandatory_statuses.append("UNKNOWN")

        else:
            status = "REVIEW_REQUIRED"
            reason = (
                "The mandatory education requirement was not matched. "
                "Verify the qualification before making a decision."
            )
            mandatory_statuses.append("REVIEW_REQUIRED")

        evaluated_rules.append({
            **rule,
            "status": status,
            "reason": reason,
        })

    if not evaluated_rules:
        return {
            "status": "NOT_SPECIFIED",
            "candidate_education": candidate_education,
            "rules": [],
            "reason": "No valid education rules are configured.",
        }

    if "REVIEW_REQUIRED" in mandatory_statuses:
        overall_status = "REVIEW_REQUIRED"
        overall_reason = (
            "A mandatory education requirement needs verification."
        )
    elif "UNKNOWN" in mandatory_statuses:
        overall_status = "UNKNOWN"
        overall_reason = (
            "A mandatory education requirement could not be verified."
        )
    elif mandatory_statuses:
        overall_status = "PASS"
        overall_reason = (
            "All evaluated mandatory education requirements passed."
        )
    elif any(
        item.get("status") == "PASS"
        for item in evaluated_rules
    ):
        overall_status = "PASS"
        overall_reason = (
            "Candidate education matches the configured qualification."
        )
    else:
        overall_status = "PREFERRED"
        overall_reason = (
            "Education is optional or preferred and does not "
            "block candidate eligibility."
        )

    return {
        "status": overall_status,
        "candidate_education": candidate_education,
        "rules": evaluated_rules,
        "reason": overall_reason,
    }


# ============================================================
# MAIN ELIGIBILITY EVALUATION
# ============================================================

def evaluate_candidate_eligibility(
    candidate_profile: dict[str, Any],
    generated_rules: dict[str, Any],
    ats_score: float | None = None,
) -> dict[str, Any]:
    """
    Evaluate a candidate against generated eligibility rules.

    All checks are assembled here and the function always returns
    the final result dictionary for a valid rules/profile structure.
    """
    if not isinstance(candidate_profile, dict):
        raise TypeError("candidate_profile must be a dictionary.")

    if not isinstance(generated_rules, dict):
        raise TypeError("generated_rules must be a dictionary.")

    rules = generated_rules.get("eligibility_rules", generated_rules)

    if not isinstance(rules, dict):
        raise TypeError("eligibility_rules must be a dictionary.")

    profile = _get_profile(candidate_profile)

    candidate_id = (
        candidate_profile.get("candidate_id")
        or profile.get("candidate_id")
    )

    logger.info(
        "Eligibility evaluation started | candidate_id=%s",
        candidate_id,
    )

    # ---------------------------------------------------------
    # 1. ATS SCORE
    # ---------------------------------------------------------
    cutoffs = rules.get("cutoffs") or {}

    if not isinstance(cutoffs, dict):
        cutoffs = {}

    score_check = _evaluate_score(ats_score, cutoffs)

    # ---------------------------------------------------------
    # 2. MANDATORY SKILLS
    # ---------------------------------------------------------
    candidate_skills = _extract_skill_names(candidate_profile)
    mandatory_skills = rules.get("mandatory_skills") or []

    if isinstance(mandatory_skills, str):
        mandatory_skills = [mandatory_skills]

    if not isinstance(mandatory_skills, list):
        mandatory_skills = []

    missing_skills = [
        skill
        for skill in mandatory_skills
        if (
            isinstance(skill, str)
            and skill.strip()
            and _normalize_skill(skill) not in candidate_skills
        )
    ]

    if not mandatory_skills:
        skills_check = {
            "status": "NOT_SPECIFIED",
            "missing_skills": [],
        }
    elif missing_skills:
        skills_check = {
            "status": "REVIEW_REQUIRED",
            "missing_skills": missing_skills,
            "reason": (
                "Mandatory skills were not found in the extracted "
                "profile. Verify the resume before making a decision."
            ),
        }
    else:
        skills_check = {
            "status": "PASS",
            "missing_skills": [],
        }

    # ---------------------------------------------------------
    # 3. EXPERIENCE
    # ---------------------------------------------------------
    experience_rule = rules.get("experience") or {}

    if not isinstance(experience_rule, dict):
        experience_rule = {}

    minimum_years = experience_rule.get("minimum_years")
    maximum_years = experience_rule.get("maximum_years")

    experience_is_configured = (
        minimum_years is not None or maximum_years is not None
    )

    candidate_years = _extract_experience_years(candidate_profile)

    if not experience_is_configured:
        experience_check = {
            "status": "NOT_SPECIFIED",
            "candidate_years": candidate_years,
            "reason": "No experience requirement is configured.",
        }

    elif candidate_years is None:
        experience_check = {
            "status": "UNKNOWN",
            "candidate_years": None,
            "reason": (
                "Experience is required for evaluation but could not "
                "be verified from the candidate profile."
            ),
        }

    elif (
        (
            minimum_years is not None
            and (
                isinstance(minimum_years, bool)
                or not isinstance(minimum_years, (int, float))
            )
        )
        or (
            maximum_years is not None
            and (
                isinstance(maximum_years, bool)
                or not isinstance(maximum_years, (int, float))
            )
        )
        or (
            minimum_years is not None
            and maximum_years is not None
            and minimum_years > maximum_years
        )
    ):
        experience_check = {
            "status": "UNKNOWN",
            "candidate_years": candidate_years,
            "reason": "The configured experience range is invalid.",
        }

    else:
        outside_range = (
            (
                minimum_years is not None
                and candidate_years < minimum_years
            )
            or (
                maximum_years is not None
                and candidate_years > maximum_years
            )
        )

        experience_check = {
            "status": "REVIEW_REQUIRED" if outside_range else "PASS",
            "candidate_years": candidate_years,
        }

        if outside_range:
            experience_check["reason"] = (
                "Candidate experience is outside the configured "
                "JD range. Verify before making a decision."
            )

    # ---------------------------------------------------------
    # 4. EDUCATION
    # ---------------------------------------------------------
    education_rules = rules.get("education") or []

    education_check = _evaluate_education(
        candidate_profile,
        education_rules,
    )

    # ---------------------------------------------------------
    # 5. LOCATION
    # ---------------------------------------------------------
    location_rule = rules.get("location") or {}

    if not isinstance(location_rule, dict):
        location_rule = {}

    location_check = _evaluate_location(
        candidate_profile,
        location_rule,
    )

    # ---------------------------------------------------------
    # 6. AVAILABILITY
    # ---------------------------------------------------------
    availability_rule = rules.get("availability") or {}

    if not isinstance(availability_rule, dict):
        availability_rule = {}

    availability_check = _evaluate_availability(
        candidate_profile,
        availability_rule,
    )

    # ---------------------------------------------------------
    # 7. COLLECT CHECKS
    # ---------------------------------------------------------
    checks = {
        "ats_score": score_check,
        "skills": skills_check,
        "experience": experience_check,
        "education": education_check,
        "location": location_check,
        "availability": availability_check,
    }

    # ---------------------------------------------------------
    # 8. FINAL DECISION
    # ---------------------------------------------------------
    location_enforcement = str(
        location_rule.get("enforcement", "unspecified")
    ).strip().casefold()

    availability_enforcement = str(
        availability_rule.get("enforcement", "unspecified")
    ).strip().casefold()

    has_definite_failure = (
        score_check.get("status") == "FAIL"
        or (
            location_check.get("status") == "FAIL"
            and location_enforcement == "mandatory"
        )
        or (
            availability_check.get("status") == "FAIL"
            and availability_enforcement == "mandatory"
        )
    )

    needs_review = any(
        check.get("status") in {"REVIEW_REQUIRED", "UNKNOWN"}
        for check in checks.values()
    )

    if has_definite_failure:
        eligibility_status = "REJECTED"
    elif needs_review:
        eligibility_status = "REVIEW_REQUIRED"
    else:
        eligibility_status = "ELIGIBLE"

    # ---------------------------------------------------------
    # 9. REASONS
    # ---------------------------------------------------------
    reasons = [
        check["reason"]
        for check in checks.values()
        if check.get("reason")
    ]

    result = {
        "job_id": rules.get("job_id"),
        "jd_id": rules.get("jd_id"),
        "candidate_id": candidate_id,
        "eligibility_status": eligibility_status,
        "ats_score": ats_score,
        "rule_version": rules.get("rule_version", "1.0"),
        "checks": checks,
        "reasons": reasons,
    }

    logger.info(
        "Eligibility evaluation completed | candidate_id=%s | status=%s",
        candidate_id,
        eligibility_status,
    )

    return result
