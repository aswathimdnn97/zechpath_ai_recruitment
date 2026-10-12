import re

from document_processing.resume.headings import heading_aliases


# ============================================================
# HEADING MAP
# ============================================================

HEADING_MAP = {
    str(alias).strip().lower(): canonical
    for alias, canonical in heading_aliases.items()
}


# ============================================================
# NORMALIZE HEADING VALUE
# ============================================================

def _normalize_heading_value(value):
    """
    Normalize a possible section heading for exact comparison.

    Examples:
        "CERTIFICATIONS"       -> "certifications"
        "Certificate:"         -> "certificate"
        "Technical-Skills"     -> "technical skills"
        "Professional_Certifications"
                                -> "professional certifications"
    """

    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    # Replace non-breaking spaces
    value = value.replace(
        "\u00a0",
        " "
    )

    # Normalize separators
    value = re.sub(
        r"[-_/]+",
        " ",
        value
    )

    # Remove trailing colon
    value = re.sub(
        r"\s*:\s*$",
        "",
        value
    )

    # Collapse multiple spaces
    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip().lower()


# ============================================================
# NORMALIZE RESUME TEXT
# ============================================================

def normalize_text(text):
    """
    Normalize resume text.

    Responsibilities:
        1. Remove unnecessary whitespace
        2. Normalize bullet characters
        3. Normalize known section headings
        4. Preserve normal resume content

    IMPORTANT:
        This function does NOT use fuzzy/NLP heading
        detection.

        Section detection is handled by section_detector.py.
    """

    if not isinstance(text, str):
        return ""

    if not text.strip():
        return ""

    normalized_lines = []

    # ========================================================
    # PROCESS EACH LINE
    # ========================================================

    for raw_line in text.splitlines():

        line = raw_line.strip()

        if not line:
            continue

        # ----------------------------------------------------
        # Normalize bullet points
        # ----------------------------------------------------

        line = re.sub(
            r"^[•●◦▪■‣⁃*-]\s*",
            "",
            line
        )

        line = line.strip()

        if not line:
            continue

        # ----------------------------------------------------
        # Check complete line against known headings
        # ----------------------------------------------------

        normalized_heading = _normalize_heading_value(
            line
        )

        # This phrase is both a valid section heading and a common
        # generic certification title. Keep it intact so the section
        # detector can resolve it using the current section context.
        canonical_heading = (
            None
            if normalized_heading == "professional certification"
            else HEADING_MAP.get(normalized_heading)
        )

        # Some PDF layouts extract the section icon as a single
        # leading letter (for example, "G Skills"). Only treat it
        # as noise when the remaining text is a known heading.
        if canonical_heading is None:
            prefixed_heading = re.fullmatch(
                r"[A-Z]\s+(.+)",
                line,
                re.IGNORECASE,
            )

            if prefixed_heading:
                prefixed_heading_value = (
                    _normalize_heading_value(
                        prefixed_heading.group(1)
                    )
                )
                if (
                    prefixed_heading_value
                    == "professional certification"
                ):
                    line = prefixed_heading.group(1).strip()
                else:
                    canonical_heading = HEADING_MAP.get(
                        prefixed_heading_value
                    )

        if canonical_heading:
            line = canonical_heading

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Do NOT run resolve_heading() here.
        #
        # Normal resume content such as:
        #
        # "Professional Development Program Completed"
        #
        # must remain unchanged.
        # ----------------------------------------------------

        normalized_lines.append(
            line
        )

    return "\n".join(
        normalized_lines
    )
