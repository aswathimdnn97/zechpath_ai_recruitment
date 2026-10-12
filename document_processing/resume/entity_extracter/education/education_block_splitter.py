"""
education_block_splitter.py

Responsibilities
----------------
1. Split education section into logical education blocks.
2. Detect degree records.
3. Detect school qualification records.
4. Detect university continuation records.
5. Preserve line order.
6. Ignore empty lines.
7. Keep university continuation with the preceding degree.
8. Keep institution-before-degree records together.
"""

import re


# ============================================================
# DEGREE KEYWORDS
# ============================================================

DEGREE_KEYWORDS = [
    # Engineering
    "b.tech",
    "btech",
    "b.e.",
    "b.e",
    "be ",
    "bachelor of technology",
    "bachelor of engineering",
    "m.tech",
    "mtech",
    "m.e.",
    "m.e",
    "me ",
    "master of technology",
    "master of engineering",

    # Science
    "b.sc.",
    "b.sc",
    "bsc",
    "bachelor of science",
    "m.sc.",
    "m.sc",
    "msc",
    "master of science",

    # Commerce
    "b.com.",
    "b.com",
    "bcom",
    "bachelor of commerce",
    "m.com.",
    "m.com",
    "mcom",
    "master of commerce",

    # Computer Applications
    "b.c.a.",
    "b.c.a",
    "bca",
    "bachelor of computer applications",
    "m.c.a.",
    "m.c.a",
    "mca",
    "master of computer applications",

    # Management
    "b.b.a.",
    "b.b.a",
    "bba",
    "bachelor of business administration",
    "b.m.s.",
    "b.m.s",
    "bms",
    "bachelor of management studies",
    "m.b.a.",
    "m.b.a",
    "mba",
    "master of business administration",

    # Arts
    "b.a.",
    "b.a",
    "ba ",
    "bachelor of arts",
    "m.a.",
    "m.a",
    "ma ",
    "master of arts",

    # Pharmacy
    "b.pharm.",
    "b.pharm",
    "bpharm",
    "bachelor of pharmacy",
    "m.pharm.",
    "m.pharm",
    "mpharm",
    "master of pharmacy",

    # Architecture / Design
    "b.arch.",
    "b.arch",
    "barch",
    "bachelor of architecture",
    "b.des.",
    "b.des",
    "bdes",
    "bachelor of design",

    # Fine Arts
    "b.f.a.",
    "b.f.a",
    "bfa",
    "bachelor of fine arts",

    # Law
    "l.l.b.",
    "l.l.b",
    "llb",
    "bachelor of laws",

    # Social Work
    "b.s.w.",
    "b.s.w",
    "bsw",
    "bachelor of social work",

    # Library Science
    "b.l.i.s.",
    "b.l.i.s",
    "blis",
    "bachelor of library and information science",

    # Hotel Management
    "b.h.m.",
    "b.h.m",
    "bhm",
    "bachelor of hotel management",

    # Journalism
    "b.j.m.c.",
    "b.j.m.c",
    "bjmc",
    "bachelor of journalism and mass communication",

    # Medical
    "m.b.b.s.",
    "m.b.b.s",
    "mbbs",
    "bachelor of medicine and bachelor of surgery",
    "b.d.s.",
    "b.d.s",
    "bds",
    "bachelor of dental surgery",
    "b.p.t.",
    "b.p.t",
    "bpt",
    "bachelor of physiotherapy",

    # HR
    "b.h.r.m.",
    "b.h.r.m",
    "bhrm",
    "bachelor of human resource management",

    # Travel / Tourism
    "b.t.t.m.",
    "b.t.t.m",
    "bttm",
    "bachelor of travel and tourism management",

    # General
    "bachelor",
    "master",

    # Doctorate
    "ph.d.",
    "ph.d",
    "phd",
    "doctor of philosophy",

    # Other
    "associate degree",
    "associate",
    "diploma",
    "computer operator and programming assistant",
    "copa",
]


# ============================================================
# SCHOOL QUALIFICATION KEYWORDS
# ============================================================

SCHOOL_KEYWORDS = [
    "all india senior school certificate",
    "senior school certificate",
    "senior secondary",
    "higher secondary",
    "higher secondary certificate",
    "class xii",
    "class 12",
    "12th",
    "intermediate",
    "xii",
    "all india secondary school examination",
    "secondary school examination",
    "secondary school",
    "secondary examination",
    "class x",
    "class 10",
    "10th",
]


# ============================================================
# UNIVERSITY KEYWORDS
# ============================================================

UNIVERSITY_KEYWORDS = [
    "university",
    "universit",
    "technological university",
    "technical university",
    "open university",
    "deemed university",
]


# ============================================================
# INSTITUTION KEYWORDS
# ============================================================

INSTITUTION_KEYWORDS = [
    "college",
    "institute",
    "institution",
    "school",
    "academy",
    "vidyalaya",
    "polytechnic",
    "training institute",
]


# ============================================================
# NORMALIZATION
# ============================================================

def _normalize_line(line):
    """Normalize whitespace for detection."""

    if not isinstance(line, str):
        return ""

    line = line.replace("\xa0", " ")
    line = re.sub(r"\s+", " ", line)

    return line.strip()


# ============================================================
# DEGREE DETECTION
# ============================================================

def is_degree_start(line):
    """
    Determine whether a line contains a degree qualification.
    """

    line = _normalize_line(line)

    if not line:
        return False

    lower = line.lower()

    return any(
        keyword in lower
        for keyword in DEGREE_KEYWORDS
    )


# ============================================================
# SCHOOL DETECTION
# ============================================================

def is_school_start(line):
    """
    Detect school / secondary education qualification.
    """

    line = _normalize_line(line)

    if not line:
        return False

    normalized = re.sub(
        r"^\s*(?:19|20)\d{2}\s*[-–—]\s*(?:19|20)?\d{2}\s*",
        "",
        line,
        flags=re.IGNORECASE,
    )

    normalized = normalized.lower()

    return any(
        keyword in normalized
        for keyword in SCHOOL_KEYWORDS
    )


# ============================================================
# UNIVERSITY DETECTION
# ============================================================

def is_university_continuation(line):
    """
    Detect a university continuation line.

    The detailed university detection is handled by
    university_extractor.py. This function is only used by
    the education block splitter.
    """

    line = _normalize_line(line)

    if not line:
        return False

    lower = line.lower()

    return any(
        keyword in lower
        for keyword in UNIVERSITY_KEYWORDS
    )


# ============================================================
# EDUCATION START
# ============================================================

def is_education_start(line):
    return (
        is_degree_start(line)
        or is_school_start(line)
        or is_university_continuation(line)
    )


# ============================================================
# INSTITUTION LINE
# ============================================================

def is_institution_line(line):
    """
    Detect an institution-like line.
    """

    line = _normalize_line(line)

    if not line:
        return False

    lower = line.lower()

    if is_university_continuation(line):
        return True

    if any(
        keyword in lower
        for keyword in INSTITUTION_KEYWORDS
    ):
        return True

    # A comma-separated location line is often an institution.
    if (
        "," in line
        and not is_degree_start(line)
        and not is_school_start(line)
    ):
        return True

    return False


# ============================================================
# INSTITUTION-ONLY BLOCK
# ============================================================

def current_block_is_institution_only(block):
    """
    True when block does not yet contain a degree/school
    qualification.
    """

    if not block:
        return False

    return not any(
        is_degree_start(line)
        or is_school_start(line)
        for line in block
    )


# ============================================================
# NEXT QUALIFICATION
# ============================================================

def next_line_is_qualification(lines, index):
    """
    Determine whether the next meaningful line starts a
    qualification.
    """

    for next_index in range(index + 1, len(lines)):

        next_line = _normalize_line(
            lines[next_index]
        )

        if not next_line:
            continue

        return (
            is_degree_start(next_line)
            or is_school_start(next_line)
        )

    return False


# ============================================================
# UNIVERSITY CONTINUATION FOR DEGREE
# ============================================================

def is_university_continuation_for_degree(
    line,
    current_block,
):
    """
    University continuation belongs to an existing degree
    when the current block already starts with a degree.
    """

    if not line or not current_block:
        return False

    return (
        is_university_continuation(line)
        and is_degree_start(current_block[0])
        and not is_degree_start(line)
    )


# ============================================================
# SCHOOL INSTITUTION CONTINUATION
# ============================================================

def is_institution_continuation_for_school(
    line,
    current_block,
):
    """
    Determine whether a school institution line belongs to
    the current school qualification.
    """

    if not line or not current_block:
        return False

    if not is_school_start(current_block[0]):
        return False

    normalized = _normalize_line(line).lower()

    normalized_without_date = re.sub(
        r"^\s*(?:19|20)\d{2}\s*[-–—]\s*(?:19|20)?\d{2}\s*",
        "",
        normalized,
    ).strip()

    explicit_school_qualifications = [
        "all india senior school certificate",
        "senior school certificate",
        "all india secondary school examination",
        "secondary school examination",
        "secondary examination",
    ]

    if any(
        normalized_without_date.startswith(prefix)
        for prefix in explicit_school_qualifications
    ):
        return False

    return any(
        keyword in normalized
        for keyword in [
            "school",
            "vidyalaya",
            "college",
            "institute",
            "academy",
            "polytechnic",
        ]
    )


# ============================================================
# SPLITTER
# ============================================================

def split_education_blocks(education_section):
    """
    Split education section into logical education blocks.
    """

    if not education_section:
        return []

    # Flatten nested lists.
    if (
        isinstance(education_section, list)
        and education_section
        and isinstance(education_section[0], list)
    ):
        flattened = []

        for item in education_section:
            if isinstance(item, list):
                flattened.extend(item)
            else:
                flattened.append(item)

        education_section = flattened

    blocks = []
    current_block = []

    for index, raw_line in enumerate(education_section):

        line = _normalize_line(raw_line)

        if not line:
            continue

        # ----------------------------------------------------
        # Qualification / university start
        # ----------------------------------------------------

        if is_education_start(line):

            # School institution continuation.
            if is_institution_continuation_for_school(
                line,
                current_block,
            ):
                current_block.append(line)
                continue

            # University continuation.
            if is_university_continuation_for_degree(
                line,
                current_block,
            ):
                current_block.append(line)
                continue

            # Institution before qualification:
            #
            # ABC College
            # B.Tech Computer Science
            #
            # Keep them in the same block.
            if (
                current_block_is_institution_only(current_block)
                and (
                    is_degree_start(line)
                    or is_school_start(line)
                )
            ):
                current_block.append(line)
                continue

            # Otherwise start a new education record.
            if current_block:
                blocks.append(current_block)

            current_block = [line]
            continue

        # ----------------------------------------------------
        # Institution line
        # ----------------------------------------------------

        if is_institution_line(line):

            if current_block_is_institution_only(
                current_block
            ):
                current_block.append(line)
                continue

            # Institution before next qualification.
            if (
                current_block
                and next_line_is_qualification(
                    education_section,
                    index,
                )
            ):
                blocks.append(current_block)
                current_block = [line]
                continue

            # Otherwise it belongs to current block.
            if current_block:
                current_block.append(line)
            else:
                current_block = [line]

            continue

        # ----------------------------------------------------
        # Ordinary continuation
        # ----------------------------------------------------

        if current_block:
            current_block.append(line)

    if current_block:
        blocks.append(current_block)

    return blocks


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    education = [
        "B.Tech in Computer Science and Engineering - Kerala Institute of Technology (2020 - 2024)",
        "Computer Science and Engineering",
        "Higher Secondary - Computer Science - Government Higher Secondary School (2018 - 2020)",
        "Central Board of Secondary Education",
    ]

    result = split_education_blocks(education)

    for index, block in enumerate(result, start=1):
        print(f"\nBlock {index}")

        for line in block:
            print("  ", line)
