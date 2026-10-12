from document_processing.resume.entity_extracter.skill.spelling_resolver import (
    resolve_spelling,
)

from document_processing.resume.entity_extracter.skill.synonym_resolver import (
    resolve_synonyms,
)

from document_processing.resume.entity_extracter.skill.master_skill_validator import (
    validate_skills,
)

from document_processing.resume.entity_extracter.skill.stack_resolver import (
    expand_skill_stacks,
)


# ============================================================
# CLEAN INPUT
# ============================================================

def _clean_strings(items):
    """
    Keep only non-empty technology strings.
    """

    if not items:
        return []

    result = []

    for item in items:

        if not isinstance(item, str):
            continue

        item = item.strip()

        if not item:
            continue

        result.append(item)

    return result


# ============================================================
# EXTRACT SKILL NAMES
# ============================================================

def _extract_skill_names(items):
    """
    Extract canonical skill names from resolver outputs.

    Supports both:

        {"skill": "Python"}

    and possible alternate dictionary structures.
    """

    if not items:
        return []

    result = []

    for item in items:

        if isinstance(item, dict):

            skill = (
                item.get("skill")
                or item.get("matched_skill")
                or item.get("canonical_skill")
                or item.get("name")
            )

            if isinstance(skill, str):

                skill = skill.strip()

                if skill:
                    result.append(skill)

        elif isinstance(item, str):

            item = item.strip()

            if item:
                result.append(item)

    return result


# ============================================================
# DEDUPLICATION
# ============================================================

def _deduplicate(items):
    """
    Remove duplicate technology names while preserving order.
    """

    result = []
    seen = set()

    for item in items:

        if not isinstance(item, str):
            continue

        item = item.strip()

        if not item:
            continue

        key = item.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


# ============================================================
# NORMALIZE PROJECT TECHNOLOGIES
# ============================================================

def normalize_project_technologies(
    technologies,
    spelling_threshold=90,
    skill_threshold=90,
):
    """
    Normalize project technologies through the existing
    skill normalization pipeline.

    Pipeline:

        raw technologies
            ↓
        spelling resolver
            ↓
        synonym resolver
            ↓
        master skill validator
            ↓
        stack resolver
            ↓
        canonical technology names
    """

    # --------------------------------------------------------
    # INPUT
    # --------------------------------------------------------

    cleaned = _clean_strings(technologies)

    if not cleaned:
        return []

    # --------------------------------------------------------
    # 1. SPELLING RESOLUTION
    # --------------------------------------------------------

    try:

        spelling_resolved = resolve_spelling(
            cleaned,
            threshold=spelling_threshold,
        )

    except TypeError:

        spelling_resolved = resolve_spelling(
            cleaned
        )

    if not spelling_resolved:
        spelling_resolved = cleaned

    # IMPORTANT:
    # Keep the dictionary structure.
    #
    # Do NOT convert to list[str] here.
    #
    # Example:
    #
    # [
    #     {"skill": "Python"},
    #     {"skill": "FastAPI"}
    # ]

    # --------------------------------------------------------
    # 2. SYNONYM RESOLUTION
    # --------------------------------------------------------

    try:

        synonym_resolved = resolve_synonyms(
            spelling_resolved
        )

    except TypeError:

        synonym_resolved = spelling_resolved

    if not synonym_resolved:
        synonym_resolved = spelling_resolved

    # --------------------------------------------------------
    # 3. MASTER SKILL VALIDATION
    # --------------------------------------------------------

    try:

        validated = validate_skills(
            synonym_resolved,
            threshold=skill_threshold,
        )

    except TypeError:

        validated = validate_skills(
            synonym_resolved
        )

    # --------------------------------------------------------
    # 4. STACK EXPANSION
    # --------------------------------------------------------

    if validated:
        try:

            expanded = expand_skill_stacks(
                validated
            )

        except TypeError:

            expanded = validated

        if not expanded:
            expanded = validated
    else:
        expanded = []

    # --------------------------------------------------------
    # 5. EXTRACT FINAL CANONICAL NAMES
    # --------------------------------------------------------

    final_names = _extract_skill_names(
        expanded
    )

    # Project technology lists are explicit resume content, so keep
    # declared technologies even when the master skill catalog lacks them.
    for candidate in synonym_resolved:

        names = _extract_skill_names(
            [candidate]
        )

        if not names:
            continue

        try:
            candidate_validation = validate_skills(
                [candidate],
                threshold=skill_threshold,
            )
        except TypeError:
            candidate_validation = validate_skills(
                [candidate]
            )

        if candidate_validation:
            continue

        final_names.extend(names)

    # --------------------------------------------------------
    # 6. DEDUPLICATION
    # --------------------------------------------------------

    return _deduplicate(
        final_names
    )