import re

from document_processing.common.skill_cleaner import clean_skills


# ============================================================
# HEADER / METADATA PREFIXES
# ============================================================

METADATA_PREFIXES = (
    "location:",
    "employment:",
    "employment type:",
    "salary:",
    "experience:",
    "job id:",
    "availability:",
    "company:",
    "job title:",
    "position:",
    "role:",
)


# ============================================================
# JOB TITLE INFERENCE PATTERNS
# ============================================================
#
# These patterns are linguistic patterns, NOT technology names.
#
# They allow us to extract:
#
#   "We are looking for an entry-level Python Developer"
#       -> "Python Developer"
#
#   "Seeking a Backend Developer"
#       -> "Backend Developer"
#
#   "Hiring a Software Engineer"
#       -> "Software Engineer"
#
# No hard-coded technology list is used.
# ============================================================

JOB_TITLE_PATTERNS = [
    # We are looking for an entry-level Python Developer
    re.compile(
        r"\b(?:we\s+are\s+)?looking\s+for\s+(?:an?|the)\s+"
        r"(?:(?:entry[- ]level|junior|senior|lead|principal)\s+)?"
        r"(?P<title>[A-Za-z][A-Za-z0-9/&+.#,\- ]{2,80}?)"
        r"(?=\s+(?:to|who|that|with|for|at|in)\b|[.,]|$)",
        flags=re.IGNORECASE,
    ),

    # Seeking a Python Developer
    re.compile(
        r"\bseeking\s+(?:an?|the)\s+"
        r"(?:(?:entry[- ]level|junior|senior|lead|principal)\s+)?"
        r"(?P<title>[A-Za-z][A-Za-z0-9/&+.#,\- ]{2,80}?)"
        r"(?=\s+(?:to|who|that|with|for|at|in)\b|[.,]|$)",
        flags=re.IGNORECASE,
    ),

    # Hiring a Python Developer
    re.compile(
        r"\bhiring\s+(?:an?|the)\s+"
        r"(?:(?:entry[- ]level|junior|senior|lead|principal)\s+)?"
        r"(?P<title>[A-Za-z][A-Za-z0-9/&+.#,\- ]{2,80}?)"
        r"(?=\s+(?:to|who|that|with|for|at|in)\b|[.,]|$)",
        flags=re.IGNORECASE,
    ),

    # We need a Python Developer
    re.compile(
        r"\b(?:we\s+)?need\s+(?:an?|the)\s+"
        r"(?:(?:entry[- ]level|junior|senior|lead|principal)\s+)?"
        r"(?P<title>[A-Za-z][A-Za-z0-9/&+.#,\- ]{2,80}?)"
        r"(?=\s+(?:to|who|that|with|for|at|in)\b|[.,]|$)",
        flags=re.IGNORECASE,
    ),

    # Looking for Python Developer
    re.compile(
        r"\blooking\s+for\s+"
        r"(?:(?:an?|the)\s+)?"
        r"(?:(?:entry[- ]level|junior|senior|lead|principal)\s+)?"
        r"(?P<title>[A-Za-z][A-Za-z0-9/&+.#,\- ]{2,80}?)"
        r"(?=\s+(?:to|who|that|with|for|at|in)\b|[.,]|$)",
        flags=re.IGNORECASE,
    ),
]


# ============================================================
# CLEAN HEADER LINES
# ============================================================

def _clean_header_lines(header):
    """
    Clean and return meaningful header lines.
    """

    if not isinstance(header, list):
        return []

    return [
        str(line).strip()
        for line in header
        if str(line).strip()
    ]


# ============================================================
# CLEAN INFERRED JOB TITLE
# ============================================================

def _clean_job_title(title: str) -> str:
    """
    Clean a job title extracted from a natural-language sentence.

    Examples
    --------
    "Python Developer"
        -> "Python Developer"

    "entry-level Python Developer"
        -> "Python Developer"

    "Python Developer."
        -> "Python Developer"
    """

    if not isinstance(title, str):
        return ""

    title = title.strip()

    if not title:
        return ""

    # --------------------------------------------------------
    # Remove leading determiners
    # --------------------------------------------------------

    title = re.sub(
        r"^(?:an?|the)\s+",
        "",
        title,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Remove seniority modifiers.
    #
    # These normally describe the level rather than the core
    # job title.
    # --------------------------------------------------------

    title = re.sub(
        r"^(?:entry[- ]level|junior|senior|lead|principal)\s+",
        "",
        title,
        flags=re.IGNORECASE,
    )

    # --------------------------------------------------------
    # Remove trailing punctuation.
    # --------------------------------------------------------

    title = re.sub(
        r"[\s,;:|.\-–—]+$",
        "",
        title,
    )

    # --------------------------------------------------------
    # Normalize whitespace.
    # --------------------------------------------------------

    title = re.sub(
        r"\s+",
        " ",
        title,
    ).strip()

    return title


# ============================================================
# INFER JOB TITLE FROM TEXT
# ============================================================

def _infer_job_title(text: str) -> str:
    """
    Infer a job title from a natural-language JD statement.

    This uses linguistic patterns only and does not contain a
    technology dictionary.

    Examples
    --------
    "We are looking for an entry-level Python Developer to build..."
        -> "Python Developer"

    "Seeking a Backend Developer with experience..."
        -> "Backend Developer"
    """

    if not isinstance(text, str):
        return ""

    text = text.strip()

    if not text:
        return ""

    for pattern in JOB_TITLE_PATTERNS:

        match = pattern.search(text)

        if not match:
            continue

        title = match.group("title")

        title = _clean_job_title(title)

        if title:
            return title

    return ""


# ============================================================
# PARSE INLINE HEADER METADATA
# ============================================================

def _parse_inline_metadata(text):
    """
    Parse metadata stored together in one line.

    Example:

        Location: Kochi, Kerala | Employment: Full-time | Job ID: JD_EVAL_001

    Also supports:

        Kochi, Kerala | Employment: Full-time | Job ID: JD_EVAL_001
    """

    result = {
        "location": "",
        "employment_type": "",
        "salary": "",
        "availability": "",
        "job_id": "",
    }

    if not isinstance(text, str):
        return result

    text = text.strip()

    if not text:
        return result

    # --------------------------------------------------------
    # A plain header/company line such as:
    #
    #     TechNova Solutions
    #
    # must NOT be treated as location metadata.
    #
    # Only parse unlabeled content as location when it is an
    # actual metadata string containing pipe-delimited fields or
    # explicit metadata keywords.
    # --------------------------------------------------------

    text_lower = text.lower()

    has_inline_metadata_keywords = any(
        keyword in text_lower
        for keyword in (
            "location:",
            "employment:",
            "employment type:",
            "salary:",
            "availability:",
            "job id:",
            "job id",
            "employment type",
            "salary",
            "availability",
        )
    )

    parts = [
        part.strip()
        for part in text.split("|")
        if part.strip()
    ]

    if len(parts) <= 1 and not has_inline_metadata_keywords:
        return result

    location_parts = []

    for part in parts:

        lower_part = part.lower()

        # ----------------------------------------------------
        # Location
        # ----------------------------------------------------

        if lower_part.startswith("location:"):

            result["location"] = part.split(
                ":",
                1,
            )[1].strip()

        # ----------------------------------------------------
        # Employment
        # ----------------------------------------------------

        elif lower_part.startswith("employment type:"):

            result["employment_type"] = part.split(
                ":",
                1,
            )[1].strip()

        elif lower_part.startswith("employment:"):

            result["employment_type"] = part.split(
                ":",
                1,
            )[1].strip()

        # ----------------------------------------------------
        # Salary
        # ----------------------------------------------------

        elif lower_part.startswith("salary:"):

            result["salary"] = part.split(
                ":",
                1,
            )[1].strip()

        # ----------------------------------------------------
        # Availability
        # ----------------------------------------------------

        elif lower_part.startswith("availability:"):

            result["availability"] = part.split(
                ":",
                1,
            )[1].strip()

        # ----------------------------------------------------
        # Job ID
        # ----------------------------------------------------

        elif lower_part.startswith("job id:"):

            result["job_id"] = part.split(
                ":",
                1,
            )[1].strip()

        # ----------------------------------------------------
        # Unlabelled part
        #
        # Usually this is location.
        # ----------------------------------------------------

        else:

            location_parts.append(part)

    # --------------------------------------------------------
    # If location was not explicitly labelled
    # --------------------------------------------------------

    if not result["location"] and location_parts:

        result["location"] = location_parts[0]

    return result


# ============================================================
# EXTRACT HEADER ENTITIES
# ============================================================

def _extract_header_entities(header):
    """
    Extract job title, company and metadata from the JD header.

    Supported layouts
    -----------------

    Layout 1: Explicit labels

        Job Title: Python Developer
        Company: CodeNest Technologies
        Location: Kochi, Kerala

    Layout 2: Standard JD header

        Python Developer Trainee
        CodeNest Technologies
        Kochi, Kerala | Full-time | Job ID: JD_EVAL_001

    Layout 3: Natural-language title

        We are looking for an entry-level Python Developer
        CodeNest Technologies
        Kochi, Kerala | Full-time

    Important
    ---------
    The company does NOT need to have a "Company:" label.

    For a conventional JD header, the first meaningful line is
    treated as the job title and the next meaningful line is
    treated as the company.
    """

    header_lines = _clean_header_lines(header)

    result = {
        "job_title": "",
        "company": "",
        "location": "",
        "employment_type": "",
        "salary": "",
        "availability": "",
        "job_id": "",
    }

    if not header_lines:
        return result

    # ========================================================
    # FIRST PASS
    #
    # Extract explicitly labelled fields and metadata.
    # ========================================================

    remaining_lines = []

    for line in header_lines:

        lower_line = line.lower()

        # ----------------------------------------------------
        # Explicit Job Title
        # ----------------------------------------------------

        if (
            lower_line.startswith("job title:")
            or lower_line.startswith("position title:")
        ):

            result["job_title"] = line.split(
                ":",
                1,
            )[1].strip()

            continue

        # ----------------------------------------------------
        # Position
        # ----------------------------------------------------

        if lower_line.startswith("position:"):

            result["job_title"] = line.split(
                ":",
                1,
            )[1].strip()

            continue

        # ----------------------------------------------------
        # Role
        # ----------------------------------------------------

        if lower_line.startswith("role:"):

            result["job_title"] = line.split(
                ":",
                1,
            )[1].strip()

            continue

        # ----------------------------------------------------
        # Explicit Company
        # ----------------------------------------------------

        if (
            lower_line.startswith("company:")
            or lower_line.startswith("company name:")
        ):

            result["company"] = line.split(
                ":",
                1,
            )[1].strip()

            continue

        # ----------------------------------------------------
        # Employer
        # ----------------------------------------------------

        if lower_line.startswith("employer:"):

            result["company"] = line.split(
                ":",
                1,
            )[1].strip()

            continue

        # ----------------------------------------------------
        # Organization
        # ----------------------------------------------------

        if lower_line.startswith("organization:"):

            result["company"] = line.split(
                ":",
                1,
            )[1].strip()

            continue

        # ----------------------------------------------------
        # Parse inline metadata
        # ----------------------------------------------------

        metadata = _parse_inline_metadata(line)

        metadata_found = any(
            value
            for value in metadata.values()
        )

        if metadata_found:

            for key, value in metadata.items():

                if value:
                    result[key] = value

            continue

        # ----------------------------------------------------
        # Normal header line
        # ----------------------------------------------------

        remaining_lines.append(line)

    # ========================================================
    # SECOND PASS
    #
    # Layout-based extraction.
    #
    # Example:
    #
    #   Python Developer Trainee
    #   CodeNest Technologies
    #
    # becomes:
    #
    #   job_title = Python Developer Trainee
    #   company   = CodeNest Technologies
    # ========================================================

    meaningful_lines = []

    for line in remaining_lines:

        line = line.strip()

        if not line:
            continue

        lower_line = line.lower()

        # Ignore any remaining metadata lines.

        if any(
            lower_line.startswith(prefix)
            for prefix in METADATA_PREFIXES
        ):
            continue

        meaningful_lines.append(line)

    # ========================================================
    # LAYOUT-BASED JOB TITLE
    # ========================================================

    if not result["job_title"]:

        # ----------------------------------------------------
        # First try natural-language title inference.
        # ----------------------------------------------------

        for line in meaningful_lines:

            inferred_title = _infer_job_title(line)

            if inferred_title:

                result["job_title"] = inferred_title
                break

        # ----------------------------------------------------
        # If no natural-language pattern matched, the first
        # meaningful header line is the conventional JD title.
        # ----------------------------------------------------

        if not result["job_title"] and meaningful_lines:

            result["job_title"] = meaningful_lines[0]

    # ========================================================
    # LAYOUT-BASED COMPANY
    # ========================================================

    if not result["company"]:

        title_index = -1

        # ----------------------------------------------------
        # Find the line used as the title.
        # ----------------------------------------------------

        for index, line in enumerate(meaningful_lines):

            if line == result["job_title"]:

                title_index = index
                break

        # ----------------------------------------------------
        # The company is normally the next meaningful line
        # after the title.
        # ----------------------------------------------------

        if (
            title_index >= 0
            and title_index + 1 < len(meaningful_lines)
        ):

            candidate_company = meaningful_lines[
                title_index + 1
            ].strip()

            # Make sure it is not another natural-language
            # sentence such as:
            #
            # "We are looking for..."
            #
            candidate_lower = candidate_company.lower()

            if not candidate_lower.startswith(
                (
                    "we are looking",
                    "we're looking",
                    "looking for",
                    "seeking",
                    "hiring",
                    "we need",
                )
            ):

                result["company"] = candidate_company

    return result



# ============================================================
# CLEAN RESPONSIBILITIES
# ============================================================

def _clean_responsibilities(responsibilities):
    """
    Remove accidental dataset/footer text from responsibilities.
    """

    if not isinstance(
        responsibilities,
        list,
    ):
        return []

    cleaned = []

    for item in responsibilities:

        text = str(item).strip()

        if not text:
            continue

        lower_text = text.lower()

        # ----------------------------------------------------
        # Ignore evaluation dataset/footer text
        # ----------------------------------------------------

        if (
            "zechpath ats evaluation dataset"
            in lower_text
        ):
            continue

        if (
            "fictional job description"
            in lower_text
        ):
            continue

        cleaned.append(text)

    return cleaned


# ============================================================
# NORMALIZE EXPERIENCE
# ============================================================

def _normalize_experience(experience):
    """
    Convert raw JD experience text into structured data.

    Examples
    --------
    "0-1 year experience, internship or relevant project experience acceptable."
        ->
        {
            "minimum_years": 0,
            "maximum_years": 1,
            "description": "..."
        }

    "2-3 years of experience"
        ->
        {
            "minimum_years": 2,
            "maximum_years": 3,
            "description": "..."
        }

    "2+ years experience"
        ->
        {
            "minimum_years": 2,
            "maximum_years": None,
            "description": "..."
        }

    "3 years experience"
        ->
        {
            "minimum_years": 3,
            "maximum_years": None,
            "description": "..."
        }
    """

    if not isinstance(experience, list):
        experience = [experience]

    normalized = []

    for item in experience:

        if not isinstance(item, str):
            continue

        text = item.strip()

        if not text:
            continue

        minimum_years = None
        maximum_years = None

        # ----------------------------------------------------
        # Match experience ranges
        #
        # Examples:
        # 0-1 year
        # 1-2 years
        # 2 to 3 years
        # ----------------------------------------------------

        range_match = re.search(
            r"\b(\d+(?:\.\d+)?)\s*"
            r"(?:-|–|—|to)\s*"
            r"(\d+(?:\.\d+)?)\s*"
            r"years?\b",
            text,
            flags=re.IGNORECASE,
        )

        if range_match:

            minimum_years = float(
                range_match.group(1)
            )

            maximum_years = float(
                range_match.group(2)
            )

        else:

            # ------------------------------------------------
            # Match minimum experience
            #
            # Examples:
            # 2+ years
            # 3 years experience
            # ------------------------------------------------

            minimum_match = re.search(
                r"\b(\d+(?:\.\d+)?)\s*\+?\s*"
                r"years?\b",
                text,
                flags=re.IGNORECASE,
            )

            if minimum_match:

                minimum_years = float(
                    minimum_match.group(1)
                )

        # ----------------------------------------------------
        # Convert 0.0 -> 0 and 1.0 -> 1
        # ----------------------------------------------------

        if (
            minimum_years is not None
            and minimum_years.is_integer()
        ):
            minimum_years = int(minimum_years)

        if (
            maximum_years is not None
            and maximum_years.is_integer()
        ):
            maximum_years = int(maximum_years)

        normalized.append(
            {
                "minimum_years": minimum_years,
                "maximum_years": maximum_years,
                "description": text,
            }
        )

    return normalized

# ============================================================
# EXTRACT ENTITIES
# ============================================================

def extract_entities(sections):

    if not isinstance(sections, dict):
        sections = {}

    entities = {}

    # ========================================================
    # HEADER
    # ========================================================

    header = sections.get(
        "header",
        [],
    )

    header_entities = _extract_header_entities(
        header
    )

    # ========================================================
    # JOB TITLE
    # ========================================================

    explicit_job_title = " ".join(
        sections.get(
            "job_title",
            [],
        )
    ).strip()

    # First priority:
    # explicit extracted job title
    #
    # Second:
    # header job title
    #
    # Third:
    # infer from job summary
    #

    entities["job_title"] = (
        explicit_job_title
        or header_entities["job_title"]
    )

    if not entities["job_title"]:

        job_summary = " ".join(
            sections.get(
                "job_summary",
                [],
            )
        ).strip()

        entities["job_title"] = _infer_job_title(
            job_summary
        )

    # ========================================================
    # COMPANY
    # ========================================================

    explicit_company = " ".join(
        sections.get(
            "company",
            [],
        )
    ).strip()

    entities["company"] = (
        explicit_company
        or header_entities["company"]
    )

    # IMPORTANT:
    # Do NOT infer a company from the job description.
    #
    # If there is no explicit evidence, company remains "".

    # ========================================================
    # LOCATION
    #
    # Important:
    # Your parser currently sometimes puts:
    #
    # Kochi, Kerala | Employment: Full-time | Job ID: ...
    #
    # inside sections["location"].
    #
    # Therefore parse it again here.
    # ========================================================

    explicit_location = " ".join(
        sections.get(
            "location",
            [],
        )
    ).strip()

    location_metadata = _parse_inline_metadata(
        explicit_location
    )

    entities["location"] = (
        location_metadata["location"]
        or header_entities["location"]
        or explicit_location
    )

    # ========================================================
    # EMPLOYMENT TYPE
    # ========================================================

    explicit_employment = " ".join(
        sections.get(
            "employment_type",
            [],
        )
    ).strip()

    entities["employment_type"] = (
        explicit_employment
        or location_metadata["employment_type"]
        or header_entities["employment_type"]
    )

    # ========================================================
    # SALARY
    # ========================================================

    explicit_salary = " ".join(
        sections.get(
            "salary",
            [],
        )
    ).strip()

    entities["salary"] = (
        explicit_salary
        or location_metadata["salary"]
        or header_entities["salary"]
    )

    # ========================================================
    # AVAILABILITY
    # ========================================================

    explicit_availability = " ".join(
        sections.get(
            "availability",
            [],
        )
    ).strip()

    entities["availability"] = (
        explicit_availability
        or location_metadata["availability"]
        or header_entities["availability"]
    )

    # ========================================================
    # JOB ID
    # ========================================================

    entities["job_id"] = (
        location_metadata["job_id"]
        or header_entities["job_id"]
    )

    # ========================================================
    # JOB SUMMARY
    # ========================================================

    entities["job_summary"] = " ".join(
        sections.get(
            "job_summary",
            [],
        )
    ).strip()

    # ========================================================
    # RESPONSIBILITIES
    # ========================================================

    entities["responsibilities"] = (
        _clean_responsibilities(
            sections.get(
                "responsibilities",
                [],
            )
        )
    )

    # ========================================================
    # REQUIRED SKILLS
    # ========================================================

    required_skills = sections.get(
        "required_skills",
        [],
    )

    if not isinstance(required_skills, list):
        required_skills = [required_skills]

    entities["required_skills"] = clean_skills(
        required_skills
    )

    # ========================================================
    # PREFERRED SKILLS
    # ========================================================

    preferred_skills = sections.get(
        "preferred_skills",
        [],
    )

    if not isinstance(preferred_skills, list):
        preferred_skills = [preferred_skills]

    entities["preferred_skills"] = clean_skills(
        preferred_skills
    )

    # ========================================================
    # EDUCATION
    # ========================================================

    entities["education"] = sections.get(
        "education",
        [],
    )

    # ========================================================
    # SOFT SKILLS
    # ========================================================

    entities["soft_skills"] = sections.get(
        "soft_skills",
        [],
    )

   # ========================================================
    # EXPERIENCE
    # ========================================================

    entities["experience"] = _normalize_experience(
        sections.get(
            "experience",
            [],
        )
    )

    # ========================================================
    # REQUIREMENTS
    # ========================================================

    entities["requirements"] = sections.get(
        "requirements",
        [],
    )

    return entities
