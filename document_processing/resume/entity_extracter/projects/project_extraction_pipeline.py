
from document_processing.resume.entity_extracter.projects.project_block_splitter import (
    split_project_blocks,
)

from document_processing.resume.entity_extracter.projects.project_name_extractor import (
    extract_project_name,
)

from document_processing.resume.entity_extracter.projects.project_description_extractor import (
    extract_project_description,
)

from document_processing.resume.entity_extracter.projects.project_technologies_extractor import (
    extract_project_technologies,
)

from document_processing.resume.entity_extracter.projects.project_technology_normalizer import (
    normalize_project_technologies,
)

from document_processing.resume.entity_extracter.projects.project_url_extractor import (
    extract_project_url,
)

from document_processing.common.llm_fallback_service import llm_fallback_service


PROJECT_LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "project_name": {"type": "string"},
        "description": {"type": "string"},
        "technologies": {
            "type": "array",
            "items": {"type": "string"},
        },
        "url": {"type": "string"},
    },
    "required": [
        "project_name",
        "description",
        "technologies",
        "url",
    ],
    "additionalProperties": False,
}


def _block_to_text(block):
    """Convert a project block into readable text for LLM fallback."""

    if isinstance(block, str):
        return block.strip()

    if isinstance(block, (list, tuple)):
        return "\n".join(
            str(line).strip()
            for line in block
            if line is not None and str(line).strip()
        )

    if block is None:
        return ""

    return str(block).strip()


def _clean_text(value):
    """Return a clean non-empty string or an empty string."""

    if not isinstance(value, str):
        return ""

    value = " ".join(value.split())

    if value.lower() in {
        "",
        "none",
        "null",
        "n/a",
        "not available",
        "unknown",
    }:
        return ""

    return value


def _clean_technologies(value):
    """Convert technology output into a normalized list."""

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, (list, tuple, set)):
        return []

    cleaned = []
    seen = set()

    for technology in value:
        technology = _clean_text(technology)

        if not technology:
            continue

        key = technology.casefold()

        if key not in seen:
            seen.add(key)
            cleaned.append(technology)

    return cleaned


def _safe_extract(extractor, block, default=None):
    """Prevent one extractor failure from stopping project parsing."""

    try:
        result = extractor(block)
        return result if result is not None else default
    except Exception:
        return default


def _normalize_technologies(technologies):
    """Use the existing normalizer without breaking the pipeline."""

    technologies = _clean_technologies(technologies)

    if not technologies:
        return []

    try:
        normalized = normalize_project_technologies(technologies)

        if normalized is not None:
            return _clean_technologies(normalized)

    except Exception:
        pass

    # Preserve extracted technologies if normalization fails.
    return technologies


def _llm_project_fallback(block):
    """
    Extract missing project fields using the shared LLM service.

    Returns an empty dictionary if the LLM fails or produces
    an unusable response.
    """

    block_text = _block_to_text(block)

    if not block_text:
        return {}

    prompt_text = (
        "Extract project information from the resume text below.\n"
        "Return only information explicitly supported by the text.\n"
        "Do not invent project names, descriptions, technologies, or URLs.\n"
        "Keep technologies as a list of strings.\n"
        "Use an empty string for unknown text fields and an empty list "
        "for unknown technologies.\n\n"
        f"Resume project text:\n{block_text}"
    )

    try:
        result = llm_fallback_service.extract_json(
            entity_name="project",
            text=prompt_text,
            output_schema=PROJECT_LLM_SCHEMA,
        )

        if not isinstance(result, dict):
            return {}

        return {
            "project_name": _clean_text(
                result.get("project_name")
            ),
            "description": _clean_text(
                result.get("description")
            ),
            "technologies": _clean_technologies(
                result.get("technologies")
            ),
            "url": _clean_text(
                result.get("url")
            ),
        }

    except Exception:
        # Resume parsing must continue if the LLM is unavailable.
        return {}


def extract_projects(section):
    """
    Extract projects using deterministic extractors first,
    then use the LLM only when important fields are missing.

    Output format:
    [
        {
            "project_name": str,
            "description": str,
            "technologies": list,
            "url": str,
        }
    ]
    """

    if not section:
        return []

    try:
        project_blocks = split_project_blocks(section)
    except Exception:
        return []

    if not project_blocks:
        return []

    projects = []
    seen_projects = set()

    for block in project_blocks:
        if not _block_to_text(block):
            continue

        # Step 1: Deterministic extraction.
        project_name = _clean_text(
            _safe_extract(extract_project_name, block, "")
        )

        description = _clean_text(
            _safe_extract(extract_project_description, block, "")
        )

        raw_technologies = _safe_extract(
            extract_project_technologies,
            block,
            [],
        )

        technologies = _normalize_technologies(
            raw_technologies
        )

        url = _clean_text(
            _safe_extract(extract_project_url, block, None)
        ) or None

        
        # Step 2: LLM fallback only for missing fields.
        if not project_name or not description or not technologies:
            llm_data = _llm_project_fallback(block)

            # Fill missing fields only.
            if not project_name:
                project_name = llm_data.get("project_name", "")

            if not description:
                description = llm_data.get("description", "")

            if not technologies:
                technologies = _normalize_technologies(
                    llm_data.get("technologies", [])
                )

            # URL is optional. Use it only if no URL was extracted.
            if not url:
                url = llm_data.get("url") or None

        # Step 3: Clean the final values.
        project_name = _clean_text(project_name)
        description = _clean_text(description)
        technologies = _normalize_technologies(technologies)
        url = _clean_text(url) or None

        # Step 4: Skip only if every meaningful field is empty.
        if not project_name and not description and not technologies:
            continue

        # Step 5: Avoid duplicate projects.
        duplicate_key = (
            project_name.casefold(),
            description.casefold(),
        )

        if duplicate_key in seen_projects:
            continue

        seen_projects.add(duplicate_key)

        # Step 6: Preserve the output schema.
        projects.append({
            "project_name": project_name,
            "description": description,
            "technologies": technologies,
            "url": url,
        })


    return projects
