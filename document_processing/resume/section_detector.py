
"""
Optimized Resume Section Detector

Responsibilities
----------------
1. Detect explicit resume section headings.
2. Detect heading + content on the same line.
3. Keep skill subsections inside the Skills section.
4. Handle merged Education + Certifications headings.
5. Support compound headings.
6. Infer common sections when explicit headings are absent.

Performance improvements
------------------------
- Compile regex patterns once.
- Precompute static heading structures.
- Build custom heading structures once per function call.
- Reuse normalized heading values inside the main loop.
- Avoid rebuilding and sorting compound-heading structures per line.
- Keep fallback inference available.
"""

import re

from document_processing.resume.headings import (
    headings,
    heading_aliases,
)


# ============================================================
# PRECOMPILED REGEX PATTERNS
# ============================================================

RE_SEPARATOR = re.compile(r"[-_/]+")
RE_WHITESPACE = re.compile(r"\s+")

RE_BULLET = re.compile(
    r"^\s*[•●▪◦‣⁃*\\-]+\s*"
)

RE_NUMBERED_BULLET = re.compile(
    r"^\s*(?:\d+[.)]\s*|\d{1,2}\s+-\s+)"
)

RE_TRAILING_COLON = re.compile(r"\s*:\s*$")

RE_SAME_LINE_HEADING = re.compile(
    r"^\s*(.+?)\s*(?::|\||—|–|-)\s*(.+)$",
    re.IGNORECASE,
)

RE_HEADING_PREFIX_CONTENT = re.compile(
    r"^\s*(?::|\||\\|—|–|-)\s*(.+)$"
)

RE_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

RE_DATE_RANGE = re.compile(
    r"""
    \b
    (?:
        jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec
    )?
    \s*
    \d{4}
    \s*
    (?:-|–|—|to)
    \s*
    (?:
        present|
        current|
        (?:
            jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec
        )?
        \s*
        \d{4}
    )
    \b
    """,
    re.IGNORECASE | re.VERBOSE,
)

RE_CERTIFICATION = re.compile(
    r"\b(?:certification|certificate|licensed|license)\b",
    re.IGNORECASE,
)

RE_CERTIFICATION_RECORD = re.compile(
    r"\b(?:certification|certificate|certified|"
    r"fundamentals|essentials|course|training|"
    r"professional development)\b",
    re.IGNORECASE,
)

RE_EDUCATION_RECORD = re.compile(
    r"""
    \b(
        b\.?\s*tech|
        b\.?\s*e|
        b\.?\s*sc|
        b\.?\s*com|
        b\.?\s*ca|
        b\.?\s*a|
        m\.?\s*tech|
        m\.?\s*e|
        m\.?\s*sc|
        m\.?\s*com|
        m\.?\s*ca|
        m\.?\s*a|
        mba|
        mca|
        bca|
        bba|
        phd|
        bachelor|
        master|
        diploma|
        degree|
        higher\s+secondary|
        secondary\s+school|
        high\s+school|
        university|
        college
    )\b
    """,
    re.IGNORECASE | re.VERBOSE,
)

RE_EXPERIENCE_TITLE = re.compile(
    r"\b(?:engineer|developer|trainee|intern|manager|analyst|designer)\b",
    re.IGNORECASE,
)

RE_SKILL_SEPARATOR = re.compile(r"[,/\\;]")

RE_SKILL_WORD = re.compile(
    r"[A-Za-z][A-Za-z0-9.+#-]*"
)


# ============================================================
# NORMALIZATION HELPERS
# ============================================================

def _normalize_heading_for_map(value):
    """
    Normalize static heading aliases when building lookup maps.
    """
    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    value = value.replace("\u00a0", " ")
    value = RE_SEPARATOR.sub(" ", value)
    value = RE_WHITESPACE.sub(" ", value)

    return value.strip().lower()


def _normalize_heading_value(value):
    """
    Normalize a line for exact heading comparisons.
    """
    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    value = value.replace("\u00a0", " ")
    value = RE_BULLET.sub("", value)
    value = RE_NUMBERED_BULLET.sub("", value)
    value = RE_SEPARATOR.sub(" ", value)
    value = RE_TRAILING_COLON.sub("", value)
    value = RE_WHITESPACE.sub(" ", value)

    return value.strip().lower()


def _normalize_line(value):
    """
    Normalize an input resume line.

    This function is executed once for each non-empty input line.
    """
    if value is None:
        return ""

    value = str(value).strip()

    if not value:
        return ""

    value = value.replace("\u00a0", " ")
    value = RE_BULLET.sub("", value)
    value = RE_NUMBERED_BULLET.sub("", value)
    value = RE_WHITESPACE.sub(" ", value)

    return value.strip()


# ============================================================
# STATIC HEADING MAP
# ============================================================

HEADING_MAP = {}

for alias, canonical in heading_aliases.items():
    normalized_alias = _normalize_heading_for_map(alias)

    if normalized_alias:
        HEADING_MAP[normalized_alias] = canonical


SORTED_HEADINGS = tuple(
    sorted(
        HEADING_MAP.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )
)


NORMALIZED_HEADING_MAP = {
    _normalize_heading_for_map(alias): canonical
    for alias, canonical in HEADING_MAP.items()
    if _normalize_heading_for_map(alias)
}


SORTED_COMPOUND_ALIASES = tuple(
    sorted(
        NORMALIZED_HEADING_MAP,
        key=lambda value: len(value.split()),
        reverse=True,
    )
)


# ============================================================
# SKILL SUBSECTION HEADINGS
# ============================================================

SKILL_SUBSECTION_HEADINGS = {
    "languages",
    "language",
    "backend",
    "frontend",
    "databases",
    "database",
    "libraries",
    "library",
    "frameworks",
    "framework",
    "testing",
    "tools",
    "tool",
    "platforms",
    "cloud",
    "devops",
    "web technologies",
    "programming languages",
    "operating systems",
    "development tools",
    "database skills",
    "web technology",
}


NORMALIZED_SKILL_SUBSECTIONS = frozenset(
    _normalize_heading_for_map(value)
    for value in SKILL_SUBSECTION_HEADINGS
)


# ============================================================
# COMPOUND HEADING CONFIGURATION
# ============================================================

EDUCATION_CERTIFICATION_COMPOUND_HEADINGS = frozenset({
    "education certifications",
    "education certification",
    "educational qualifications certifications",
    "education certificates",
})


# ============================================================
# FALLBACK KNOWN SKILLS
# ============================================================

KNOWN_FALLBACK_SKILLS = frozenset({
    "python",
    "sql",
    "mysql",
    "postgresql",
    "javascript",
    "typescript",
    "html",
    "css",
    "java",
    "c",
    "c++",
    "c#",
    "git",
    "github",
    "django",
    "flask",
    "fastapi",
    "react",
    "angular",
    "vue",
    "node.js",
})


# ============================================================
# EXACT HEADING DETECTOR
# ============================================================

def _canonical_heading(line, heading_map=None):
    """
    Return a canonical section name if the complete line matches
    a known heading.
    """
    if not isinstance(line, str):
        return None

    normalized = _normalize_heading_value(line)

    if not normalized:
        return None

    if heading_map is None:
        heading_map = HEADING_MAP

    return heading_map.get(normalized)


# ============================================================
# HEADING + CONTENT DETECTOR
# ============================================================

def _detect_heading_prefix(line, heading_map=None):
    """
    Detect heading + content on the same line.

    Examples:
        Summary: Python developer
        Skills: Python, Django
        Backend - FastAPI, Django
    """
    if not isinstance(line, str):
        return None, ""

    line = line.strip()

    if not line:
        return None, ""

    if heading_map is None:
        sorted_headings = SORTED_HEADINGS
    else:
        sorted_headings = tuple(
            sorted(
                heading_map.items(),
                key=lambda item: len(item[0]),
                reverse=True,
            )
        )

    line_lower = line.lower()

    for heading, canonical in sorted_headings:
        if not heading or not line_lower.startswith(heading):
            continue

        heading_length = len(heading)

        if len(line) <= heading_length:
            continue

        suffix = line[heading_length:]
        match = RE_HEADING_PREFIX_CONTENT.match(suffix)

        if match:
            content = match.group(1).strip()

            if content:
                return canonical, content

    return None, ""


# ============================================================
# COMPOUND HEADING DETECTOR
# ============================================================

def _detect_compound_headings(
    line,
    heading_map=None,
    *,
    normalized_line=None,
    normalized_map=None,
    sorted_aliases=None,
):
    """
    Detect multiple known headings merged into one line.

    Precomputed normalized maps and aliases can be passed in so
    they are not rebuilt for every input line.
    """
    if not isinstance(line, str):
        return []

    normalized = (
        normalized_line
        if normalized_line is not None
        else _normalize_heading_value(line)
    )

    if not normalized:
        return []

    if normalized_map is None:
        if heading_map is None:
            normalized_map = NORMALIZED_HEADING_MAP
            sorted_aliases = SORTED_COMPOUND_ALIASES
        else:
            normalized_map = {
                _normalize_heading_for_map(alias): canonical
                for alias, canonical in heading_map.items()
                if _normalize_heading_for_map(alias)
            }

            sorted_aliases = tuple(
                sorted(
                    normalized_map,
                    key=lambda value: len(value.split()),
                    reverse=True,
                )
            )

    if sorted_aliases is None:
        sorted_aliases = SORTED_COMPOUND_ALIASES

    # A complete known heading is not a compound heading.
    if normalized in normalized_map:
        return []

    words = normalized.split()

    if len(words) < 2:
        return []

    # Memoization prevents repeated segmentation of the same
    # word position during this one compound-heading check.
    memo = {}

    def segment(position):
        if position == len(words):
            return []

        if position in memo:
            return memo[position]

        for alias in sorted_aliases:
            alias_words = alias.split()
            count = len(alias_words)

            if position + count > len(words):
                continue

            if words[position:position + count] != alias_words:
                continue

            canonical = normalized_map[alias]
            remainder = segment(position + count)

            if remainder is not None:
                result = [canonical] + remainder
                memo[position] = result
                return result

        memo[position] = None
        return None

    result = segment(0)

    if result and len(result) >= 2:
        return result

    return []


# ============================================================
# CERTIFICATION ROW NORMALIZER
# ============================================================

def _normalize_certification_rows(lines):
    """
    Normalize certification rows extracted from PDF/table layouts.
    """
    if not lines:
        return []

    result = []

    for line in lines:
        if not isinstance(line, str):
            continue

        line = RE_WHITESPACE.sub(" ", line.strip())

        if line:
            result.append(line)

    return result


# ============================================================
# EDUCATION RECORD CHECK
# ============================================================

def _is_education_record(line):
    """
    Determine whether a line looks like an education record.
    """
    if not isinstance(line, str):
        return False

    line = line.strip()

    return bool(line and RE_EDUCATION_RECORD.search(line))


# ============================================================
# CERTIFICATION RECORD CHECK
# ============================================================

def _is_certification_record(line):
    """
    Determine whether a line looks like a certification record.
    """
    if not isinstance(line, str):
        return False

    line = line.strip()

    return bool(
        line and RE_CERTIFICATION_RECORD.search(line)
    )


# ============================================================
# FALLBACK SECTION INFERENCE
# ============================================================

def _fallback_infer_sections(text):
    """
    Infer common sections when explicit headings are absent.

    Supported sections:
        education
        experience
        skills
        certifications
    """
    sections = {}

    if not isinstance(text, str):
        return sections

    lines = []

    for raw_line in text.splitlines():
        line = _normalize_line(raw_line)

        if line:
            lines.append(line)

    if not lines:
        return sections

    def add_section_line(section_name, line):
        if not line:
            return

        blocks = sections.setdefault(section_name, [])

        if not blocks:
            blocks.append([])

        blocks[0].append(line)

    # --------------------------------------------------------
    # EDUCATION
    # --------------------------------------------------------

    education_indices = [
        index
        for index, line in enumerate(lines)
        if RE_EDUCATION_RECORD.search(line)
    ]

    if education_indices:
        start = education_indices[0]
        end = start

        while end + 1 < len(lines):
            next_line = lines[end + 1]

            if RE_DATE_RANGE.search(next_line):
                break

            if (
                end > start
                and RE_EXPERIENCE_TITLE.search(next_line)
                and not RE_EDUCATION_RECORD.search(next_line)
            ):
                break

            if (
                RE_YEAR.search(next_line)
                or len(next_line.split()) <= 10
            ):
                end += 1
                continue

            break

        for line in lines[start:end + 1]:
            add_section_line("education", line)

    # --------------------------------------------------------
    # EXPERIENCE
    # --------------------------------------------------------

    experience_indices = [
        index
        for index, line in enumerate(lines)
        if RE_DATE_RANGE.search(line)
    ]

    if experience_indices:
        date_index = experience_indices[0]
        start = max(0, date_index - 1)
        end = date_index

        while end + 1 < len(lines):
            next_line = lines[end + 1]

            if RE_EDUCATION_RECORD.search(next_line):
                break

            if RE_DATE_RANGE.search(next_line):
                break

            if (
                RE_SKILL_SEPARATOR.search(next_line)
                and len(next_line.split()) <= 15
            ):
                break

            end += 1

        for line in lines[start:end + 1]:
            add_section_line("experience", line)

    # --------------------------------------------------------
    # SKILLS
    # --------------------------------------------------------

    skill_candidates = []

    for index, line in enumerate(lines):
        parts = [
            part.strip().lower()
            for part in RE_SKILL_SEPARATOR.split(line)
            if part.strip()
        ]

        known_count = sum(
            part in KNOWN_FALLBACK_SKILLS
            for part in parts
        )

        if known_count >= 2:
            skill_candidates.append(index)
            continue

        words = RE_SKILL_WORD.findall(line.lower())

        matching_words = sum(
            word in KNOWN_FALLBACK_SKILLS
            for word in words
        )

        if matching_words >= 3:
            skill_candidates.append(index)

    for index in skill_candidates:
        add_section_line("skills", lines[index])

    # --------------------------------------------------------
    # CERTIFICATIONS
    # --------------------------------------------------------

    certification_lines = [
        line
        for line in lines
        if RE_CERTIFICATION.search(line)
    ]

    if certification_lines:
        sections["certifications"] = [
            _normalize_certification_rows(certification_lines)
        ]

    return {
        section_name: blocks
        for section_name, blocks in sections.items()
        if blocks and any(blocks)
    }


# ============================================================
# SKILL SUBSECTION CHECK
# ============================================================

def _is_skill_subsection(
    line,
    canonical,
    current_section,
    normalized_line=None,
):
    """
    Determine whether a heading should remain inside Skills.
    """
    if current_section != "skills":
        return False

    if not isinstance(line, str):
        return False

    normalized = (
        normalized_line
        if normalized_line is not None
        else _normalize_heading_value(line)
    )

    if not normalized:
        return False

    # Exact subsection.
    if normalized in NORMALIZED_SKILL_SUBSECTIONS:
        return True

    # Same-line subsection, such as 'Backend: FastAPI, Django'.
    match = RE_SAME_LINE_HEADING.match(line)

    if match:
        subsection_heading = _normalize_heading_for_map(
            match.group(1)
        )

        if subsection_heading in NORMALIZED_SKILL_SUBSECTIONS:
            return True

    # Canonical fallback.
    if isinstance(canonical, str):
        canonical_normalized = _normalize_heading_for_map(
            canonical
        )

        if canonical_normalized in NORMALIZED_SKILL_SUBSECTIONS:
            return True

    return False


# ============================================================
# BUILD ACTIVE HEADING MAP
# ============================================================

def _build_active_heading_map(headings_override):
    """
    Build the active heading map once per detect_sections() call.
    """
    if not headings_override:
        return HEADING_MAP

    active_map = HEADING_MAP.copy()

    for heading in headings_override:
        normalized = _normalize_heading_value(heading)

        if not normalized:
            continue

        active_map[normalized] = active_map.get(
            normalized,
            normalized,
        )

    return active_map


# ============================================================
# MAIN SECTION DETECTOR
# ============================================================

def detect_sections(text, headings_override=None):
    """
    Detect resume sections.

    Skills remains a top-level section. Known skill subsections
    such as Languages, Backend, Databases, Testing and Tools
    remain inside Skills.

    Languages outside Skills can still be a top-level section.

    Merged Education + Certifications headings and fallback
    inference are supported.
    """
    sections = {}

    if not isinstance(text, str) or not text.strip():
        return sections

    current_section = None
    compound_section_mode = None

    # --------------------------------------------------------
    # Build heading structures once per function call.
    # --------------------------------------------------------

    active_heading_map = _build_active_heading_map(
        headings_override
    )

    if headings_override:
        sorted_headings = tuple(
            sorted(
                active_heading_map.items(),
                key=lambda item: len(item[0]),
                reverse=True,
            )
        )

        normalized_compound_map = {
            _normalize_heading_for_map(alias): canonical
            for alias, canonical in active_heading_map.items()
            if _normalize_heading_for_map(alias)
        }

        sorted_compound_aliases = tuple(
            sorted(
                normalized_compound_map,
                key=lambda value: len(value.split()),
                reverse=True,
            )
        )
    else:
        sorted_headings = SORTED_HEADINGS
        normalized_compound_map = NORMALIZED_HEADING_MAP
        sorted_compound_aliases = SORTED_COMPOUND_ALIASES

    # --------------------------------------------------------
    # Process input lines.
    # --------------------------------------------------------

    for raw_line in text.splitlines():
        line = _normalize_line(raw_line)

        if not line:
            continue

        # Normalize the line for heading matching once.
        normalized_heading = _normalize_heading_value(line)

        # ====================================================
        # COMPOUND EDUCATION + CERTIFICATIONS MODE
        # ====================================================

        if compound_section_mode == "education_certifications":
            if _is_education_record(line):
                current_section = "education"
                sections["education"][-1].append(line)
                continue

            if _is_certification_record(line):
                current_section = "certifications"
                sections["certifications"][-1].append(line)
                continue

            possible_heading = active_heading_map.get(
                normalized_heading
            )

            if possible_heading:
                compound_section_mode = None
            else:
                if current_section:
                    sections[current_section][-1].append(line)
                    continue

        # ====================================================
        # COMPOUND HEADING
        # ====================================================

        compound_headings = _detect_compound_headings(
            line,
            normalized_line=normalized_heading,
            normalized_map=normalized_compound_map,
            sorted_aliases=sorted_compound_aliases,
        )

        if compound_headings:
            normalized_compound = normalized_heading

            # Special Education + Certifications case.
            if (
                normalized_compound
                in EDUCATION_CERTIFICATION_COMPOUND_HEADINGS
            ):
                sections.setdefault("education", []).append([])
                sections.setdefault("certifications", []).append([])

                compound_section_mode = "education_certifications"
                current_section = "education"
                continue

            # Generic compound heading.
            for compound_canonical in compound_headings:
                if (
                    compound_canonical
                    in NORMALIZED_SKILL_SUBSECTIONS
                    and current_section == "skills"
                ):
                    continue

                current_section = compound_canonical

                sections.setdefault(
                    current_section,
                    [],
                ).append([])

            compound_section_mode = None
            continue

        # ====================================================
        # EXACT HEADING
        # ====================================================

        canonical = active_heading_map.get(normalized_heading)

        if (
            canonical == "certifications"
            and normalized_heading == "professional certification"
            and current_section == "certifications"
        ):
            canonical = None

        if canonical:
            if _is_skill_subsection(
                line=line,
                canonical=canonical,
                current_section=current_section,
                normalized_line=normalized_heading,
            ):
                if current_section:
                    sections[current_section][-1].append(line)

                continue

            current_section = canonical

            sections.setdefault(
                current_section,
                [],
            ).append([])

            continue

        # ====================================================
        # HEADING + CONTENT
        # ====================================================

        canonical = None
        remaining = ""
        line_lower = line.lower()

        for heading, heading_canonical in sorted_headings:
            if not line_lower.startswith(heading):
                continue

            heading_length = len(heading)

            if len(line) <= heading_length:
                continue

            suffix = line[heading_length:]
            match = RE_HEADING_PREFIX_CONTENT.match(suffix)

            if match:
                canonical = heading_canonical
                remaining = match.group(1).strip()
                break

        if canonical:
            if _is_skill_subsection(
                line=line,
                canonical=canonical,
                current_section=current_section,
                normalized_line=normalized_heading,
            ):
                if current_section:
                    sections[current_section][-1].append(line)

                continue

            current_section = canonical

            sections.setdefault(
                current_section,
                [],
            ).append([])

            if remaining:
                sections[current_section][-1].append(remaining)

            continue

        # ====================================================
        # NORMAL CONTENT
        # ====================================================

        if current_section:
            sections[current_section][-1].append(line)

    # ========================================================
    # NO EXPLICIT HEADINGS
    # ========================================================

    if not sections:
        return _fallback_infer_sections(text)

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
                if isinstance(line, str) and line.strip()
            ]

            if cleaned_block:
                cleaned_blocks.append(cleaned_block)

        if not cleaned_blocks:
            continue

        if section_name == "certifications":
            cleaned_blocks = [
                _normalize_certification_rows(block)
                for block in cleaned_blocks
            ]

        cleaned_sections[section_name] = cleaned_blocks

    return cleaned_sections


# ============================================================
# LOCAL TESTS
# ============================================================

if __name__ == "__main__":
    from pprint import pprint

    test_text = """
    Summary
    Entry-level Python developer.

    Skills
    Languages
    Python, SQL, JavaScript
    Backend
    FastAPI, Django, Django REST Framework
    Databases
    PostgreSQL, MySQL
    Libraries
    NumPy, Pandas
    Testing
    Pytest
    Tools
    Git, Docker, Postman

    Experience
    Python Backend Developer Intern
    CodeNest Technologies

    Education
    B.Tech in Computer Science and Engineering

    Certifications
    Python Programming Fundamentals

    Projects
    Recruitment ATS API

    Languages
    English
    Malayalam
    """

    print("\n========== STANDARD SECTION TEST ==========\n")
    pprint(detect_sections(test_text, headings_override=headings))

    same_line_test = """
    Summary
    Python backend developer.

    Skills
    Languages: Python, SQL, JavaScript
    Backend: FastAPI, Django
    Databases: PostgreSQL, MySQL
    Libraries: Pandas, NumPy
    Testing: Pytest, unittest
    Tools: Git, Docker, Postman

    Experience
    Python Developer
    """

    print("\n========== SAME-LINE SKILL TEST ==========\n")
    pprint(detect_sections(same_line_test, headings_override=headings))

    compound_test = """
    Summary
    Python developer.

    Experience
    Python Developer
    ABC Technologies

    Projects
    Recruitment ATS API

    EDUCATION CERTIFICATIONS
    B.Tech in Computer Science and Engineering -
    Kerala Institute of Technology - 2020 - 2024
    Higher Secondary - Computer Science -
    Government Higher Secondary School - 2018 - 2020
    Python Programming Fundamentals - SkillForge Academy, 2024
    REST API Development with FastAPI -
    DevPath Learning, 2024
    SQL and PostgreSQL Essentials -
    OpenLearn Labs, 2023
    """

    compound_result = detect_sections(
        compound_test,
        headings_override=headings,
    )

    print("\n========== COMPOUND HEADING TEST ==========\n")
    pprint(compound_result)

    print("\n========== EDUCATION CONTENT ==========\n")
    pprint(compound_result.get("education", []))

    print("\n========== CERTIFICATION CONTENT ==========\n")
    pprint(compound_result.get("certifications", []))