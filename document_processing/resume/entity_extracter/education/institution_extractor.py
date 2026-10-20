"""
institution_extractor.py

Responsibilities
----------------
1. Extract college / institute / school names.
2. Delegate university detection to university_extractor.py.
3. Extract education boards.
4. Remove degree / qualification / date / field-of-study noise.
5. Avoid returning university names as institutions.
6. Support university aliases through university_dictionary.json.
7. Remove university content BEFORE institution extraction.
8. Correctly handle mixed education lines.

Examples
--------
B.Tech in Computer Science and Engineering - Kerala Institute of Technology
    -> Kerala Institute of Technology

Higher Secondary - Computer Science - Government Higher Secondary School
    -> Government Higher Secondary School

Kerala Institute of Technology (2020 - 2024)
    -> Kerala Institute of Technology
"""

import re


from document_processing.resume.entity_extracter.education.university_extractor import (
    extract_university as extract_university_alias,
    remove_university_content,
    remove_years_from_university_remainder,
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
# QUALIFICATION PREFIXES
# ============================================================

QUALIFICATION_PREFIX_PATTERNS = [
    r"\ball india senior school certificate\s+exam(?:ination)?\b",
    r"\bsenior school certificate\s+exam(?:ination)?\b",
    r"all india secondary school examination",
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
    # Full names
    r"\bbachelor\s+of\s+technology\b",
    r"\bbachelor\s+of\s+engineering\b",
    r"\bmaster\s+of\s+technology\b",
    r"\bmaster\s+of\s+engineering\b",
    r"\bbachelor\s+of\s+computer\s+applications\b",
    r"\bmaster\s+of\s+computer\s+applications\b",
    r"\bbachelor\s+of\s+science\b",
    r"\bmaster\s+of\s+science\b",
    r"\bbachelor\s+of\s+arts\b",
    r"\bmaster\s+of\s+arts\b",
    r"\bbachelor\s+of\s+commerce\b",
    r"\bmaster\s+of\s+commerce\b",
    r"\bbachelor\s+of\s+business\s+administration\b",
    r"\bmaster\s+of\s+business\s+administration\b",
    r"\bbachelor\s+of\s+pharmacy\b",
    r"\bmaster\s+of\s+pharmacy\b",
    r"\bbachelor\s+of\s+architecture\b",
    r"\bbachelor\s+of\s+design\b",
    r"\bbachelor\s+of\s+fine\s+arts\b",
    r"\bbachelor\s+of\s+laws\b",
    r"\bbachelor\s+of\s+social\s+work\b",
    r"\bbachelor\s+of\s+physiotherapy\b",
    r"\bbachelor\s+of\s+hotel\s+management\b",
    r"\bdoctor\s+of\s+philosophy\b",
    r"\bassociate\s+degree\b",

    # Abbreviations
    r"\bb\.?\s*tech\.?\b",
    r"\bb\.?\s*e\.?\b",
    r"\bm\.?\s*tech\.?\b",
    r"\bm\.?\s*e\.?\b",
    r"\bb\.?\s*c\.?\s*a\.?\b",
    r"\bm\.?\s*c\.?\s*a\.?\b",
    r"\bb\.?\s*sc\.?\b",
    r"\bm\.?\s*sc\.?\b",
    r"\bb\.?\s*com\.?\b",
    r"\bm\.?\s*com\.?\b",
    r"\bb\.?\s*b\.?\s*a\.?\b",
    r"\bm\.?\s*b\.?\s*a\.?\b",
    r"\bb\.?\s*a\.?\b",
    r"\bm\.?\s*a\.?\b",
    r"\bb\.?\s*pharm\.?\b",
    r"\bm\.?\s*pharm\.?\b",
    r"\bb\.?\s*arch\.?\b",
    r"\bb\.?\s*des\.?\b",
    r"\bb\.?\s*f\.?\s*a\.?\b",
    r"\bl\.?\s*l\.?\s*b\.?\b",
    r"\bm\.?\s*b\.?\s*b\.?\s*s\.?\b",
    r"\bb\.?\s*d\.?\s*s\.?\b",
    r"\bb\.?\s*p\.?\s*t\.?\b",
    r"\bp\.?\s*h\.?\s*d\.?\b",
    r"\bcopa\b",
]

COMPILED_DEGREE_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in DEGREE_PATTERNS
)

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
# GENERIC UNIVERSITY WORDING
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
# FIELD-OF-STUDY NOISE
# ============================================================

FIELD_OF_STUDY_PATTERNS = [
    r"computer\s+science(?:\s+and\s+engineering)?",
    r"computer\s+science",
    r"information\s+technology",
    r"information\s+systems",
    r"computer\s+applications?",
    r"software\s+engineering",
    r"electronics?\s+and\s+communication(?:\s+engineering)?",
    r"electronics?\s+communication(?:\s+engineering)?",
    r"electrical\s+engineering",
    r"mechanical\s+engineering",
    r"civil\s+engineering",
    r"chemical\s+engineering",
    r"communication\s+engineering",
    r"business\s+administration",
    r"business\s+management",
    r"commerce",
    r"physics",
    r"chemistry",
    r"mathematics",
    r"biology",
    r"microbiology",
    r"biotechnology",
]

COMPILED_QUALIFICATION_PREFIX_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in QUALIFICATION_PREFIX_PATTERNS
)
COMPILED_BOARD_PATTERNS = tuple(
    re.compile(pattern)
    for pattern in BOARD_PATTERNS
)
COMPILED_FIELD_OF_STUDY_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in FIELD_OF_STUDY_PATTERNS
)
EDUCATION_YEAR_RANGE_PATTERN = re.compile(
    r"""
    \(?\s*
    (?:19|20)\d{2}
    \s*[-–—]
    \s*
    (?:
        (?:19|20)\d{2}
        |
        present
    )
    \s*\)?
    """,
    re.IGNORECASE | re.VERBOSE,
)
PARENTHESIZED_YEAR_PATTERN = re.compile(
    r"\(\s*(?:19|20)\d{2}\s*\)",
    re.IGNORECASE,
)
INCOMPLETE_PARENTHESIZED_YEAR_PATTERN = re.compile(
    r"\(\s*(?:19|20)\d{2}\b",
    re.IGNORECASE,
)
STANDALONE_YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b",
    re.IGNORECASE,
)
EMPTY_PARENTHESES_PATTERN = re.compile(r"\(\s*\)")
LEADING_IN_PATTERN = re.compile(r"^\s*in\s+", re.IGNORECASE)
MIXED_LINE_SEPARATOR_PATTERN = re.compile(r"\s*[-–—|]\s*")

# ============================================================
# NORMALIZATION
# ============================================================

def normalize_spaces(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_commas(text):
    if not text:
        return ""

    text = re.sub(
        r"\s*,\s*",
        ", ",
        text,
    )

    text = re.sub(
        r",\s*,+",
        ", ",
        text,
    )

    return text.strip()


# ============================================================
# EDUCATION YEAR DETECTION
# ============================================================

def contains_education_year(text):
    """
    Detect education years.

    Supports:
        2020
        (2020
        (2020)
        2020-2024
        2020 - 2024
        2020–2024
        2020 - Present
        2024
    """

    if not text:
        return False

    return bool(
        re.search(
            r"""
            (?:
                \b(?:19|20)\d{2}\b
            )
            |
            (?:
                \(?\s*(?:19|20)\d{2}
                \s*[-–—]
                \s*(?:
                    (?:19|20)\d{2}
                    |
                    present
                )
                \s*\)?
            )
            """,
            text,
            flags=re.IGNORECASE | re.VERBOSE,
        )
    )


# ============================================================
# REMOVE EDUCATION YEARS
# ============================================================

def remove_education_years(text):
    """
    Remove years and education date ranges.
    """

    if not text:
        return ""

    # Date range first.
    text = EDUCATION_YEAR_RANGE_PATTERN.sub("", text)

    # Parenthesized single year.
    text = PARENTHESIZED_YEAR_PATTERN.sub("", text)

    # Incomplete parenthesized year such as "(2020".
    text = INCOMPLETE_PARENTHESIZED_YEAR_PATTERN.sub("", text)

    # Standalone year.
    text = STANDALONE_YEAR_PATTERN.sub("", text)

    return normalize_spaces(text)


# ============================================================
# REMOVE DATES
# ============================================================

def remove_dates(text):
    """
    Backward-compatible alias.
    """

    return remove_education_years(text)


# ============================================================
# REMOVE DEGREE
# ============================================================

def remove_degree(text):
    if not text:
        return ""

    for pattern in COMPILED_DEGREE_PATTERNS:
        text = pattern.sub("", text)

    # Remove empty parentheses.
    text = EMPTY_PARENTHESES_PATTERN.sub("", text)

    return normalize_spaces(text)


# ============================================================
# REMOVE QUALIFICATION
# ============================================================

def remove_qualification_prefix(text):
    if not text:
        return ""

    for pattern in COMPILED_QUALIFICATION_PREFIX_PATTERNS:
        text = pattern.sub("", text)

    return normalize_spaces(text)


# ============================================================
# REMOVE LEADING / TRAILING NOISE
# ============================================================

def remove_leading_noise(text):
    if not text:
        return ""

    text = re.sub(
        r"^[\s,|:;()\-–—]+",
        "",
        text,
    )

    text = re.sub(
        r"[\s,|:;()\-–—]+$",
        "",
        text,
    )

    return text.strip()


# ============================================================
# BOARD
# ============================================================

def is_board(text):
    if not text:
        return False

    lower = text.lower()

    return any(pattern.search(lower) for pattern in COMPILED_BOARD_PATTERNS)


def clean_board_name(text):
    if not text:
        return None

    board = normalize_spaces(text)
    board = normalize_commas(board)
    board = remove_leading_noise(board)

    board = board.strip(
        " ,.;:-()"
    )

    return board or None


def extract_board(block):
    if not block:
        return None

    for line in block:
        if isinstance(line, str) and is_board(line):
            return clean_board_name(line)

    return None


# ============================================================
# INSTITUTION KEYWORD
# ============================================================

def contains_institution_keyword(text):
    if not text:
        return False

    lower = text.lower()

    return any(
        keyword in lower
        for keyword in INSTITUTION_KEYWORDS
    )


def contains_university_wording(text):
    if not text:
        return False

    lower = text.lower()

    return any(
        keyword in lower
        for keyword in UNIVERSITY_WORDING
    )


# ============================================================
# DEGREE LINE
# ============================================================

def is_degree_line(text):
    """
    Detect actual degree / qualification content.

    IMPORTANT:
    A year alone is NOT considered a degree line.
    """

    if not text:
        return False

    lower = text.lower()

    if any(pattern.search(lower) for pattern in COMPILED_DEGREE_PATTERNS):
        return True

    if any(
        pattern.search(lower)
        for pattern in COMPILED_QUALIFICATION_PREFIX_PATTERNS
    ):
        return True

    return False


# ============================================================
# FIELD OF STUDY
# ============================================================

def remove_field_of_study(text):
    """
    Remove common field-of-study phrases.

    This is intentionally conservative. It is primarily used
    after the institution-bearing portion has been identified.
    """

    if not text:
        return ""

    result = text

    for pattern in COMPILED_FIELD_OF_STUDY_PATTERNS:
        result = pattern.sub("", result)

    return normalize_spaces(result)


# ============================================================
# EXTRACT INSTITUTION FROM MIXED LINE
# ============================================================

def extract_institution_from_mixed_line(text):
    """
    Extract the institution-bearing portion from a mixed line.

    Examples
    --------
    B.Tech in Computer Science and Engineering - Kerala Institute of Technology
        -> Kerala Institute of Technology

    Higher Secondary - Computer Science - Government Higher Secondary School
        -> Government Higher Secondary School

    ABC College - B.Tech
        -> ABC College
    """

    if not text:
        return None

    text = normalize_spaces(text)

    # --------------------------------------------------------
    # Prefer explicit hyphen / dash-separated segments.
    # --------------------------------------------------------

    parts = MIXED_LINE_SEPARATOR_PATTERN.split(text)

    cleaned_parts = []

    for part in parts:

        part = normalize_spaces(part)

        if not part:
            continue

        if is_board(part):
            continue

        if contains_university_wording(part):
            continue

        part = remove_education_years(part)
        part = remove_qualification_prefix(part)
        part = remove_degree(part)

        # "in Computer Science and Engineering"
        # should not become an institution.
        part = LEADING_IN_PATTERN.sub("", part)

        part = remove_field_of_study(part)

        part = remove_leading_noise(part)
        part = normalize_spaces(part)

        if not part:
            continue

        cleaned_parts.append(part)

    if not cleaned_parts:
        return None

    # --------------------------------------------------------
    # Strongest signal: explicit institution keyword.
    # Search from right to left because institutions commonly
    # appear after degree / field information.
    # --------------------------------------------------------

    for part in reversed(cleaned_parts):

        if contains_institution_keyword(part):
            return part

    # --------------------------------------------------------
    # If no explicit keyword exists, use the last meaningful
    # segment.
    # --------------------------------------------------------

    return cleaned_parts[-1]


# ============================================================
# CLEAN INSTITUTION NAME
# ============================================================

def clean_institution_name(institution):
    """
    Clean institution text without returning degree,
    field-of-study or education-year noise.
    """

    if not institution:
        return None

    institution = normalize_spaces(institution)

    # --------------------------------------------------------
    # Pipe-separated content.
    # --------------------------------------------------------

    if "|" in institution:
        institution = institution.split("|")[0].strip()

    # --------------------------------------------------------
    # If mixed with dash-separated education information,
    # identify the actual institution-bearing segment first.
    # --------------------------------------------------------

    if re.search(
        r"\s*[-–—]\s*",
        institution,
    ):
        mixed = extract_institution_from_mixed_line(
            institution
        )

        if mixed:
            institution = mixed

    # --------------------------------------------------------
    # Remove years.
    # --------------------------------------------------------

    institution = remove_education_years(
        institution
    )

    # --------------------------------------------------------
    # Remove qualification / degree.
    # --------------------------------------------------------

    institution = remove_qualification_prefix(
        institution
    )

    institution = remove_degree(
        institution
    )

    # --------------------------------------------------------
    # Remove leading "in".
    # --------------------------------------------------------

    institution = LEADING_IN_PATTERN.sub("", institution)

    # --------------------------------------------------------
    # Remove obvious field-of-study prefix.
    # --------------------------------------------------------

    institution = remove_field_of_study(
        institution
    )

    # --------------------------------------------------------
    # Remove residual year brackets / punctuation.
    # --------------------------------------------------------

    institution = EMPTY_PARENTHESES_PATTERN.sub("", institution)

    institution = remove_leading_noise(
        institution
    )

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

def _remove_recognized_university_from_block(
    block,
    university_result,
):
    """
    Remove only the detected university from its matching line.
    """

    if not block:
        return []

    cleaned_block = []

    university_line_index = None

    if university_result:
        university_line_index = university_result.get(
            "line_index"
        )

    for index, line in enumerate(block):

        if not isinstance(line, str):
            continue

        line = normalize_spaces(line)

        if not line:
            continue

        if (
            university_line_index is not None
            and index == university_line_index
        ):
            line = remove_university_content(
                line,
                university_result,
            )

            line = normalize_spaces(line)

        if line:
            cleaned_block.append(line)

    return cleaned_block


# ============================================================
# FIND EXPLICIT INSTITUTION CANDIDATES
# ============================================================


def find_institution_candidates(
    block,
    university_result=None,
):
    """
    Find explicit institution candidates.

    Remove the recognized university before institution
    extraction. Ignore qualification-only lines, but retain
    mixed lines when they contain an actual institution.
    """
    candidates = []

    if not block:
        return candidates

    working_block = _remove_recognized_university_from_block(
        block,
        university_result,
    )

    for line in working_block:
        if not isinstance(line, str):
            continue

        line = normalize_spaces(line)

        if not line:
            continue

        if is_board(line):
            continue

        if contains_university_wording(line):
            continue

        candidate = line

        # Qualification and degree lines may also contain words
        # such as "school". Extract the institution-bearing part
        # before accepting them as candidates.
        if is_degree_line(line):
            candidate = extract_institution_from_mixed_line(line)

            if not candidate:
                continue

            candidate = normalize_spaces(candidate)

        if not candidate:
            continue

        if is_board(candidate):
            continue

        if contains_university_wording(candidate):
            continue

        if is_degree_line(candidate):
            continue

        if contains_institution_keyword(candidate):
            candidates.append(candidate)

    return candidates

# ============================================================
# FALLBACK CANDIDATES
# ============================================================

def find_fallback_institution_candidates(
    block,
    university_result=None,
):
    """
    Find institution candidates without explicit keywords.
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

        cleaned = clean_institution_name(line)

        if not cleaned:
            continue

        if is_board(cleaned):
            continue

        if contains_university_wording(cleaned):
            continue

        if is_degree_line(cleaned):
            continue

        # Avoid field-of-study-only lines.
        lower = cleaned.lower()

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
            word == lower
            or lower.startswith(word)
            for word in field_noise
        ):
            continue

        # Comma-containing lines are useful fallbacks.
        if "," in cleaned:
            candidates.append(cleaned)

    return candidates


# ============================================================
# UNIVERSITY
# ============================================================


def extract_university_from_block(block):
    """
    Detect a university from an education block.

    Responsibilities:
    1. Detect universities using dictionary aliases or patterns.
    2. Preserve the detected university name.
    3. Remove graduation years from appended university text.
    4. Avoid appending degree information to the university.
    5. Preserve line_index for institution extraction.
    """

    if not block:
        return None

    for line_index, line in enumerate(block):

        if not isinstance(line, str):
            continue

        line = normalize_spaces(line)

        if not line:
            continue

        result = extract_university_alias(line)

        if not result:
            continue

        matched_end = result.get("end")

        if isinstance(matched_end, int):

            remainder = line[matched_end:].strip()

            # Remove separators between the university and
            # any remaining text.
            remainder = remainder.lstrip(
                " ,;:-–—|"
            ).strip()

            # Remove degree information from the remainder.
            degree_start = None

            for pattern in DEGREE_PATTERNS:
                match = re.search(
                    pattern,
                    remainder,
                    flags=re.IGNORECASE,
                )

                if match and (
                    degree_start is None
                    or match.start() < degree_start
                ):
                    degree_start = match.start()

            if degree_start is not None:
                remainder = remainder[:degree_start]

            # Critical fix:
            # Remove graduation years before appending
            # any remaining text to the university name.
            remainder = remove_years_from_university_remainder(
                remainder
            )

            remainder = normalize_spaces(remainder)
            remainder = remainder.strip(" ,;:-–—|.")

            # Append only meaningful non-year remainder text.
            if remainder:
                result["value"] = (
                    f"{result['value']}, {remainder}"
                )

        result["line_index"] = line_index

        return result

    return None



# ============================================================
# BACKWARD COMPATIBLE UNIVERSITY VALUE
# ============================================================

def extract_university(
    block,
    institution=None,
):
    result = extract_university_from_block(block)

    if not result:
        return None

    return result.get("value")


# ============================================================
# EXTRACT INSTITUTION
# ============================================================

def extract_institution(
    block,
    university_result=None,
):
    """
    Extract college / institute / school.

    University detection happens first and the detected
    university is removed before institution extraction.
    """

    if not block:
        return None

    if university_result is None:
        university_result = (
            extract_university_from_block(block)
        )

    # --------------------------------------------------------
    # Explicit institution candidates.
    # --------------------------------------------------------

    candidates = find_institution_candidates(
        block,
        university_result,
    )

    for candidate in candidates:

        cleaned = clean_institution_name(
            candidate
        )

        if not cleaned:
            continue

        if is_board(cleaned):
            continue

        if contains_university_wording(cleaned):
            continue

        if is_degree_line(cleaned):
            continue

        # Do not return field-only content.
        if (
            cleaned.lower()
            in {
                "computer science",
                "computer science and engineering",
                "information technology",
                "engineering",
                "computer applications",
            }
        ):
            continue

        return cleaned

    # --------------------------------------------------------
    # Fallback candidates.
    # --------------------------------------------------------

    fallback_candidates = (
        find_fallback_institution_candidates(
            block,
            university_result,
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

        if contains_university_wording(cleaned):
            continue

        if is_degree_line(cleaned):
            continue

        return cleaned

    return None


# ============================================================
# ALL EDUCATION ENTITIES
# ============================================================

def extract_education_institutions(block):
    """
    Extract university, institution and board.

    University is detected exactly once.
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
        extract_university_from_block(block)
    )

    university = None

    if university_result:
        university = university_result.get(
            "value"
        )

    # --------------------------------------------------------
    # INSTITUTION SECOND
    # --------------------------------------------------------

    institution = extract_institution(
        block,
        university_result,
    )

    # --------------------------------------------------------
    # BOARD
    # --------------------------------------------------------

    board = extract_board(block)

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

        [
            "B.Tech in Computer Science and Engineering - Kerala Institute of Technology (2020 - 2024)",
            "Computer Science and Engineering",
        ],

        [
            "Higher Secondary - Computer Science - Government Higher Secondary School (2018 - 2020)",
            "Central Board of Secondary Education",
        ],

        [
            "B.Tech Computer Science and Engineering",
            "Rajagiri School of Engineering",
            "APJ Abdul Kalam Technological University",
            "2022 - 2026",
        ],

        [
            "B.Tech Computer Science",
            "Visvesvaraya Technological University",
            "2017 - 2021",
        ],

        [
            "Bachelor of Engineering",
            "P.E.S Institute of Technology",
            "2012 - 2016",
        ],

        [
            "All India Senior School Certificate Exam",
            "Kendriya Vidyalaya Kalpetta, Kerala, India",
            "Central Board of Secondary Education",
            "2011 - 2012",
        ],

        [
            "VTU - B.Tech",
            "Computer Science and Engineering",
            "2019",
        ],

        [
            "B.Tech - VTU",
            "Computer Science and Engineering",
            "2019",
        ],

        [
            "ABC College - VTU - B.Tech",
            "Computer Science Engineering",
            "2019",
        ],
    ]

    for index, block in enumerate(
        test_blocks,
        start=1,
    ):

        result = extract_education_institutions(
            block
        )

        print(
            f"\n========== BLOCK {index} =========="
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
        
        
