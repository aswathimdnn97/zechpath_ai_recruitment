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
7. Keep university continuation separate so that the
   post-processor can merge it with the preceding degree.
"""

import re


# =========================================================
# DEGREE KEYWORDS
# =========================================================

DEGREE_KEYWORDS = [
    "b.tech",
    "btech",
    "b.e",
    "be ",
    "b.sc",
    "bsc",
    "bachelor",
    "m.tech",
    "mtech",
    "m.e",
    "me ",
    "m.sc",
    "msc",
    "master",
    "mca",
    "mba",
    "phd",
    "doctor of philosophy",
    "associate degree",
    "associate",
    "diploma",
    "computer operator and programming assistant",
    "copa",
]


# =========================================================
# SCHOOL QUALIFICATION KEYWORDS
# =========================================================

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


# =========================================================
# UNIVERSITY KEYWORDS
# =========================================================

UNIVERSITY_KEYWORDS = [
    "university",
    "universit",
    "technological university",
    "technical university",
    "institute of technology",
    "open university",
    "deemed university",
]


# =========================================================
# INSTITUTION KEYWORDS
# =========================================================

INSTITUTION_KEYWORDS = [
    "college",
    "institute",
    "institution",
    "academy",
    "vidyalaya",
    "polytechnic",
    "training institute",
]


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def _normalize_line(line):
    """Normalize whitespace for detection only."""

    if not line:
        return ""

    line = line.replace("\xa0", " ")
    line = re.sub(r"\s+", " ", line)

    return line.strip()


def is_degree_start(line):
    """
    Determine whether a line starts a degree record.
    """

    line = _normalize_line(line)

    if not line:
        return False

    lower = line.lower()

    return any(
        keyword in lower
        for keyword in DEGREE_KEYWORDS
    )


def is_school_start(line):
    """
    Determine whether a line starts a school-level
    education record.
    """

    line = _normalize_line(line)

    if not line:
        return False

    lower = line.lower()

    return any(
        keyword in lower
        for keyword in SCHOOL_KEYWORDS
    )


def is_university_continuation(line):
    """
    Determine whether a line starts a university
    continuation record.

    Example:

        Visvesvaraya Technological University,
        Belgaum, Karnataka, India.

    This is intentionally separate from degree detection.
    """

    line = _normalize_line(line)

    if not line:
        return False

    lower = line.lower()

    return any(
        keyword in lower
        for keyword in UNIVERSITY_KEYWORDS
    )


def is_education_start(line):
    """
    Determine whether a line starts any major education
    record.

    This includes:

        - Degree
        - School qualification
        - University continuation
    """

    return (
        is_degree_start(line)
        or is_school_start(line)
        or is_university_continuation(line)
    )


def is_institution_line(line):
    """
    Detect a line that appears to be an institution/location
    entry in an education section.
    """

    if not line:
        return False

    lower = _normalize_line(line).lower()

    if is_university_continuation(line):
        return True

    if any(
        keyword in lower
        for keyword in INSTITUTION_KEYWORDS
    ):
        return True

    if "," in lower and not is_degree_start(line) and not is_school_start(line):
        return True

    return False


def current_block_is_institution_only(block):
    """
    Detect whether the current block is a pending institution
    record without a degree or school qualification yet.
    """

    if not block:
        return False

    return not any(
        is_degree_start(line)
        or is_school_start(line)
        for line in block
    )


def next_line_is_qualification(lines, index):
    """
    Look ahead to see whether a later non-empty line
    represents a qualification.
    """

    for next_line in lines[index + 1 :]:

        next_line = _normalize_line(next_line)

        if not next_line:
            continue

        return (
            is_degree_start(next_line)
            or is_school_start(next_line)
        )

    return False


def is_university_continuation_for_degree(line, current_block):
    """
    Determine whether a university continuation line should
    be treated as part of the current degree block.

    A line that contains both degree information and a university
    name should NOT be treated as a continuation of the previous
    block; it starts a new degree record.
    """

    if not line:
        return False

    if not current_block:
        return False

    return (
        is_university_continuation(line)
        and is_degree_start(current_block[0])
        and not is_degree_start(line)
    )


# =========================================================
# SPLITTER
# =========================================================

def split_education_blocks(education_section):
    """
    Split education section into logical blocks.

    Parameters
    ----------
    education_section : list[str]

    Returns
    -------
    list[list[str]]
    """

    if not education_section:
        return []

    # -----------------------------------------------------
    # Flatten nested list
    # -----------------------------------------------------

    if (
        isinstance(education_section, list)
        and education_section
        and isinstance(
            education_section[0],
            list
        )
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

    # -----------------------------------------------------
    # Process lines
    # -----------------------------------------------------

    for index, raw_line in enumerate(education_section):

        line = _normalize_line(raw_line)

        if not line:
            continue

        # -------------------------------------------------
        # A new logical education record starts here.
        # -------------------------------------------------

        if is_education_start(line):

            if is_university_continuation_for_degree(
                line,
                current_block
            ):
                current_block.append(line)
                continue

            if current_block_is_institution_only(current_block) and (
                is_degree_start(line)
                or is_school_start(line)
            ):
                current_block.append(line)
                continue

            if current_block:
                blocks.append(
                    current_block
                )

            current_block = [line]

        elif is_institution_line(line) and current_block_is_institution_only(current_block):
            current_block.append(line)

        elif is_institution_line(line) and next_line_is_qualification(education_section, index):
            if current_block:
                blocks.append(current_block)
            current_block = [line]

        else:

            # Continuation line
            if current_block:
                current_block.append(line)

            else:
                # Ignore orphan lines before first education
                # record rather than creating an invalid block.
                continue

    # -----------------------------------------------------
    # Add final block
    # -----------------------------------------------------

    if current_block:
        blocks.append(current_block)

    return blocks


# =========================================================
# TESTING
# =========================================================

if __name__ == "__main__":

    education = [

        "2012-2016 Bachelor of Engineering (B.E), "
        "P.E.S Institute of Technology, "
        "Bangalore South Campus, India.",

        "Visvesvaraya Technological University, "
        "Belgaum, Karnataka, India.",

        "Computer Science and Engineering",

        "Aggregate Score : 64.2",

        "2011-2012 All India Senior School Certificate Exam, "
        "Kendriya Vidyalaya Kalpetta, Kerala, India.",

        "Central Board of Secondary Education",

        "Marks Obtained - 85.5",

        "2000-2010 All India Secondary School Examination, "
        "Kendriya Vidyalaya Kalpetta, Kerala, India.",

        "Central Board of Secondary Education",

        "Marks Obtained - 9.4 CGPA",
    ]

    result = split_education_blocks(
        education
    )

    for i, block in enumerate(
        result,
        start=1
    ):

        print(
            f"\nBlock {i}"
        )

        for line in block:
            print(line)