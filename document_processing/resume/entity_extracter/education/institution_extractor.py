"""
institution_extractor.py

Responsibilities
----------------
1. Extract institution / college / school names.
2. Use university_extractor.py for university detection.
3. Extract education boards.
4. Remove degree, qualification and date noise.
5. Avoid classifying university names as institutions.
6. Support university aliases through the external
   university_dictionary.json.
7. Ensure university content is removed BEFORE institution
   extraction.

Important
---------
University aliases and university data must NOT be hard-coded
in this file.

University detection is delegated to:
    university_extractor.py
"""

import re

from document_processing.resume.entity_extracter.education.university_extractor import (
    extract_university as extract_university_alias,
    remove_university_content,
)


# ============================================================
# EDUCATION BOARD PATTERNS
# ============================================================

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


# ============================================================
# QUALIFICATION / EXAMINATION PREFIXES
# ============================================================

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


# ============================================================
# DEGREE PATTERNS
# ============================================================

DEGREE_PATTERNS = [

    # Full degree names
    r"\bbachelor of technology\b",
    r"\bbachelor of engineering\b",
    r"\bmaster of technology\b",
    r"\bmaster of engineering\b",
    r"\bmaster of computer applications\b",
    r"\bbachelor of computer applications\b",
    r"\bbachelor of science\b",
    r"\bmaster of science\b",
    r"\bbachelor of arts\b",
    r"\bmaster of arts\b",
    r"\bbachelor of commerce\b",
    r"\bmaster of commerce\b",

    # B.Tech / B.E / M.Tech / M.E
    r"\bb\.?\s*tech\b",
    r"\bb\.?\s*e\.?\b",
    r"\bm\.?\s*tech\b",
    r"\bm\.?\s*e\.?\b",

    # BCA / MCA
    r"\bb\.?\s*c\.?\s*a\.?\b",
    r"\bm\.?\s*c\.?\s*a\.?\b",

    # BSc / MSc
    r"\bb\.?\s*sc\.?\b",
    r"\bm\.?\s*sc\.?\b",

    # MBA / BBA
    r"\bb\.?\s*b\.?\s*a\.?\b",
    r"\bm\.?\s*b\.?\s*a\.?\b",

    # BCom / MCom
    r"\bb\.?\s*com\.?\b",
    r"\bm\.?\s*com\.?\b",

]


# ============================================================
# INSTITUTION KEYWORDS
#
# These identify colleges / institutes / schools.
#
# IMPORTANT:
# "university" is intentionally NOT here.
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
# UNIVERSITY WORDING
#
# This is NOT a university dictionary.
#
# These generic terms are only used as a safety filter so that
# an unrecognized university line is not returned as an
# institution.
#
# Actual university aliases are handled by
# university_extractor.py.
# ============================================================

UNIVERSITY_WORDING = [

    "university",
    "universit",
    "technological university",
    "technical university",
    "deemed university",
    "open university",

]


# ============================================================
# BASIC CLEANING
# ============================================================

def normalize_spaces(text):
    """
    Normalize whitespace and non-breaking spaces.
    """

    if not text:
        return ""

    text = text.replace(
        "\xa0",
        " "
    )

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

    if not text:
        return ""

    text = re.sub(
        r"\s*,\s*",
        ", ",
        text
    )

    text = re.sub(
        r",\s*,+",
        ", ",
        text
    )

    return text.strip()


# ============================================================
# REMOVE DATES
# ============================================================

def remove_dates(text):
    """
    Remove education date ranges.

    Examples
    --------
    2012-2016
    2011–2012
    2022 - Present
    """

    if not text:
        return ""

    # --------------------------------------------------------
    # Date range with two years
    # --------------------------------------------------------

    text = re.sub(
        r"\b(?:19|20)\d{2}\s*[-–—]\s*(?:19|20)?\d{2}\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Date range ending with Present
    # --------------------------------------------------------

    text = re.sub(
        r"\b(?:19|20)\d{2}\s*[-–—]\s*present\b",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Single year at beginning
    # --------------------------------------------------------

    text = re.sub(
        r"^\s*(?:19|20)\d{2}\s*[,|:-]?\s*",
        "",
        text,
    )

    return text


# ============================================================
# REMOVE DEGREE
# ============================================================

def remove_degree(text):
    """
    Remove degree names and abbreviations.
    """

    if not text:
        return ""

    # --------------------------------------------------------
    # Remove degree names / abbreviations
    # --------------------------------------------------------

    for pattern in DEGREE_PATTERNS:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )

    # --------------------------------------------------------
    # Remove degree abbreviations inside parentheses
    #
    # Examples:
    #   (B.E)
    #   (B.Tech)
    #   (M.E)
    #   (M.Tech)
    #   (BCA)
    #   (MCA)
    #   (BSc)
    #   (MSc)
    #   (BCom)
    #   (MCom)
    # --------------------------------------------------------

    text = re.sub(
        r"\(\s*"
        r"(?:"
        r"B\.?\s*E\.?|"
        r"B\.?\s*Tech\.?|"
        r"M\.?\s*E\.?|"
        r"M\.?\s*Tech\.?|"
        r"B\.?\s*C\.?\s*A\.?|"
        r"M\.?\s*C\.?\s*A\.?|"
        r"B\.?\s*Sc\.?|"
        r"M\.?\s*Sc\.?|"
        r"B\.?\s*Com\.?|"
        r"M\.?\s*Com\.?"
        r")"
        r"\s*\)",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Remove empty parentheses
    # --------------------------------------------------------

    text = re.sub(
        r"\(\s*\)",
        "",
        text,
    )

    return text


# ============================================================
# REMOVE QUALIFICATION / EXAMINATION PREFIX
# ============================================================

def remove_qualification_prefix(text):
    """
    Remove school examination names.
    """

    if not text:
        return ""

    for pattern in QUALIFICATION_PREFIX_PATTERNS:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE,
        )

    return text


# ============================================================
# REMOVE LEADING / TRAILING NOISE
# ============================================================

def remove_leading_noise(text):
    """
    Remove punctuation left after cleaning.
    """

    if not text:
        return ""

    text = re.sub(
        r"^[\s,|:;()\-\–—]+",
        "",
        text,
    )

    text = re.sub(
        r"[\s,|:;()\-\–—]+$",
        "",
        text,
    )

    return text


# ============================================================
# BOARD DETECTION
# ============================================================

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
            lower,
        )
        for pattern in BOARD_PATTERNS
    )


# ============================================================
# BOARD CLEANING
# ============================================================

def clean_board_name(text):
    """
    Clean board text.
    """

    if not text:
        return None

    board = normalize_spaces(
        text
    )

    board = remove_leading_noise(
        board
    )

    board = normalize_commas(
        board
    )

    board = remove_leading_noise(
        board
    )

    board = board.strip(
        " ,.;:-()"
    )

    if not board:
        return None

    return board


# ============================================================
# EXTRACT BOARD
# ============================================================

def extract_board(block):
    """
    Extract board name from education block.
    """

    if not block:
        return None

    for line in block:

        if not isinstance(line, str):
            continue

        if is_board(line):

            return clean_board_name(
                line
            )

    return None


# ============================================================
# INSTITUTION KEYWORD CHECK
# ============================================================

def contains_institution_keyword(text):
    """
    Check whether a line looks like a college,
    institute, school, academy, etc.

    University is intentionally excluded.
    """

    if not text:
        return False

    lower = text.lower()

    return any(
        keyword in lower
        for keyword in INSTITUTION_KEYWORDS
    )


# ============================================================
# GENERIC UNIVERSITY WORDING CHECK
# ============================================================

def contains_university_wording(text):
    """
    Safety check for generic university wording.

    This does NOT identify aliases.

    University aliases are handled by
    university_extractor.py.

    This function only prevents text such as:

        Visvesvaraya Technological University

    from being returned as an institution if, for some reason,
    it was not present in the external university dictionary.
    """

    if not text:
        return False

    lower = text.lower()

    return any(
        keyword in lower
        for keyword in UNIVERSITY_WORDING
    )


# ============================================================
# DEGREE LINE DETECTION
# ============================================================

def is_degree_line(text):
    """
    Determine whether a line contains degree information.
    """

    if not text:
        return False

    lower = text.lower()

    # --------------------------------------------------------
    # Year
    # --------------------------------------------------------

    if re.search(
        r"\b(?:19|20)\d{2}\b",
        lower,
    ):
        return True

    # --------------------------------------------------------
    # Degree pattern
    # --------------------------------------------------------

    return any(
        re.search(
            pattern,
            lower,
        )
        for pattern in DEGREE_PATTERNS
    )


# ============================================================
# CLEAN INSTITUTION NAME
# ============================================================

def clean_institution_name(institution):
    """
    Clean institution text.

    University content should already have been removed before
    this function is called.
    """

    if not institution:
        return None

    institution = normalize_spaces(
        institution
    )

    # --------------------------------------------------------
    # Remove pipe and anything after it
    # --------------------------------------------------------

    if "|" in institution:

        institution = (
            institution
            .split("|")[0]
            .strip()
        )

    # --------------------------------------------------------
    # Handle separators
    #
    # Example:
    #
    # B.Tech — ABC College
    #
    # ABC College — B.Tech
    # --------------------------------------------------------

    parts = re.split(
        r"\s*[-–—~]+\s*",
        institution
    )

    if len(parts) > 1:

        valid_parts = []

        for part in parts:

            part = normalize_spaces(
                part
            )

            if not part:
                continue

            if is_board(part):
                continue

            if is_degree_line(part):
                continue

            if contains_university_wording(part):
                continue

            valid_parts.append(
                part
            )

        if valid_parts:

            # ------------------------------------------------
            # Prefer the part explicitly containing an
            # institution keyword.
            # ------------------------------------------------

            for part in valid_parts:

                if contains_institution_keyword(
                    part
                ):
                    institution = part
                    break

            else:

                institution = valid_parts[-1]

    # --------------------------------------------------------
    # Remove dates
    # --------------------------------------------------------

    institution = remove_dates(
        institution
    )

    # --------------------------------------------------------
    # Remove qualification
    # --------------------------------------------------------

    institution = remove_qualification_prefix(
        institution
    )

    # --------------------------------------------------------
    # Remove degree
    # --------------------------------------------------------

    institution = remove_degree(
        institution
    )

    # --------------------------------------------------------
    # Remove "in" when used as a degree connector
    #
    # Example:
    #
    # B.Tech in ABC College
    # --------------------------------------------------------

    institution = re.sub(
        r"\s+in\s+",
        " ",
        institution,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Remove leading noise
    # --------------------------------------------------------

    institution = remove_leading_noise(
        institution
    )

    # --------------------------------------------------------
    # Normalize commas
    # --------------------------------------------------------

    institution = normalize_commas(
        institution
    )

    institution = remove_leading_noise(
        institution
    )

    institution = institution.strip(
        " ,.;:-()"
    )

    if not institution:
        return None

    return institution


# ============================================================
# REMOVE RECOGNIZED UNIVERSITY FROM BLOCK
# ============================================================

# ============================================================
# REMOVE RECOGNIZED UNIVERSITY
# ============================================================

def _remove_recognized_university_from_block(
    block,
    university_result
):
    """
    Remove the recognized university from its original line.

    The rest of the education block is preserved.
    """

    if not block:
        return []

    cleaned_block = []

    university_line_index = None

    if university_result:

        university_line_index = (
            university_result.get(
                "line_index"
            )
        )

    for index, line in enumerate(block):

        if not isinstance(
            line,
            str
        ):
            continue

        line = normalize_spaces(
            line
        )

        if not line:
            continue

        # ----------------------------------------------------
        # Remove university only from the matched line.
        # ----------------------------------------------------

        if (
            university_line_index is not None
            and index == university_line_index
        ):

            line = remove_university_content(
                line,
                university_result
            )

            line = normalize_spaces(
                line
            )

        if line:
            cleaned_block.append(
                line
            )

    return cleaned_block


# ============================================================
# FIND INSTITUTION CANDIDATES
# ============================================================

def find_institution_candidates(
    block,
    university_result=None,
):
    """
    Find possible college / institute / school lines.

    University content is removed BEFORE candidate detection.

    Parameters
    ----------
    block:
        Education block.

    university_result:
        Result returned by
        university_extractor.extract_university().
    """

    candidates = []

    if not block:
        return candidates

    # --------------------------------------------------------
    # First remove recognized university content.
    # --------------------------------------------------------

    working_block = (
        _remove_recognized_university_from_block(
            block,
            university_result,
        )
    )

    # --------------------------------------------------------
    # Candidate detection.
    # --------------------------------------------------------

    for line in working_block:

        if not isinstance(line, str):
            continue

        line = normalize_spaces(
            line
        )

        if not line:
            continue

        # ----------------------------------------------------
        # Never classify board as institution.
        # ----------------------------------------------------

        if is_board(line):
            continue

        # ----------------------------------------------------
        # Never classify generic university wording as
        # institution.
        # ----------------------------------------------------

        if contains_university_wording(line):
            continue

        # ----------------------------------------------------
        # Ignore degree lines.
        # ----------------------------------------------------

        if is_degree_line(line):
            continue

        # ----------------------------------------------------
        # Institution keyword.
        # ----------------------------------------------------

        if contains_institution_keyword(line):

            candidates.append(
                line
            )

    return candidates


# ============================================================
# FIND FALLBACK INSTITUTION CANDIDATES
# ============================================================

def find_fallback_institution_candidates(
    block,
    university_result=None,
):
    """
    Find institution candidates when the institution does not
    contain an explicit keyword such as "College" or "Institute".

    University content is removed first.
    """

    candidates = []

    if not block:
        return candidates

    working_block = (
        _remove_recognized_university_from_block(
            block,
            university_result,
        )
    )

    for line in working_block:

        if not isinstance(line, str):
            continue

        cleaned = clean_institution_name(
            line
        )

        if not cleaned:
            continue

        # ----------------------------------------------------
        # Board
        # ----------------------------------------------------

        if is_board(cleaned):
            continue

        # ----------------------------------------------------
        # Generic university wording
        # ----------------------------------------------------

        if contains_university_wording(
            cleaned
        ):
            continue

        # ----------------------------------------------------
        # Degree
        # ----------------------------------------------------

        if is_degree_line(cleaned):
            continue

        lower = cleaned.lower()

        # ----------------------------------------------------
        # Ignore obvious field-of-study lines.
        # ----------------------------------------------------

        field_noise = [

            "computer science",
            "engineering",
            "information technology",
            "computer application",
            "electronics",
            "communication engineering",
            "mechanical engineering",
            "civil engineering",
            "electrical engineering",
            "aggregate score",
            "cgpa",
            "marks obtained",
            "percentage",

        ]

        if any(
            word in lower
            for word in field_noise
        ):
            continue

        # ----------------------------------------------------
        # Comma-containing lines are useful fallback
        # candidates.
        #
        # Example:
        #
        # XYZ College, Kerala, India
        # ABC Institute, Bangalore
        # ----------------------------------------------------

        if "," in cleaned:

            candidates.append(
                cleaned
            )

    return candidates


# ============================================================
# EXTRACT UNIVERSITY FROM BLOCK
# ============================================================

# ============================================================
# EXTRACT UNIVERSITY FROM BLOCK
# ============================================================

def extract_university_from_block(block):
    """
    Detect university from an education block.

    The actual university detection is delegated to
    university_extractor.py.

    Returns the complete detection result so that the
    institution extractor can remove the university
    before institution detection.
    """

    if not block:
        return None

    for line_index, line in enumerate(block):

        if not isinstance(
            line,
            str
        ):
            continue

        line = normalize_spaces(
            line
        )

        if not line:
            continue

        # IMPORTANT:
        # This calls the imported university extractor.
        #
        # It does NOT call the local extract_university()
        # function below.

        result = extract_university_alias(
            line
        )

        if not result:
            continue

        result["line_index"] = (
            line_index
        )

        return result

    return None


# ============================================================
# BACKWARD-COMPATIBLE UNIVERSITY VALUE
# ============================================================

def extract_university(
    block,
    institution=None
):
    """
    Return only the university value.

    This function is retained for backward compatibility.

    Example
    -------
    [
        "B.E. Information Technology",
        "Anna University",
        "2016"
    ]

    returns:

        "Anna University"
    """

    result = extract_university_from_block(
        block
    )

    if not result:
        return None

    return result.get(
        "value"
    )
    
# ============================================================
# EXTRACT INSTITUTION
# ============================================================

def extract_institution(
    block,
    university_result=None
):
    """
    Extract college / institute / school.

    University detection is performed first.

    The detected university is removed before institution
    detection.

    Unknown universities are also protected because the
    university extractor can detect them using generic
    patterns.
    """

    if not block:
        return None

    # --------------------------------------------------------
    # STEP 1
    # Detect university only if caller didn't already provide it.
    # --------------------------------------------------------

    if university_result is None:

        university_result = (
            extract_university_from_block(
                block
            )
        )

    # --------------------------------------------------------
    # STEP 2
    # Remove university from block.
    # --------------------------------------------------------

    candidates = find_institution_candidates(
        block,
        university_result
    )

    # --------------------------------------------------------
    # STEP 3
    # Explicit institution candidates.
    # --------------------------------------------------------

    for candidate in candidates:

        cleaned = clean_institution_name(
            candidate
        )

        if not cleaned:
            continue

        if is_board(cleaned):
            continue

        if contains_university_wording(
            cleaned
        ):
            continue

        if is_degree_line(cleaned):
            continue

        return cleaned

    # --------------------------------------------------------
    # STEP 4
    # Fallback institution candidates.
    # --------------------------------------------------------

    fallback_candidates = (
        find_fallback_institution_candidates(
            block,
            university_result
        )
    )

    for candidate in fallback_candidates:

        cleaned = clean_institution_name(
            candidate
        )

        if not cleaned:
            continue

        if is_board(cleaned):
            continue

        if contains_university_wording(
            cleaned
        ):
            continue

        if is_degree_line(cleaned):
            continue

        return cleaned

    return None


# ============================================================
# EXTRACT ALL EDUCATION INSTITUTION ENTITIES
# ============================================================

def extract_education_institutions(block):
    """
    Extract university, institution and board.

    University is detected FIRST.

    The exact same university detection result is then
    passed to institution extraction.
    """

    if not block:

        return {
            "university": None,
            "institution": None,
            "board": None,
        }

    # --------------------------------------------------------
    # UNIVERSITY FIRST
    # --------------------------------------------------------

    university_result = (
        extract_university_from_block(
            block
        )
    )

    university = None

    if university_result:

        university = (
            university_result.get(
                "value"
            )
        )

    # --------------------------------------------------------
    # INSTITUTION SECOND
    #
    # IMPORTANT:
    # Pass the already detected result.
    # Do NOT detect university again.
    # --------------------------------------------------------

    institution = extract_institution(
        block,
        university_result
    )

    # --------------------------------------------------------
    # BOARD
    # --------------------------------------------------------

    board = extract_board(
        block
    )

    return {

        "university": university,

        "institution": institution,

        "board": board,

    }


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    test_blocks = [

        # ----------------------------------------------------
        # 1. University abbreviation only
        # ----------------------------------------------------

        [
            "B.Tech Electronics Communication Engineering",
            "KTU",
            "2022 - 2026",
        ],

        # ----------------------------------------------------
        # 2. College + University
        # ----------------------------------------------------

        [
            "B.Tech Computer Science and Engineering",
            "Rajagiri School of Engineering",
            "APJ Abdul Kalam Technological University",
            "2022 - 2026",
        ],

        # ----------------------------------------------------
        # 3. University full name
        # ----------------------------------------------------

        [
            "B.Tech Computer Science",
            "Visvesvaraya Technological University",
            "2017 - 2021",
        ],

        # ----------------------------------------------------
        # 4. Institution only
        # ----------------------------------------------------

        [
            "Bachelor of Engineering",
            "P.E.S Institute of Technology",
            "2012 - 2016",
        ],

        # ----------------------------------------------------
        # 5. School
        # ----------------------------------------------------

        [
            "All India Senior School Certificate Exam",
            "Kendriya Vidyalaya Kalpetta, Kerala, India",
            "Central Board of Secondary Education",
            "2011 - 2012",
        ],

        # ----------------------------------------------------
        # 6. MIXED LINE
        #
        # University + degree
        # ----------------------------------------------------

        [
            "VTU - B.Tech",
            "Computer Science and Engineering",
            "2019",
        ],

        # ----------------------------------------------------
        # 7. MIXED LINE
        #
        # Degree + university
        # ----------------------------------------------------

        [
            "B.Tech - VTU",
            "Computer Science and Engineering",
            "2019",
        ],

        # ----------------------------------------------------
        # 8. MIXED LINE
        #
        # Institution + university
        # ----------------------------------------------------

        [
            "ABC College - VTU",
            "B.Tech Computer Science",
            "2019",
        ],

        # ----------------------------------------------------
        # 9. MIXED LINE
        #
        # University + institution + degree
        # ----------------------------------------------------

        [
            "VTU - XYZ College - B.Tech",
            "Computer Science Engineering",
            "2019",
        ],

    ]

    for i, block in enumerate(
        test_blocks,
        start=1,
    ):

        result = extract_education_institutions(
            block
        )

        print(
            f"\n========== BLOCK {i} =========="
        )

        print(
            "University:",
            result["university"],
        )

        print(
            "Institution:",
            result["institution"],
        )

        print(
            "Board:",
            result["board"],
        )
