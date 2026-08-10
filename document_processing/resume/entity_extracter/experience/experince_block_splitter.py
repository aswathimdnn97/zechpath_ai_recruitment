import re


DATE_PATTERN = re.compile(
    r"""
    (?:
        Jan|Feb|Mar|Apr|May|Jun|
        Jul|Aug|Sep|Oct|Nov|Dec
    )
    \s+
    \d{4}
    |
    \d{4}
    """,
    re.IGNORECASE | re.VERBOSE,
)


DATE_RANGE_PATTERN = re.compile(
    r"""
    (?:
        (?:Jan|Feb|Mar|Apr|May|Jun|
        Jul|Aug|Sep|Oct|Nov|Dec)
        \s+\d{4}
        |
        \d{4}
    )
    \s*
    [-–—]
    \s*
    (?:
        (?:Jan|Feb|Mar|Apr|May|Jun|
        Jul|Aug|Sep|Oct|Nov|Dec)
        \s+\d{4}
        |
        \d{4}
        |
        Present
        |
        Current
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def is_experience_start(line):
    """
    Determine whether a line looks like the beginning
    of an experience record.

    This is intentionally conservative.
    """

    if not isinstance(line, str):
        return False

    line = line.strip()

    if not line:
        return False

    # A date range is a strong experience signal.
    if DATE_RANGE_PATTERN.search(line):
        return True

    return False


def has_date(lines):
    """Return True if any line in lines contains a date range."""

    if not lines:
        return False

    return any(DATE_RANGE_PATTERN.search(line) for line in lines if isinstance(line, str))


def is_title_line(line):
    """Heuristic to detect title lines like 'Senior X — Company' or 'Title - Company'."""

    if not isinstance(line, str):
        return False

    # common separators between title and company
    if "—" in line or "–" in line or " - " in line or "—" in line:

        # require at least two alpha segments around the separator
        parts = re.split(r"[—–-]+", line)

        if len(parts) >= 2:
            left, right = parts[0].strip(), parts[1].strip()

            if left and right and re.search(r"[A-Za-z]", left) and re.search(r"[A-Za-z]", right):
                return True

    return False


def normalize_lines(lines):
    """
    Convert experience input into a simple list of strings.

    Handles both:

        ["line1", "line2"]

    and:

        [
            ["line1", "line2"],
            ["line3", "line4"]
        ]
    """

    if not lines:
        return []

    # --------------------------------------------------------
    # Already a string
    # --------------------------------------------------------

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

        # ----------------------------------------------------
        # Normal line
        # ----------------------------------------------------

        if isinstance(item, str):

            item = item.strip()

            if item:
                normalized.append(item)

        # ----------------------------------------------------
        # Existing block
        # ----------------------------------------------------

        elif isinstance(item, list):

            for line in item:

                if not isinstance(
                    line,
                    str
                ):
                    continue

                line = line.strip()

                if line:
                    normalized.append(
                        line
                    )

    return normalized


def split_experience_blocks(lines):
    """
    Split experience lines into logical experience blocks.

    Input:
        list[str]

    or:
        list[list[str]]

    Output:
        list[list[str]]
    """

    lines = normalize_lines(
        lines
    )

    if not lines:
        return []

    blocks = []

    current_block = []

    for line in lines:

        # ----------------------------------------------------
        # Date line handling
        # ----------------------------------------------------
        if is_experience_start(line):

            # If current block already contains a date, this signals a new experience
            if current_block and has_date(current_block):
                blocks.append(current_block)
                current_block = []

            # Otherwise, just append the date to the current block so title+date stay together
            current_block.append(line)
            continue

        # ----------------------------------------------------
        # Title line handling
        # If we detect a title and the current block already has a date,
        # then this is the start of a new experience block (title precedes its date).
        # ----------------------------------------------------
        if is_title_line(line) and current_block and has_date(current_block):
            blocks.append(current_block)
            current_block = [line]
            continue

        # ----------------------------------------------------
        # Default: append line to current block
        # ----------------------------------------------------
        current_block.append(line)

    # --------------------------------------------------------
    # Add final block
    # --------------------------------------------------------

    if current_block:
        blocks.append(
            current_block
        )

    return blocks
