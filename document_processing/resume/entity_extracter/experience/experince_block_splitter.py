"""
experience_block_splitter.py

Responsibilities
----------------
1. Split experience section into logical experience blocks.
2. Preserve title/company/location/date lines.
3. Keep description/responsibility lines inside the correct block.
4. Support:
       Title - Company
       Company - Location
       Company | Location | Dates
       Title | Company | Dates
       Company
       Location
       Dates
5. Do not split a block merely because a description line
   contains a dash.
"""

import re


# ============================================================
# DATE PATTERNS
# ============================================================

MONTH_PATTERN = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)

DATE_TOKEN_PATTERN = (
    rf"(?:"
    rf"{MONTH_PATTERN}\s+\d{{4}}"
    rf"|"
    rf"\d{{4}}"
    rf")"
)

DATE_RANGE_PATTERN = re.compile(
    rf"""
    {DATE_TOKEN_PATTERN}
    \s*
    [-–—\uFFFD]
    \s*
    (?:
        {DATE_TOKEN_PATTERN}
        |
        Present
        |
        Current
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# DATE HELPERS
# ============================================================

def is_date_line(line):
    """
    Return True if the line contains a date range.
    """

    if not isinstance(line, str):
        return False

    line = line.strip()

    if not line:
        return False

    return bool(
        DATE_RANGE_PATTERN.search(line)
    )


def has_date(lines):
    """
    Return True if any line contains an experience date range.
    """

    if not lines:
        return False

    return any(
        is_date_line(line)
        for line in lines
        if isinstance(line, str)
    )


# Backward compatibility
def is_experience_start(line):
    """
    Determine whether a line is a strong experience boundary.

    A date range is treated as the strongest signal.
    """

    return is_date_line(line)


# ============================================================
# TITLE DETECTION
# ============================================================

TITLE_KEYWORDS = {
    "developer",
    "engineer",
    "programmer",
    "analyst",
    "manager",
    "consultant",
    "architect",
    "specialist",
    "scientist",
    "designer",
    "administrator",
    "administrator",
    "intern",
    "trainee",
    "lead",
    "senior",
    "junior",
    "associate",
    "director",
    "officer",
    "executive",
    "assistant",
    "developer",
}


def is_title_line(line):
    """
    Detect a title/company line.

    Examples:
        Python Developer - CodeNest Technologies
        Senior Developer — ABC Technologies

    This function intentionally does NOT classify:

        CodeNest Technologies - Kochi, Kerala

    as a title line because the right side looks like a location.
    """

    if not isinstance(line, str):
        return False

    text = line.strip()

    if not text:
        return False

    separators = [
        " - ",
        " – ",
        " — ",
        " | ",
    ]

    for separator in separators:

        if separator not in text:
            continue

        parts = [
            part.strip()
            for part in text.split(
                separator,
                1
            )
        ]

        if len(parts) != 2:
            continue

        left, right = parts

        if not left or not right:
            continue

        left_lower = left.lower()

        # A title normally contains one of these words.
        if any(
            keyword in left_lower.split()
            or keyword in left_lower
            for keyword in TITLE_KEYWORDS
        ):
            return True

        right_lower = right.lower()
        if (
            any(
                keyword in right_lower.split()
                or keyword in right_lower
                for keyword in TITLE_KEYWORDS
            )
            and not any(
                keyword in left_lower.split()
                or keyword in left_lower
                for keyword in TITLE_KEYWORDS
            )
        ):
            return True

    return False


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_lines(lines):
    """
    Convert experience input into a flat list of strings.

    Supports:

        ["line1", "line2"]

    and:

        [
            ["line1", "line2"],
            ["line3", "line4"]
        ]
    """

    if not lines:
        return []

    if isinstance(lines, str):

        return [
            line.strip()
            for line in lines.splitlines()
            if line.strip()
        ]

    if not isinstance(lines, list):
        return []

    normalized = []

    for item in lines:

        if isinstance(item, str):

            line = item.strip()

            if line:
                normalized.append(line)

        elif isinstance(item, list):

            for sub_item in item:

                if not isinstance(
                    sub_item,
                    str
                ):
                    continue

                line = sub_item.strip()

                if line:
                    normalized.append(line)

    return normalized


# ============================================================
# EXPERIENCE BLOCK SPLITTER
# ============================================================

def split_experience_blocks(lines):
    """
    Split experience section into logical experience blocks.

    Important behavior
    -------------------
    A date range starts a new experience only when the current
    block already contains a date.

    This allows:

        Python Developer
        CodeNest Technologies - Kochi, Kerala
        Jan 2024 - Jun 2024

    to remain one block.

    It also allows:

        CodeNest Technologies - Kochi, Kerala
        Jan 2024 - Jun 2024
        description...

        BluePeak Digital Labs - Calicut, Kerala
        Jul 2023 - Dec 2023
        description...

    to become two blocks.
    """

    lines = normalize_lines(lines)

    if not lines:
        return []

    blocks = []

    current_block = []

    for line in lines:

        # ----------------------------------------------------
        # Date line
        # ----------------------------------------------------

        if is_date_line(line):

            if (
                current_block
                and has_date(current_block)
            ):
                blocks.append(
                    current_block
                )

                current_block = []

            current_block.append(line)

            continue

        # ----------------------------------------------------
        # Title line
        #
        # A title line appearing after an already completed
        # date-containing block is a strong new-record signal.
        # ----------------------------------------------------

        if (
            is_title_line(line)
            and current_block
            and has_date(current_block)
        ):

            blocks.append(
                current_block
            )

            current_block = [
                line
            ]

            continue

        # ----------------------------------------------------
        # Normal continuation
        # ----------------------------------------------------

        current_block.append(line)

    # --------------------------------------------------------
    # Final block
    # --------------------------------------------------------

    if current_block:

        blocks.append(
            current_block
        )

    return blocks


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":

    experience = [

        "Python Developer",

        "CodeNest Technologies - Kochi, Kerala",

        "Jan 2024 - Jun 2024",

        "Developed FastAPI endpoints for candidate workflows.",

        "Designed PostgreSQL tables.",

        "Built Pydantic request and response schemas.",

        "Wrote pytest cases.",

        "Used Git and pull requests for source control.",

        "BluePeak Digital Labs - Calicut, Kerala",

        "Jul 2023 - Dec 2023",

        "Implemented Django modules.",

    ]

    blocks = split_experience_blocks(
        experience
    )

    for index, block in enumerate(
        blocks,
        start=1
    ):

        print(
            f"\n========== BLOCK {index} =========="
        )

        for line in block:
            print(line)