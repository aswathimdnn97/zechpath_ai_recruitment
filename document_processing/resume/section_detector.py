import re

from document_processing.resume.headings import (
    heading_aliases,
    headings,
)


# ============================================================
# HEADING MAP
# ============================================================

HEADING_MAP = {
    str(alias).strip().lower(): canonical
    for alias, canonical in heading_aliases.items()
}


# ============================================================
# NORMALIZE HEADING
# ============================================================

def _normalize_heading_value(value):
    """
    Normalize a heading for reliable comparison.

    Examples:

        "Technical Skills"        -> "technical skills"
        "TECHNICAL-SKILLS"        -> "technical skills"
        "Certifications :"        -> "certifications"
    """

    if value is None:
        return ""

    value = str(value).strip()

    # Replace non-breaking spaces
    value = value.replace("\u00a0", " ")

    # Remove bullets
    value = re.sub(
        r"^[\s•●▪◦*-]+",
        "",
        value
    )

    # Remove numbering
    value = re.sub(
        r"^\s*\d+\s*[.)-]\s*",
        "",
        value
    )

    # Normalize separators
    value = re.sub(
        r"[-_/]+",
        " ",
        value
    )

    # Normalize colon
    value = re.sub(
        r"\s*:\s*$",
        "",
        value
    )

    # Collapse whitespace
    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip().lower()


# ============================================================
# NORMALIZE INPUT LINE
# ============================================================

def _normalize_line(value):
    """
    Basic normalization for resume text lines.
    """

    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    value = value.replace(
        "\u00a0",
        " "
    )

    # Remove common bullet characters
    value = re.sub(
        r"^\s*[•●▪◦‣⁃*-]\s*",
        "",
        value
    )

    # Remove numbered bullets
    value = re.sub(
        r"^\s*\d+\s*[.)-]\s*",
        "",
        value
    )

    # Collapse whitespace
    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


# ============================================================
# EXACT HEADING DETECTOR
# ============================================================

def _canonical_heading(line):
    """
    Return the canonical section name ONLY when the complete
    line represents a known section heading.

    IMPORTANT:
    This intentionally does NOT use substring matching.

    Therefore:

        "Certifications"
            -> certifications

        "Certificate"
            -> certifications

        "Python / Domain Certification Completed"
            -> None

    The last example is resume content, not a heading.
    """

    if not isinstance(line, str):
        return None

    line = _normalize_line(line)

    if not line:
        return None

    normalized = _normalize_heading_value(
        line
    )

    if not normalized:
        return None

    # --------------------------------------------------------
    # Exact match ONLY
    # --------------------------------------------------------

    return HEADING_MAP.get(
        normalized
    )


# ============================================================
# HEADING + CONTENT DETECTOR
# ============================================================

def _detect_heading_prefix(
    line,
    heading_map=None
):
    """
    Detect a genuine section heading followed by content
    on the same physical line.
    """

    if not isinstance(line, str):
        return None, ""

    line = _normalize_line(line)

    if not line:
        return None, ""

    if heading_map is None:
        heading_map = HEADING_MAP

    sorted_headings = sorted(
        heading_map.items(),
        key=lambda item: len(item[0]),
        reverse=True
    )

    for heading, canonical in sorted_headings:

        if not heading:
            continue

        pattern = re.compile(
            rf"^{re.escape(heading)}"
            rf"\s*(?::|\||—|–|-)\s*(.+)$",
            re.IGNORECASE
        )

        match = pattern.match(line)

        if not match:
            continue

        remaining = match.group(1).strip()

        if not remaining:
            continue

        return canonical, remaining

    return None, ""


# ============================================================
# CERTIFICATION ROW NORMALIZER
# ============================================================

def _normalize_certification_rows(lines):
    """
    Normalize certification rows extracted from PDF/table
    layouts.

    Example:

        Python / Domain Certification Completed

    remains a single logical certification line.

    This function does NOT decide whether something is a
    certification. It only cleans the extracted rows.
    """

    if not lines:
        return []

    result = []

    for line in lines:

        if not isinstance(line, str):
            continue

        line = line.strip()

        if not line:
            continue

        line = re.sub(
            r"\s+",
            " ",
            line
        )

        result.append(
            line
        )

    return result


# ============================================================
# FALLBACK SECTION INFERENCE
# ============================================================

def _fallback_infer_sections(text):
    """
    Conservative fallback used only when no explicit section
    headings were detected.

    Certification detection is intentionally conservative.
    """

    sections = {}

    if not isinstance(text, str):
        return sections

    lines = [
        _normalize_line(line)
        for line in text.splitlines()
        if _normalize_line(line)
    ]

    if not lines:
        return sections

    certification_lines = []

    for line in lines:

        lower = line.lower().strip()

        # ----------------------------------------------------
        # Only classify obvious standalone certification
        # content.
        # ----------------------------------------------------

        if re.search(
            r"\b(certification|certificate|licensed|license)\b",
            lower
        ):

            certification_lines.append(line)

    if certification_lines:

        sections["certifications"] = [
            _normalize_certification_rows(
                certification_lines
            )
        ]

    return sections


# ============================================================
# MAIN SECTION DETECTOR
# ============================================================

def detect_sections(
    text,
    headings_override=None
):
    """
    Detect resume sections.

    Supports:

    1. Normal headings

        CERTIFICATIONS
        Python Certification
        ...

    2. Heading + content on same line

        Certificate Python Certification Completed

    3. Normal content containing heading keywords

        Python / Domain Certification Completed

    The third case must NOT change the current section.
    """

    sections = {}
    current_section = None

    if not isinstance(text, str):
        return sections

    if not text.strip():
        return sections

    print("\n========== RAW TEXT SENT TO SECTION DETECTOR ==========")

    for i, raw_line in enumerate(text.splitlines(), start=1):
        print(i, repr(raw_line))

    print("=======================================================\n")
    # ========================================================
    # ACTIVE HEADING MAP
    # ========================================================

    active_heading_map = HEADING_MAP

    if headings_override:

        temporary_map = {}

        for heading in headings_override:

            normalized = _normalize_heading_value(
                heading
            )

            if normalized:
                temporary_map[
                    normalized
                ] = normalized

        # Existing aliases remain available
        temporary_map.update(
            HEADING_MAP
        )

        active_heading_map = (
            temporary_map
        )

    # ========================================================
    # PROCESS LINES
    # ========================================================

    for raw_line in text.splitlines():

        line = _normalize_line(
            raw_line
        )

        if not line:
            continue

        # ====================================================
        # 1. EXACT HEADING
        # ====================================================

        normalized = _normalize_heading_value(
            line
        )

        canonical = active_heading_map.get(
            normalized
        )

        if canonical:

            current_section = canonical

            sections.setdefault(
                current_section,
                []
            ).append([])

            continue

        # ====================================================
        # 2. HEADING + CONTENT ON SAME LINE
        # ====================================================

        # Use the global HEADING_MAP here because aliases are
        # the canonical source of known section headings.

        canonical, remaining = (
            _detect_heading_prefix(
            line,
            active_heading_map
        )
    )

        if canonical:

            current_section = canonical

            sections.setdefault(
                current_section,
                []
            ).append([])

            if remaining:

                sections[
                    current_section
                ][-1].append(
                    remaining
                )

            continue

        # ====================================================
        # 3. NORMAL CONTENT
        # ====================================================

        if current_section:

            sections[
                current_section
            ][-1].append(
                line
            )

    # ========================================================
    # NO EXPLICIT HEADINGS
    # ========================================================

    if not sections:

        return _fallback_infer_sections(
            text
        )

    # ========================================================
    # CLEAN EMPTY BLOCKS
    # ========================================================

    cleaned_sections = {}

    for section_name, blocks in sections.items():

        cleaned_blocks = []

        for block in blocks:

            if not block:
                continue

            cleaned_block = [
                line.strip()
                for line in block
                if isinstance(line, str)
                and line.strip()
            ]

            if cleaned_block:

                cleaned_blocks.append(
                    cleaned_block
                )

        if cleaned_blocks:

            if section_name == "certifications":

                cleaned_blocks = [
                    _normalize_certification_rows(
                        block
                    )
                    for block in cleaned_blocks
                ]

            cleaned_sections[
                section_name
            ] = cleaned_blocks

    return cleaned_sections

# if __name__ == "__main__":

#     test_headings = [
#     "Summary",
#     "Experience",
#     "Education",
#     "Certificate",
#     "Certifications",
#     "Professional Certifications",
#     "Technical Certifications",
#     "Licenses",
#     "Awards",
#     "Python / Domain Certification Completed",
#     "Professional Development Program Completed",
#     "Workplace Communication Completed",
# ]

#     print("\n========== HEADING TEST ==========")

#     for line in test_headings:

#         print(
#             repr(line),
#             "=>",
#             _canonical_heading(line)
#         )

#         print(
#             "PREFIX =>",
#             _detect_heading_prefix(line)
#         )
# print("\n========== SECTION DETECTOR TEST ==========")

# test_text = """
# Summary
# Recent engineering graduate with practical Java experience.

# Experience
# Backend Intern - ByteCraft Technologies
# Worked with Spring Boot.

# Education
# B.Tech in Electronics and Communication Engineering

# Certifications
# Python / Domain Certification Completed
# Professional Development Program Completed
# Workplace Communication Completed

# Awards
# Best Project Award
# """

# result = detect_sections(test_text)

# from pprint import pprint
# pprint(result)


if __name__ == "__main__":

    test_headings = [
        "Summary",
        "Experience",
        "Education",
        "Certificate",
        "Certifications",
        "Professional Certifications",
        "Technical Certifications",
        "Licenses",
        "Awards",
        "Python / Domain Certification Completed",
        "Professional Development Program Completed",
        "Workplace Communication Completed",
    ]

    print("\n========== HEADING TEST ==========")

    for line in test_headings:

        print(
            repr(line),
            "=>",
            _canonical_heading(line)
        )

        print(
            "PREFIX =>",
            _detect_heading_prefix(line)
        )

    # ========================================================
    # SECTION DETECTOR TEST
    # ========================================================

    print("\n========== SECTION DETECTOR TEST ==========")

    test_text = """
    Summary
    Entry-level software trainee with exposure to Java, Spring Boot and relational databases.

    Experience
    Software Trainee - App Works Academy
    Developed basic Java applications.

    Education
    B.Tech in Electronics and Communication Engineering

    Skills
    Java • Spring Boot • SQL • MySQL • HTML • CSS • Git

    Certifications
    Java / Domain Certification Completed
    Professional Development Program Completed

    Achievements
    Java Project Showcase - 2026
    """

    result = detect_sections(test_text)

    from pprint import pprint

    pprint(result)

    # ========================================================
    # SKILLS CHECK
    # ========================================================

    print("\n========== SKILLS CHECK ==========")

    if "skills" in result:
        print("✅ Skills section detected")

        print(
            "Skills content:",
            result["skills"]
        )

    else:
        print("❌ Skills section NOT detected")