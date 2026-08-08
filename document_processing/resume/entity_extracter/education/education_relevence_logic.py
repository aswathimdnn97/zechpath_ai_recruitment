"""
education_relevance_logic.py

Determine whether text belongs to an education record.

Responsibilities
----------------
1. Calculate education relevance score.
2. Detect degree/qualification keywords.
3. Detect institution keywords.
4. Detect education boards.
5. Detect fields of study.
6. Detect graduation years/date ranges.
7. Detect academic scores such as CGPA/percentage.
8. Reject obvious non-education content.
9. Classify text as:
       HIGH
       MEDIUM
       LOW
       NONE

This module does NOT extract:
    - degree_type
    - institution
    - field_of_study
    - graduation_year

Those responsibilities belong to the respective extractors.
"""

import re



# =========================================================
# KEYWORD DEFINITIONS
# =========================================================

DEGREE_KEYWORDS = [

    # Bachelor
    "bachelor",
    "b.tech",
    "btech",
    "b.e",
    "b.e.",
    "bsc",
    "b.sc",
    "bca",
    "b.c.a",
    "bba",
    "b.b.a",
    "b.com",
    "bcom",
    "b.a",
    "ba",

    # Master
    "master",
    "m.tech",
    "mtech",
    "m.e",
    "m.e.",
    "msc",
    "m.sc",
    "mca",
    "m.c.a",
    "mba",
    "m.b.a",
    "m.com",
    "mcom",
    "m.a",
    "ma",

    # Doctorate
    "phd",
    "ph.d",
    "doctor of philosophy",
    "doctorate",

    # Other
    "associate",
    "diploma",
    "certificate",
    "certification",

]


SCHOOL_QUALIFICATION_KEYWORDS = [

    "secondary",
    "senior secondary",
    "higher secondary",
    "senior school",
    "school certificate",
    "all india senior school certificate",
    "all india secondary school examination",
    "intermediate",
    "class x",
    "class xii",
    "10th",
    "12th",
    "sslc",
    "hsc",
    "plus two",
    "matriculation",

]


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


BOARD_KEYWORDS = [

    "central board of secondary education",
    "cbse",
    "state board",
    "board of secondary education",
    "kerala board",
    "board of education",
    "council for the indian school certificate examinations",
    "icse",
    "isc",

]


FIELD_KEYWORDS = [

    "computer science",
    "computer engineering",
    "computer application",
    "information technology",
    "electronics",
    "electrical",
    "mechanical",
    "civil engineering",
    "chemical engineering",
    "biotechnology",
    "business administration",
    "business",
    "commerce",
    "management",
    "mathematics",
    "physics",
    "chemistry",
    "biology",
    "economics",
    "accounting",
    "finance",
    "arts",
    "science",
    "engineering",

]


ACADEMIC_SCORE_KEYWORDS = [

    "cgpa",
    "gpa",
    "sgpa",
    "percentage",
    "percent",
    "aggregate",
    "marks obtained",
    "score",
    "grade",
    "marks",

]


EDUCATION_CONTEXT_KEYWORDS = [

    "education",
    "academic",
    "qualification",
    "qualifications",
    "graduation",
    "graduated",
    "degree",
    "study",
    "studied",

]


# =========================================================
# NON-EDUCATION KEYWORDS
# =========================================================

NON_EDUCATION_KEYWORDS = [

    "work experience",
    "professional experience",
    "employment",
    "responsibilities",
    "projects",
    "project",
    "skills",
    "technical skills",
    "experience",
    "work history",
    "certifications",

]


# =========================================================
# REGEX PATTERNS
# =========================================================

YEAR_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\b"
)


DATE_RANGE_PATTERN = re.compile(
    r"\b(?:19|20)\d{2}\s*"
    r"[-–—]\s*"
    r"(?:19|20)\d{2}\b",
    re.IGNORECASE
)


ACADEMIC_SCORE_PATTERN = re.compile(
    r"\b(?:cgpa|gpa|sgpa|percentage|percent|"
    r"marks|score|aggregate)\b",
    re.IGNORECASE
)


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_text(text):
    """
    Normalize text before analysis.
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

    return text.strip().lower()


# =========================================================
# KEYWORD MATCH
# =========================================================

def contains_keyword(
    text,
    keywords
):
    """
    Return True if any keyword exists in text.
    """

    return any(
        keyword in text
        for keyword in keywords
    )


# =========================================================
# DEGREE DETECTION
# =========================================================

def has_degree_keyword(text):
    """
    Detect degree/qualification keywords.
    """

    return contains_keyword(
        text,
        DEGREE_KEYWORDS
    )


def has_school_qualification(text):
    """
    Detect school-level qualifications.
    """

    return contains_keyword(
        text,
        SCHOOL_QUALIFICATION_KEYWORDS
    )


# =========================================================
# INSTITUTION DETECTION
# =========================================================

def has_institution_keyword(text):
    """
    Detect university, college, institute, school, etc.
    """

    return contains_keyword(
        text,
        INSTITUTION_KEYWORDS
    )


# =========================================================
# BOARD DETECTION
# =========================================================

def has_board_keyword(text):
    """
    Detect education board.
    """

    return contains_keyword(
        text,
        BOARD_KEYWORDS
    )


# =========================================================
# FIELD DETECTION
# =========================================================

def has_field_keyword(text):
    """
    Detect common fields of study.
    """

    return contains_keyword(
        text,
        FIELD_KEYWORDS
    )


# =========================================================
# YEAR DETECTION
# =========================================================

def has_year(text):
    """
    Detect a four-digit year.
    """

    return bool(
        YEAR_PATTERN.search(text)
    )


def has_date_range(text):
    """
    Detect education date range.

    Examples
    --------
    2018-2022
    2018 - 2022
    2018–2022
    """

    return bool(
        DATE_RANGE_PATTERN.search(text)
    )


# =========================================================
# SCORE DETECTION
# =========================================================

def has_academic_score(text):
    """
    Detect CGPA, GPA, percentage, marks, etc.
    """

    return bool(
        ACADEMIC_SCORE_PATTERN.search(text)
    )


# =========================================================
# NON-EDUCATION DETECTION
# =========================================================

def has_non_education_keyword(text):
    """
    Detect obvious non-education sections.
    """

    return contains_keyword(
        text,
        NON_EDUCATION_KEYWORDS
    )


# =========================================================
# LINE RELEVANCE SCORE
# =========================================================

def calculate_relevance_score(text):
    """
    Calculate education relevance score.

    Scoring
    -------
    Degree / qualification       +4
    Institution                 +4
    School qualification        +4
    Field of study              +3
    Education board             +3
    Date range                  +2
    Year                        +1
    Academic score              +2
    Education context           +2
    Non-education keyword       -5

    Returns
    -------
    int
    """

    text = normalize_text(text)

    if not text:
        return 0

    score = 0

    # -----------------------------------------------------
    # Degree
    # -----------------------------------------------------

    if has_degree_keyword(text):

        score += 4

    # -----------------------------------------------------
    # School qualification
    # -----------------------------------------------------

    if has_school_qualification(text):

        score += 4

    # -----------------------------------------------------
    # Institution
    # -----------------------------------------------------

    if has_institution_keyword(text):

        score += 4

    # -----------------------------------------------------
    # Field
    # -----------------------------------------------------

    if has_field_keyword(text):

        score += 3

    # -----------------------------------------------------
    # Board
    # -----------------------------------------------------

    if has_board_keyword(text):

        score += 3

    # -----------------------------------------------------
    # Date range
    # -----------------------------------------------------

    if has_date_range(text):

        score += 2

    # -----------------------------------------------------
    # Year
    # -----------------------------------------------------

    elif has_year(text):

        score += 1

    # -----------------------------------------------------
    # Academic score
    # -----------------------------------------------------

    if has_academic_score(text):

        score += 2

    # -----------------------------------------------------
    # Education context
    # -----------------------------------------------------

    if contains_keyword(
        text,
        EDUCATION_CONTEXT_KEYWORDS
    ):

        score += 2

    # -----------------------------------------------------
    # Non-education penalty
    # -----------------------------------------------------

    if has_non_education_keyword(text):

        score -= 5

    return max(
        score,
        0
    )


# =========================================================
# RELEVANCE LEVEL
# =========================================================

def get_relevance_level(score):
    """
    Convert numerical score into relevance level.

    Score
    -----
    >= 6   HIGH
    3-5    MEDIUM
    1-2    LOW
    0      NONE
    """

    if score >= 6:

        return "HIGH"

    if score >= 3:

        return "MEDIUM"

    if score >= 1:

        return "LOW"

    return "NONE"


# =========================================================
# MAIN LINE ANALYZER
# =========================================================

def analyze_education_line(text):
    """
    Analyze one education line.

    Returns
    -------
    dict
    """

    score = calculate_relevance_score(
        text
    )

    level = get_relevance_level(
        score
    )

    return {

        "text": text,

        "score": score,

        "relevance": level,

        "signals": {

            "degree":
                has_degree_keyword(
                    normalize_text(text)
                ),

            "school_qualification":
                has_school_qualification(
                    normalize_text(text)
                ),

            "institution":
                has_institution_keyword(
                    normalize_text(text)
                ),

            "field":
                has_field_keyword(
                    normalize_text(text)
                ),

            "board":
                has_board_keyword(
                    normalize_text(text)
                ),

            "year":
                has_year(
                    normalize_text(text)
                ),

            "date_range":
                has_date_range(
                    normalize_text(text)
                ),

            "academic_score":
                has_academic_score(
                    normalize_text(text)
                ),

        }

    }


# =========================================================
# IS EDUCATION RELEVANT
# =========================================================

def is_education_relevant(
    text,
    threshold=3
):
    """
    Return True when text is education-related.

    Default threshold = 3.

    This allows individual lines such as:

        Computer Science
        2019
        CGPA: 8.5

    to be retained when processed together with
    an education block.
    """

    score = calculate_relevance_score(
        text
    )

    return score >= threshold


# =========================================================
# FILTER EDUCATION LINES
# =========================================================

def filter_education_lines(
    lines,
    threshold=1
):
    """
    Filter potentially education-related lines.

    Parameters
    ----------
    lines : list[str]

    threshold : int
        Minimum relevance score.

    Returns
    -------
    list[str]
    """

    if not lines:
        return []

    filtered = []

    for line in lines:

        if not line:
            continue

        score = calculate_relevance_score(
            line
        )

        if score >= threshold:

            filtered.append(
                line
            )

    return filtered


# =========================================================
# FILTER EDUCATION BLOCKS
# =========================================================

def filter_education_blocks(
    blocks,
    threshold=3
):
    """
    Filter education blocks based on combined
    relevance.

    This is preferred over filtering individual
    lines because education information is often
    distributed across multiple lines.

    Example
    -------
    [
        "Bachelor of Engineering",
        "P.E.S Institute of Technology",
        "Computer Science",
        "2012-2016"
    ]

    is treated as one education record.
    """

    if not blocks:
        return []

    relevant_blocks = []

    for block in blocks:

        if not block:
            continue

        combined_text = " ".join(
            block
        )

        score = calculate_relevance_score(
            combined_text
        )

        if score >= threshold:

            relevant_blocks.append(
                block
            )

    return relevant_blocks


# =========================================================
# BLOCK ANALYSIS
# =========================================================

def analyze_education_block(
    block
):
    """
    Analyze a complete education block.

    Returns
    -------
    dict
    """

    if not block:

        return {

            "block": [],
            "score": 0,
            "relevance": "NONE",

        }

    combined_text = " ".join(
        block
    )

    score = calculate_relevance_score(
        combined_text
    )

    return {

        "block": block,

        "score": score,

        "relevance":
            get_relevance_level(
                score
            ),

    }


# =========================================================
# TESTING
# =========================================================

if __name__ == "__main__":

    test_lines = [

        "Bachelor of Engineering (B.E)",

        "P.E.S Institute of Technology, Bangalore",

        "Computer Science and Engineering",

        "2012-2016",

        "CGPA : 8.5",

        "Central Board of Secondary Education",

        "Kendriya Vidyalaya Kalpetta, Kerala",

        "Developed a full-stack web application",

        "Python, React, PostgreSQL",

        "Software Developer",

    ]

    print(
        "\nEDUCATION LINE ANALYSIS"
    )

    print(
        "-" * 70
    )

    for line in test_lines:

        result = analyze_education_line(
            line
        )

        print(
            f"\nText       : {line}"
        )

        print(
            f"Score      : {result['score']}"
        )

        print(
            f"Relevance  : {result['relevance']}"
        )

        print(
            f"Signals    : {result['signals']}"
        )


    # -----------------------------------------------------
    # Block test
    # -----------------------------------------------------

    education_block = [

        "Bachelor of Engineering (B.E)",

        "P.E.S Institute of Technology, "
        "Bangalore South Campus, India",

        "Visvesvaraya Technological University, "
        "Karnataka, India",

        "Computer Science and Engineering",

        "2012-2016",

        "Aggregate Score : 64.2",

    ]

    print(
        "\n\nEDUCATION BLOCK ANALYSIS"
    )

    result = analyze_education_block(
        education_block
    )

    print(
        result
    )
