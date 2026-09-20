"""
master_skill_validator.py

Responsibilities
----------------
1. Load master_skill_dictionary.json
2. Validate extracted skill candidates
3. Perform exact matching
4. Perform fuzzy matching
5. Calculate confidence score
6. Return only valid master skills
7. Reject unknown/non-skill text
8. Preserve extraction metadata
9. Merge metadata when the same skill appears in
   multiple resume sections

Supported input
---------------

Simple format:

    [
        "Python",
        "FastAPI",
        "PostgreSQL"
    ]

Structured format:

    [
        {
            "skill": "Python",
            "matched_by": "skills_section",
            "source_section": "skills",
            "source_text": "Python, FastAPI, Django"
        }
    ]

The structured format is preferred for the new
resume skill extraction pipeline.

Pipeline position
-----------------

skill_list_splitter.py
        +
skill_extractor_from_section.py
        ↓
candidate skills
        ↓
spelling_resolver.py
        ↓
synonym_resolver.py
        ↓
master_skill_validator.py
        ↓
validated master skills
        ↓
stack_resolver.py
"""


import json
from pathlib import Path

from rapidfuzz import process, fuzz


# ============================================================
# PROJECT ROOT
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[4]


# ============================================================
# MASTER SKILL FILE
# ============================================================

MASTER_SKILL_FILE = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "skills"
    / "master_skill_dictionary.json"
)


# ============================================================
# LOAD MASTER SKILL DICTIONARY
# ============================================================

def load_master_skill_dictionary():
    """
    Load active skills from master_skill_dictionary.json.

    Returns
    -------
    list[dict]

        Only active and valid master skill records.
    """

    if not MASTER_SKILL_FILE.exists():
        raise FileNotFoundError(
            "Master skill dictionary not found: "
            f"{MASTER_SKILL_FILE}"
        )

    with open(
        MASTER_SKILL_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "master_skill_dictionary.json "
            "must contain a list of skills."
        )

    active_skills = []

    for skill in data:

        if not isinstance(skill, dict):
            continue

        # ----------------------------------------------------
        # Only active skills are allowed.
        # ----------------------------------------------------

        if skill.get("status") != "active":
            continue

        # ----------------------------------------------------
        # Required master fields.
        # ----------------------------------------------------

        if not skill.get("skill_id"):
            continue

        if not skill.get("name"):
            continue

        active_skills.append(
            skill
        )

    return active_skills


# ============================================================
# NORMALIZE SKILL TEXT
# ============================================================

def normalize_skill_text(skill):
    """
    Normalize skill text before matching.

    Examples
    --------
    "  Python   "
        -> "python"

    "REST APIs"
        -> "rest apis"

    "  Machine   Learning  "
        -> "machine learning"
    """

    if not isinstance(skill, str):
        return ""

    return " ".join(
        skill.strip().split()
    ).lower()


# ============================================================
# BUILD EXACT LOOKUP
# ============================================================

def build_exact_lookup(master_skills):
    """
    Build normalized lookup.

    Example
    -------

        {
            "python": {
                "skill_id": "...",
                "name": "Python",
                ...
            }
        }
    """

    lookup = {}

    for skill in master_skills:

        name = skill.get(
            "name"
        )

        normalized_name = normalize_skill_text(
            name
        )

        if normalized_name:

            lookup[
                normalized_name
            ] = skill

    return lookup


# ============================================================
# EXTRACT CANDIDATE NAME
# ============================================================

def _get_candidate_name(candidate):
    """
    Extract skill name from a candidate.

    Supports:

        "Python"

    and:

        {
            "skill": "Python",
            ...
        }

    Returns
    -------
    str
    """

    # --------------------------------------------------------
    # Backward compatibility
    # --------------------------------------------------------

    if isinstance(candidate, str):

        return candidate.strip()

    # --------------------------------------------------------
    # Structured candidate
    # --------------------------------------------------------

    if isinstance(candidate, dict):

        skill_name = candidate.get(
            "skill"
        )

        if isinstance(
            skill_name,
            str
        ):

            return skill_name.strip()

    return ""


# ============================================================
# COPY EXTRACTION METADATA
# ============================================================

def _copy_metadata(
    candidate,
    result,
):
    """
    Preserve extraction metadata.

    The validator must not destroy information produced
    by the extraction stage.

    Possible metadata:

        source_section
        source_sections
        source_text
        sources
        source_skill
        extraction_method
    """

    if not isinstance(
        candidate,
        dict
    ):
        return

    # ========================================================
    # SOURCE SECTION
    # ========================================================

    source_section = candidate.get(
        "source_section"
    )

    if source_section:

        result[
            "source_section"
        ] = source_section

    # ========================================================
    # SOURCE SECTIONS
    # ========================================================

    source_sections = candidate.get(
        "source_sections"
    )

    if (
        isinstance(
            source_sections,
            list
        )
        and source_sections
    ):

        result[
            "source_sections"
        ] = list(
            dict.fromkeys(
                str(section).strip()
                for section in source_sections
                if section
            )
        )

    # ========================================================
    # SOURCE TEXT
    # ========================================================

    source_text = candidate.get(
        "source_text"
    )

    if source_text:

        result[
            "source_text"
        ] = source_text

    # ========================================================
    # SOURCES
    # ========================================================

    sources = candidate.get(
        "sources"
    )

    if (
        isinstance(
            sources,
            list
        )
        and sources
    ):

        result[
            "sources"
        ] = sources

    # ========================================================
    # SOURCE SKILL
    # ========================================================

    source_skill = candidate.get(
        "source_skill"
    )

    if source_skill:

        result[
            "source_skill"
        ] = source_skill

    # ========================================================
    # EXTRACTION METHOD
    # ========================================================

    extraction_method = candidate.get(
        "extraction_method"
    )

    if extraction_method:

        result[
            "extraction_method"
        ] = extraction_method


# ============================================================
# CREATE VALIDATED SKILL
# ============================================================

def build_validated_skill(
    skill,
    matched_by,
    confidence,
    candidate=None,
):
    """
    Convert a master dictionary entry into
    an ATS-ready validated skill object.

    IMPORTANT
    ---------
    Master dictionary information is authoritative.

    Extraction metadata is copied from the candidate.
    """

    result = {
        "skill_id": skill.get(
            "skill_id"
        ),

        "skill": skill.get(
            "name"
        ),

        "category": skill.get(
            "category",
            "Unknown"
        ),

        "subcategory": skill.get(
            "subcategory",
            "Unknown"
        ),

        "matched_by": matched_by,

        "confidence": confidence,
    }

    _copy_metadata(
        candidate,
        result
    )

    return result


# ============================================================
# MERGE METADATA
# ============================================================

def _merge_metadata(
    existing,
    candidate,
):
    """
    Merge metadata from a duplicate candidate.

    Example
    -------

    Python appears in:

        skills
        experience
        projects

    Instead of losing that information, keep:

        source_section = "skills"

        source_sections = [
            "skills",
            "experience",
            "projects"
        ]
    """

    if not isinstance(
        candidate,
        dict
    ):
        return

    # ========================================================
    # SOURCE SECTIONS
    # ========================================================

    sections = []

    # Existing source_section
    existing_section = existing.get(
        "source_section"
    )

    if existing_section:
        sections.append(
            existing_section
        )

    # Existing source_sections
    existing_sections = existing.get(
        "source_sections"
    )

    if isinstance(
        existing_sections,
        list
    ):

        sections.extend(
            existing_sections
        )

    # New source_section
    new_section = candidate.get(
        "source_section"
    )

    if new_section:
        sections.append(
            new_section
        )

    # New source_sections
    new_sections = candidate.get(
        "source_sections"
    )

    if isinstance(
        new_sections,
        list
    ):

        sections.extend(
            new_sections
        )

    # Remove duplicates while preserving order.
    sections = list(
        dict.fromkeys(
            str(section).strip()
            for section in sections
            if section
        )
    )

    if sections:

        # First source remains the primary source.
        existing[
            "source_section"
        ] = sections[0]

        existing[
            "source_sections"
        ] = sections

    # ========================================================
    # SOURCE TEXTS
    # ========================================================

    source_texts = []

    # Existing source_text
    existing_text = existing.get(
        "source_text"
    )

    if existing_text:
        source_texts.append(
            existing_text
        )

    # Existing sources
    existing_sources = existing.get(
        "sources"
    )

    if isinstance(
        existing_sources,
        list
    ):

        source_texts.extend(
            source.get("source_text", "")
            for source in existing_sources
            if isinstance(source, dict)
        )

    # New source text
    new_text = candidate.get(
        "source_text"
    )

    if new_text:
        source_texts.append(
            new_text
        )

    # Remove duplicate/empty texts.
    source_texts = list(
        dict.fromkeys(
            text.strip()
            for text in source_texts
            if isinstance(text, str)
            and text.strip()
        )
    )

    if source_texts:

        # Preserve first source text for backward compatibility.
        existing[
            "source_text"
        ] = source_texts[0]

    # ========================================================
    # STRUCTURED SOURCES
    # ========================================================

    merged_sources = []

    if isinstance(
        existing.get("sources"),
        list
    ):

        merged_sources.extend(
            existing["sources"]
        )

    # Add current candidate as a source.
    candidate_source = {}

    if candidate.get(
        "source_section"
    ):

        candidate_source[
            "source_section"
        ] = candidate[
            "source_section"
        ]

    if candidate.get(
        "source_text"
    ):

        candidate_source[
            "source_text"
        ] = candidate[
            "source_text"
        ]

    if candidate.get(
        "source_skill"
    ):

        candidate_source[
            "source_skill"
        ] = candidate[
            "source_skill"
        ]

    if candidate_source:

        merged_sources.append(
            candidate_source
        )

    # Deduplicate structured sources.
    unique_sources = []

    seen_sources = set()

    for source in merged_sources:

        if not isinstance(
            source,
            dict
        ):
            continue

        key = (
            source.get(
                "source_section",
                ""
            ),
            source.get(
                "source_text",
                ""
            ),
            source.get(
                "source_skill",
                ""
            ),
        )

        if key in seen_sources:
            continue

        seen_sources.add(
            key
        )

        unique_sources.append(
            source
        )

    if unique_sources:

        existing[
            "sources"
        ] = unique_sources


# ============================================================
# VALIDATE THRESHOLD
# ============================================================

def _validate_threshold(threshold):
    """
    Validate fuzzy matching threshold.
    """

    if not isinstance(
        threshold,
        (int, float)
    ):

        raise TypeError(
            "threshold must be a number."
        )

    if threshold < 0 or threshold > 100:

        raise ValueError(
            "threshold must be between 0 and 100."
        )


# ============================================================
# VALIDATE SKILLS
# ============================================================

def validate_skills(
    candidate_skills,
    threshold=90,
):
    """
    Validate extracted skills against the
    master skill dictionary.

    Supports:

        list[str]

    and:

        list[dict]

    Unknown candidates are discarded.

    Parameters
    ----------
    candidate_skills : list[str] | list[dict]

    threshold : int | float
        Minimum fuzzy matching score.

    Returns
    -------
    list[dict]
        Validated master skill objects.
    """

    # ========================================================
    # EMPTY INPUT
    # ========================================================

    if not candidate_skills:

        return []

    # ========================================================
    # INPUT VALIDATION
    # ========================================================

    if not isinstance(
        candidate_skills,
        (list, tuple, set)
    ):

        raise TypeError(
            "candidate_skills must be a list, "
            "tuple, or set."
        )

    _validate_threshold(
        threshold
    )

    # ========================================================
    # LOAD MASTER SKILLS
    # ========================================================

    master_skills = (
        load_master_skill_dictionary()
    )

    if not master_skills:

        return []

    # ========================================================
    # BUILD EXACT LOOKUP
    # ========================================================

    exact_lookup = build_exact_lookup(
        master_skills
    )

    # ========================================================
    # CANONICAL SKILL NAMES
    # ========================================================

    skill_names = [
        skill["name"]
        for skill in master_skills
    ]

    # ========================================================
    # RESULT STORAGE
    # ========================================================

    validated = []

    # Map skill_id -> validated object.
    #
    # This allows duplicate skills to have their metadata
    # merged instead of simply being discarded.
    validated_by_id = {}

    # ========================================================
    # PROCESS CANDIDATES
    # ========================================================

    for candidate in candidate_skills:

        # ----------------------------------------------------
        # Extract candidate name.
        # ----------------------------------------------------

        candidate_name = (
            _get_candidate_name(
                candidate
            )
        )

        if not candidate_name:

            continue

        normalized_candidate = (
            normalize_skill_text(
                candidate_name
            )
        )

        if not normalized_candidate:

            continue

        # ====================================================
        # EXACT MATCH
        # ====================================================

        matched_skill = exact_lookup.get(
            normalized_candidate
        )

        if matched_skill:

            skill_id = matched_skill.get(
                "skill_id"
            )

            if not skill_id:

                continue

            # ------------------------------------------------
            # First occurrence.
            # ------------------------------------------------

            if skill_id not in validated_by_id:

                validated_skill = (
                    build_validated_skill(
                        skill=matched_skill,
                        matched_by="exact",
                        confidence=100,
                        candidate=candidate,
                    )
                )

                validated.append(
                    validated_skill
                )

                validated_by_id[
                    skill_id
                ] = validated_skill

            # ------------------------------------------------
            # Duplicate occurrence.
            # Merge source metadata.
            # ------------------------------------------------

            else:

                _merge_metadata(
                    validated_by_id[
                        skill_id
                    ],
                    candidate
                )

            continue

        # ====================================================
        # FUZZY MATCH
        # ====================================================

        fuzzy_result = process.extractOne(
            candidate_name,
            skill_names,
            scorer=fuzz.WRatio,
        )

        if not fuzzy_result:

            continue

        best_skill_name = fuzzy_result[0]

        score = fuzzy_result[1]

        # ----------------------------------------------------
        # Reject weak fuzzy matches.
        # ----------------------------------------------------

        if score < threshold:

            continue

        # ----------------------------------------------------
        # Find master skill.
        # ----------------------------------------------------

        best_skill = exact_lookup.get(
            normalize_skill_text(
                best_skill_name
            )
        )

        if not best_skill:

            continue

        skill_id = best_skill.get(
            "skill_id"
        )

        if not skill_id:

            continue

        # ----------------------------------------------------
        # First fuzzy occurrence.
        # ----------------------------------------------------

        if skill_id not in validated_by_id:

            validated_skill = (
                build_validated_skill(
                    skill=best_skill,
                    matched_by="fuzzy",
                    confidence=round(score),
                    candidate=candidate,
                )
            )

            validated.append(
                validated_skill
            )

            validated_by_id[
                skill_id
            ] = validated_skill

        # ----------------------------------------------------
        # Duplicate fuzzy/exact occurrence.
        # ----------------------------------------------------

        else:

            _merge_metadata(
                validated_by_id[
                    skill_id
                ],
                candidate
            )

    # ========================================================
    # RETURN
    # ========================================================

    return validated


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    test_skills = [

        # ----------------------------------------------------
        # Simple format
        # ----------------------------------------------------

        "Python",

        # ----------------------------------------------------
        # Structured format
        # ----------------------------------------------------

        {
            "skill": "FastAPI",
            "matched_by": "skills_section",
            "source_section": "skills",
            "source_text": "Python, FastAPI, Django",
        },

        {
            "skill": "PostgreSQL",
            "matched_by": "master_dictionary",
            "source_section": "projects",
            "source_text": (
                "Built an application using PostgreSQL."
            ),
        },

        # ----------------------------------------------------
        # Same skill appearing in another section.
        # ----------------------------------------------------

        {
            "skill": "Python",
            "matched_by": "master_dictionary",
            "source_section": "experience",
            "source_text": (
                "Developed backend services using Python."
            ),
        },

        # ----------------------------------------------------
        # Unknown text.
        # ----------------------------------------------------

        {
            "skill": "Won 4/4 hackathons",
            "source_section": "achievements",
        },
    ]

    result = validate_skills(
        test_skills
    )

    for skill in result:

        print(skill)