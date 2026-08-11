
from document_processing.resume.entity_extracter.skill.spelling_resolver import resolve_spelling
from document_processing.resume.entity_extracter.skill.synonym_resolver import resolve_synonyms
from document_processing.resume.entity_extracter.skill.stack_resolver import expand_skill_stacks
from document_processing.resume.entity_extracter.skill.master_skill_validator import validate_skills


def normalize_project_technologies(
    technologies,
    spelling_threshold=90,
    skill_threshold=90,
):
    """
    Normalize project technologies using the existing
    skill normalization pipeline.

    Parameters
    ----------
    technologies : list[str]
        Raw technologies extracted from a project.

    spelling_threshold : int
        Threshold used by the spelling resolver.

    skill_threshold : int
        Threshold used by the master skill validator.

    Returns
    -------
    list[str]
        Normalized canonical technologies.
    """

    if not technologies:
        return []

    # ========================================================
    # Step 1: Clean raw input
    # ========================================================

    cleaned = [
        technology.strip()
        for technology in technologies
        if technology and isinstance(technology, str) and technology.strip()
    ]

    if not cleaned:
        return []

    # ========================================================
    # Step 2: Spelling resolution
    # ========================================================

    try:
        normalized = resolve_spelling(
            cleaned,
            threshold=spelling_threshold,
        )
    except TypeError:
        normalized = resolve_spelling(cleaned)

    normalized = [
        technology.strip()
        for technology in normalized
        if technology and isinstance(technology, str) and technology.strip()
    ]

    # ========================================================
    # Step 3: Synonym resolution
    # ========================================================

    try:
        synonym_normalized = resolve_synonyms(normalized)
    except TypeError:
        synonym_normalized = normalized

    synonym_normalized = [
        technology.strip()
        for technology in synonym_normalized
        if technology and isinstance(technology, str) and technology.strip()
    ]

    # ========================================================
    # Step 4: Master skill validation
    # ========================================================

    try:
        validated = validate_skills(
            synonym_normalized,
            threshold=skill_threshold,
        )
    except TypeError:
        validated = validate_skills(synonym_normalized)

    # ========================================================
    # Step 5: Expand skill stacks
    # ========================================================

    try:
        expanded = expand_skill_stacks(validated)
    except TypeError:
        expanded = validated

    # ========================================================
    # Step 6: Convert validator output to canonical skill names
    # ========================================================

    final_technologies = []

    for item in expanded:

        if isinstance(item, dict):

            canonical = (
                item.get("matched_skill")
                or item.get("canonical_skill")
                or item.get("skill")
            )

            if canonical:
                final_technologies.append(canonical)

        elif isinstance(item, str):

            final_technologies.append(item)

    # ========================================================
    # Step 7: Final duplicate removal
    # ========================================================

    result = []
    seen = set()

    for technology in final_technologies:

        key = technology.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(technology)

    return result