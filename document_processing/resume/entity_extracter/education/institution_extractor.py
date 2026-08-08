"""
institution_extractor.py

Responsibilities
----------------
1. Extract institution from an education block.
2. Remove dates and degree/qualification prefixes.
3. Remove examination names from school records.
4. Ignore education boards.
5. Clean punctuation and whitespace.
6. Return only the institution name.
"""

import re


# =========================================================
# EDUCATION BOARD PATTERNS
# =========================================================

BOARD_PATTERNS = [

    r"central board of secondary education",
    r"\bcbse\b",

    r"state board",
    r"kerala board",

    r"board of secondary education",

    r"council for the indian school certificate examinations",

    r"\bicse\b",
    r"\bisc\b",
]


# =========================================================
# QUALIFICATION / EXAMINATION PREFIXES
# =========================================================

QUALIFICATION_PREFIX_PATTERNS = [

    r"all india senior school certificate exam",
    r"all india senior school certificate examination",

    r"all india secondary school examination",

    r"senior school certificate exam",
    r"senior school certificate examination",

    r"secondary school examination",

    r"higher secondary examination",
    r"higher secondary certificate",

    r"senior secondary examination",

    r"intermediate examination",
    r"intermediate certificate",
]


# =========================================================
# DEGREE PATTERNS
# =========================================================

DEGREE_PATTERNS = [

    r"bachelor of technology",
    r"bachelor of engineering",

    r"master of technology",
    r"master of engineering",

    r"master of computer applications",
    r"bachelor of computer applications",

    r"bachelor of science",
    r"master of science",

    r"bachelor of arts",
    r"master of arts",

    r"bachelor of commerce",
    r"master of commerce",

    r"\bb\.?\s*tech\b",
    r"\bb\.?\s*e\b",

    r"\bm\.?\s*tech\b",
    r"\bm\.?\s*e\b",

    r"\bm\.?\s*c\.?\s*a\b",
    r"\bb\.?\s*c\.?\s*a\b",

    r"\bm\.?\s*sc\b",
    r"\bb\.?\s*sc\b",

    r"\bm\.?\s*ba\b",
    r"\bb\.?\s*ba\b",

    r"\bm\.?\s*com\b",
    r"\bb\.?\s*com\b",
]


# =========================================================
# INSTITUTION KEYWORDS
# =========================================================

INSTITUTION_KEYWORDS = [

    "university",
    "college",
    "institute",
    "institution",
    "school",
    "academy",
    "vidyalaya",
    "polytechnic",
    "training institute",

]

# =========================================================
# UNIVERSITY KEYWORDS
# =========================================================

UNIVERSITY_KEYWORDS = [

    "university",
    "universit",
    "technological university",
    "technical university",
    "deemed university",
    "institute of technology",
    "open university",

]


# =========================================================
# BASIC CLEANING
# =========================================================

def normalize_spaces(text):
    """
    Normalize whitespace and non-breaking spaces.
    """

    if not text:
        return ""

    text = text.replace("\xa0", " ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


def normalize_commas(text):
    """
    Normalize comma spacing.
    """

    text = re.sub(
        r"\s*,\s*",
        ", ",
        text
    )

    # Remove duplicate commas

    text = re.sub(
        r",\s*,+",
        ", ",
        text
    )

    return text.strip()


# =========================================================
# REMOVE DATE
# =========================================================

def remove_dates(text):
    """
    Remove education date ranges.

    Examples
    --------
    2012-2016
    2011–2012
    2022 - Present
    """

    text = re.sub(
        r"\b\d{4}\s*[-–]\s*(?:\d{4}|present)\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Also handle a single year when it appears
    # before an institution.

    text = re.sub(
        r"^\s*\d{4}\s*[,|:-]?\s*",
        "",
        text
    )

    return text


# =========================================================
# REMOVE DEGREE
# =========================================================

def remove_degree(text):
    """
    Remove degree names and degree abbreviations.
    """

    for pattern in DEGREE_PATTERNS:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE
        )

    # Remove degree abbreviations inside parentheses

    text = re.sub(
        r"\(\s*"
        r"(?:"
        r"B\.?\s*E\.?|"
        r"B\.?\s*Tech\.?|"
        r"M\.?\s*E\.?|"
        r"M\.?\s*Tech\.?|"
        r"B\.?\s*C\.?\s*A\.?|"
        r"M\.?\s*C\.?\s*A\.?"
        r")"
        r"\s*\)",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove empty parentheses

    text = re.sub(
        r"\(\s*\)",
        "",
        text
    )

    return text


# =========================================================
# REMOVE QUALIFICATION / EXAM NAME
# =========================================================

def remove_qualification_prefix(text):
    """
    Remove school examination names.

    Example
    -------
    All India Senior School Certificate Exam,
    Kendriya Vidyalaya Kalpetta, Kerala, India.

    becomes

    Kendriya Vidyalaya Kalpetta, Kerala, India.
    """

    for pattern in QUALIFICATION_PREFIX_PATTERNS:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE
        )

    return text


# =========================================================
# REMOVE LEADING / TRAILING NOISE
# =========================================================

def remove_leading_noise(text):
    """
    Remove punctuation left after cleaning.
    """

    text = re.sub(
        r"^[\s,|:;()\-–]+",
        "",
        text
    )

    text = re.sub(
        r"[\s,|:;()\-–]+$",
        "",
        text
    )

    return text


# =========================================================
# BOARD DETECTION
# =========================================================

def is_board(text):
    """
    Check whether text represents an education board.
    """

    if not text:
        return False

    lower = text.lower()

    return any(
        re.search(
            pattern,
            lower
        )
        for pattern in BOARD_PATTERNS
    )


# =========================================================
# BOARD CLEANING
# =========================================================


def clean_board_name(text):
    """
    Clean board text and normalize punctuation.
    """

    if not text:
        return None

    board = normalize_spaces(text)
    board = remove_leading_noise(board)
    board = normalize_commas(board)
    board = remove_leading_noise(board)
    board = board.strip(" ,.;:-()")

    if not board:
        return None

    return board


def extract_board(block):
    """
    Extract board name from an education block.
    """

    if not block:
        return None

    for line in block:

        if not line:
            continue

        if is_board(line):
            return clean_board_name(line)

    return None


# =========================================================
# INSTITUTION KEYWORD CHECK
# =========================================================

def contains_institution_keyword(text):
    """
    Check whether a line looks like an institution.
    """

    if not text:
        return False

    lower = text.lower()

    return any(
        keyword in lower
        for keyword in INSTITUTION_KEYWORDS
    )


def is_university_line(text):
    """
    Check whether a line looks like a university continuation.
    """

    if not text:
        return False

    lower = text.lower()

    return any(
        keyword in lower
        for keyword in UNIVERSITY_KEYWORDS
    )

 
def is_degree_line(text):
    """
    Determine whether a line contains degree information.
    """

    if not text:
        return False

    lower = text.lower()

    if re.search(r"\b\d{4}\b", lower):
        return True

    return any(
        re.search(
            pattern,
            lower
        )
        for pattern in DEGREE_PATTERNS
    )


def extract_university(block, institution=None):
    """
    Extract a university continuation line from an education block.
    """

    if not block:
        return None

    institution = normalize_spaces(institution) if institution else None

    for line in block:

        if not line:
            continue

        cleaned = normalize_spaces(line)

        if not cleaned:
            continue

        if is_board(cleaned):
            continue

        if institution and cleaned == institution:
            continue

        if is_university_line(cleaned):
            if is_degree_line(cleaned):
                continue

            cleaned = clean_institution_name(cleaned)

            if cleaned and not is_board(cleaned):
                return cleaned

    return None


# =========================================================
# CLEAN INSTITUTION
# =========================================================

def clean_institution_name(institution):
    """
    Clean institution text.

    Example
    -------
    2012-2016 Bachelor of Engineering (B.E),
    P.E.S Institute of Technology,
    Bangalore South Campus, India.

    becomes

    P.E.S Institute of Technology,
    Bangalore South Campus, India
    """

    if not institution:
        return None

    # -----------------------------------------------
    # Normalize spaces
    # -----------------------------------------------

    institution = normalize_spaces(
        institution
    )

    # -----------------------------------------------
    # Remove dates
    # -----------------------------------------------

    institution = remove_dates(
        institution
    )

    # -----------------------------------------------
    # Remove qualification/exam
    # -----------------------------------------------

    institution = remove_qualification_prefix(
        institution
    )

    # -----------------------------------------------
    # Remove degree
    # -----------------------------------------------

    institution = remove_degree(
        institution
    )

    # -----------------------------------------------
    # Remove leading noise
    # -----------------------------------------------

    institution = remove_leading_noise(
        institution
    )

    # -----------------------------------------------
    # Normalize commas
    # -----------------------------------------------

    institution = normalize_commas(
        institution
    )

    # -----------------------------------------------
    # Remove leading/trailing noise again
    # -----------------------------------------------

    institution = remove_leading_noise(
        institution
    )

    # -----------------------------------------------
    # Final cleanup
    # -----------------------------------------------

    institution = institution.strip(
        " ,.;:-()"
    )

    if not institution:
        return None

    return institution


# =========================================================
# FIND CANDIDATE LINES
# =========================================================

def find_institution_candidates(block):
    """
    Find possible institution lines.
    """

    candidates = []

    if not block:
        return candidates

    for line in block:

        if not line:
            continue

        line = normalize_spaces(line)

        if not line:
            continue

        # -------------------------------------------
        # Ignore education board
        # -------------------------------------------

        if is_board(line):
            continue

        # -------------------------------------------
        # Check institution keyword
        # -------------------------------------------

        if contains_institution_keyword(line):

            candidates.append(line)

    return candidates


# =========================================================
# MAIN EXTRACTOR
# =========================================================

def extract_institution(block):
    """
    Extract institution from an education block.

    Parameters
    ----------
    block : list[str]

    Returns
    -------
    str | None
    """

    if not block:
        return None

    candidates = find_institution_candidates(
        block
    )

    # -----------------------------------------------------
    # Try institution candidates
    # -----------------------------------------------------

    for candidate in candidates:

        cleaned = clean_institution_name(
            candidate
        )

        if not cleaned:
            continue

        # Never return board as institution

        if is_board(cleaned):
            continue

        return cleaned

    # -----------------------------------------------------
    # Fallback
    # -----------------------------------------------------

    # Some resumes don't contain explicit keywords such
    # as "University" or "College". Look for lines that
    # contain a comma-separated location.

    for line in block:

        if not line:
            continue

        cleaned = clean_institution_name(
            line
        )

        if not cleaned:
            continue

        if is_board(cleaned):
            continue

        # Avoid returning obvious degree/field lines

        lower = cleaned.lower()

        if any(
            word in lower
            for word in [
                "computer science",
                "engineering",
                "information technology",
                "computer application",
                "aggregate score",
                "cgpa",
                "marks obtained",
            ]
        ):
            continue

        if "," in cleaned:

            return cleaned

    return None


# =========================================================
# TESTING
# =========================================================

if __name__ == "__main__":

    test_blocks = [

        [
            "2012-2016 Bachelor of Engineering (B.E), "
            "P.E.S Institute of Technology, "
            "Bangalore South Campus, India."
        ],

        [
            "2012-2016 Bachelor of Engineering (B.E), "
            "P.E.S Institute of Technology, "
            "Bangalore South Campus, India.",
            "Visvesvaraya Technological University, "
            "Belgaum, Karnataka, India.",
            "Computer Science and Engineering",
            "Aggregate Score : 64.2",
        ],

        [
            "2011-2012 All India Senior School Certificate Exam, "
            "Kendriya Vidyalaya Kalpetta,kerala, India.",
            "Central Board of Secondary Education",
            "Marks Obtained - 85.5",
        ],

        [
            "2000-2010 All India Secondary School Examination, "
            "Kendriya Vidyalaya Kalpetta,kerala, India.",
            "Central Board of Secondary Education",
            "Marks Obtained - 9.4 CGPA",
        ],

    ]

    for i, block in enumerate(
        test_blocks,
        start=1
    ):

        result = extract_institution(
            block
        )

        print(
            f"Block {i}: {result}"
        )
