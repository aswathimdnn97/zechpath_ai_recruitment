"""
skill_extractor.py

Central skill extraction orchestrator.

Responsibilities
----------------
1. Collect skill candidates from multiple resume sections.
2. Use skill_list_splitter.py for dedicated Skills sections.
3. Use skill_extractor_from_section.py for prose sections.
4. Preserve source/evidence metadata.
5. Resolve spelling.
6. Resolve synonyms / aliases.
7. Validate against the master skill dictionary.
8. Expand technology stacks.
9. Deduplicate final skills.

Pipeline
--------
Resume sections
        ↓
Collect candidates
        ↓
Spelling resolver
        ↓
Synonym resolver
        ↓
Master skill validator
        ↓
Stack resolver
        ↓
Final skills
"""


from document_processing.resume.entity_extracter.skill.skill_list_splitter import (
    split_skill_line,
)

from document_processing.resume.entity_extracter.skill.skill_extractor_from_section import (
    extract_skills_from_section,
)

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
# SECTIONS FROM WHICH TECHNICAL SKILLS CAN BE EXTRACTED
# ============================================================

SKILL_SOURCE_SECTIONS = {
    "skills",
    "summary",
    "experience",
    "projects",
    "certifications",
    "education",
    "achievements",
    "publications",
    "activities",
}


# ============================================================
# SECTIONS THAT SHOULD NOT BE USED FOR TECHNICAL SKILLS
# ============================================================

IGNORED_SECTIONS = {
    "personal_information",
    "languages",
    "interests",
    "references",
    "declaration",
}


# ============================================================
# FLATTEN SECTION DATA
# ============================================================

def _flatten_section(value):
    """
    Flatten nested section data.

    Section detector output can sometimes contain:

        [
            "Python",
            ["Django", "FastAPI"],
            "PostgreSQL"
        ]

    This becomes:

        [
            "Python",
            "Django",
            "FastAPI",
            "PostgreSQL"
        ]
    """

    result = []

    def flatten(item):

        if isinstance(item, list):

            for child in item:
                flatten(child)

        elif isinstance(item, str):

            cleaned = item.strip()

            if cleaned:
                result.append(cleaned)

    flatten(value)

    return result


# ============================================================
# NORMALIZE TEXT
# ============================================================

def _normalize(value):
    """
    Normalize a value for case-insensitive comparison.
    """

    if not isinstance(value, str):
        return ""

    return " ".join(
        value.strip().lower().split()
    )


# ============================================================
# COLLECT SKILL CANDIDATES
# ============================================================

def _collect_candidates(sections):
    """
    Collect raw skill candidates from all relevant sections.

    Dedicated Skills section
        ↓
    skill_list_splitter.py

    Other sections
        ↓
    skill_extractor_from_section.py
    """

    candidates = []

    if not isinstance(sections, dict):
        return candidates

    for section_name, section_block in sections.items():

        # ----------------------------------------------------
        # Normalize section name
        # ----------------------------------------------------

        section_name = str(
            section_name
        ).strip().lower()

        # ----------------------------------------------------
        # Ignore sections that should not produce
        # technical skills
        # ----------------------------------------------------

        if section_name in IGNORED_SECTIONS:
            continue

        # ----------------------------------------------------
        # Ignore sections that are not configured as
        # skill sources
        # ----------------------------------------------------

        if section_name not in SKILL_SOURCE_SECTIONS:
            continue

        # ====================================================
        # DEDICATED SKILLS SECTION
        # ====================================================

        if section_name == "skills":

            lines = _flatten_section(
                section_block
            )

            raw_skills = split_skill_line(
                lines
            )

            for skill in raw_skills:

                if not isinstance(skill, str):
                    continue

                skill = skill.strip()

                if not skill:
                    continue

                candidates.append({
                    "skill": skill,

                    "source_section": "skills",

                    "source_text": skill,

                    "extraction_method": (
                        "skills_section"
                    ),
                })

        # ====================================================
        # PROSE / OTHER RESUME SECTIONS
        # ====================================================

        else:

            section_candidates = (
                extract_skills_from_section(
                    section_name=section_name,
                    section_block=section_block,
                )
            )

            if not isinstance(
                section_candidates,
                list
            ):
                continue

            for candidate in section_candidates:

                if not isinstance(
                    candidate,
                    dict
                ):
                    continue

                skill = candidate.get(
                    "skill"
                )

                if not isinstance(
                    skill,
                    str
                ):
                    continue

                skill = skill.strip()

                if not skill:
                    continue

                candidate["skill"] = skill

                # ------------------------------------------------
                # Make sure extraction metadata exists.
                # ------------------------------------------------

                candidate.setdefault(
                    "source_section",
                    section_name,
                )

                candidate.setdefault(
                    "source_text",
                    "",
                )

                candidate.setdefault(
                    "extraction_method",
                    "section_text",
                )

                candidates.append(
                    candidate
                )

    return candidates


# ============================================================
# MERGE SOURCE METADATA
# ============================================================

def _merge_source_metadata(
    existing,
    candidate
):
    """
    Merge source information when the same skill appears
    in multiple resume sections.

    Example:

        Python → Skills
        Python → Experience
        Python → Projects

    The final skill should retain all three sources.
    """

    if not isinstance(
        existing,
        dict
    ):
        return

    if not isinstance(
        candidate,
        dict
    ):
        return

    # --------------------------------------------------------
    # SOURCE SECTIONS
    # --------------------------------------------------------

    existing_sections = existing.get(
        "source_sections",
        [],
    )

    candidate_sections = candidate.get(
        "source_sections",
        [],
    )

    if not isinstance(
        existing_sections,
        list
    ):
        existing_sections = [
            existing_sections
        ]

    if not isinstance(
        candidate_sections,
        list
    ):
        candidate_sections = [
            candidate_sections
        ]

    # Also include source_section.
    existing_source_section = (
        existing.get("source_section")
    )

    candidate_source_section = (
        candidate.get("source_section")
    )

    sections = []

    for section in (
        existing_sections
        + candidate_sections
        + [
            existing_source_section,
            candidate_source_section,
        ]
    ):

        if section and section not in sections:
            sections.append(section)

    if sections:
        existing[
            "source_sections"
        ] = sections

    # --------------------------------------------------------
    # SOURCE TEXT
    # --------------------------------------------------------

    existing_text = existing.get(
        "source_text",
        "",
    )

    candidate_text = candidate.get(
        "source_text",
        "",
    )

    if candidate_text:

        if not existing_text:

            existing[
                "source_text"
            ] = candidate_text

        elif (
            candidate_text
            != existing_text
        ):

            # Preserve multiple evidence snippets.
            existing_sources = existing.get(
                "sources",
                [],
            )

            if not isinstance(
                existing_sources,
                list
            ):
                existing_sources = [
                    existing_sources
                ]

            if existing_text not in existing_sources:
                existing_sources.insert(
                    0,
                    existing_text
                )

            if candidate_text not in existing_sources:
                existing_sources.append(
                    candidate_text
                )

            existing[
                "sources"
            ] = existing_sources


# ============================================================
# DEDUPLICATE CANDIDATES
# ============================================================

def _deduplicate_candidates(candidates):
    """
    Deduplicate candidates by skill name while preserving
    source information.

    Example:

        Python
        python
        PYTHON

    becomes one candidate.

    But the source sections are merged.
    """

    if not isinstance(
        candidates,
        list
    ):
        return []

    unique = []

    seen = {}

    for candidate in candidates:

        if not isinstance(
            candidate,
            dict
        ):
            continue

        skill = candidate.get(
            "skill"
        )

        if not isinstance(
            skill,
            str
        ):
            continue

        skill = skill.strip()

        if not skill:
            continue

        candidate["skill"] = skill

        key = _normalize(skill)

        if not key:
            continue

        # ----------------------------------------------------
        # Existing candidate
        # ----------------------------------------------------

        if key in seen:

            existing = seen[key]

            _merge_source_metadata(
                existing,
                candidate
            )

            continue

        # ----------------------------------------------------
        # First occurrence
        # ----------------------------------------------------

        seen[key] = candidate

        unique.append(
            candidate
        )

    return unique


# ============================================================
# FINAL SKILL DEDUPLICATION
# ============================================================

def _deduplicate_final_skills(skills):
    """
    Deduplicate validated/expanded skills.

    Prefer skill_id when available.

    Also merge source information when the same skill occurs
    more than once.
    """

    if not isinstance(
        skills,
        list
    ):
        return []

    final = []

    seen_ids = {}

    seen_names = {}

    for skill in skills:

        if not isinstance(
            skill,
            dict
        ):
            continue

        skill_id = skill.get(
            "skill_id"
        )

        skill_name = skill.get(
            "skill"
        )

        normalized_name = (
            _normalize(skill_name)
            if skill_name
            else ""
        )

        # ----------------------------------------------------
        # Determine duplicate key
        # ----------------------------------------------------

        existing = None

        if skill_id:

            if skill_id in seen_ids:
                existing = seen_ids[
                    skill_id
                ]

        elif normalized_name:

            if normalized_name in seen_names:
                existing = seen_names[
                    normalized_name
                ]

        # ----------------------------------------------------
        # Duplicate found
        # ----------------------------------------------------

        if existing is not None:

            _merge_source_metadata(
                existing,
                skill
            )

            continue

        # ----------------------------------------------------
        # New skill
        # ----------------------------------------------------

        final.append(skill)

        if skill_id:
            seen_ids[
                skill_id
            ] = skill

        if normalized_name:
            seen_names[
                normalized_name
            ] = skill

    return final


# ============================================================
# MAIN SKILL EXTRACTION FUNCTION
# ============================================================

def extract_skill(sections):
    """
    Extract and normalize skills from the complete
    section-detected resume.

    Pipeline:

        sections
            ↓
        collect candidates
            ↓
        deduplicate candidates
            ↓
        spelling resolution
            ↓
        synonym resolution
            ↓
        master skill validation
            ↓
        stack expansion
            ↓
        final deduplication
    """

    # --------------------------------------------------------
    # Validate input
    # --------------------------------------------------------

    if not isinstance(
        sections,
        dict
    ):
        return []

    if not sections:
        return []

    # ========================================================
    # STEP 1 — COLLECT CANDIDATES
    # ========================================================

    candidates = _collect_candidates(
        sections
    )

    if not candidates:
        return []

    # ========================================================
    # STEP 2 — DEDUPLICATE RAW CANDIDATES
    # ========================================================

    candidates = _deduplicate_candidates(
        candidates
    )

    if not candidates:
        return []

    # ========================================================
    # STEP 3 — SPELLING RESOLUTION
    # ========================================================

    candidates = resolve_spelling(
        candidates
    )

    if not candidates:
        return []

    # ========================================================
    # STEP 4 — SYNONYM / ALIAS RESOLUTION
    # ========================================================

    candidates = resolve_synonyms(
        candidates
    )

    if not candidates:
        return []

    # ========================================================
    # STEP 5 — MASTER SKILL VALIDATION
    # ========================================================

    validated_skills = validate_skills(
        candidates
    )

    if not validated_skills:
        return []

    # ========================================================
    # STEP 6 — STACK EXPANSION
    # ========================================================

    expanded_skills = expand_skill_stacks(
        validated_skills
    )

    if not expanded_skills:
        return []

    # ========================================================
    # STEP 7 — FINAL DEDUPLICATION
    # ========================================================

    final_skills = _deduplicate_final_skills(
        expanded_skills
    )

    return final_skills