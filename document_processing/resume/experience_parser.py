import re

DATE_RANGE_RE = re.compile(
    r"\b("
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
    r"\s+\d{4}"
    r"|\d{4}"
    r")\s*(?:[-–—]|to)\s*"
    r"(Present|Current|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}|\d{4})",
    re.IGNORECASE,
)


def _is_noise(line):
    return (
        len(line.strip()) < 3
        or re.fullmatch(r"[^A-Za-z0-9]+", line.strip()) is not None
    )


def _looks_like_title(line):
    if _is_noise(line):
        return False

    lower = line.lower()

    # Do not use responsibility sentences as job titles.
    if re.match(
        r"^(led|developed|created|implemented|reviewed|managed|"
        r"built|designed|worked|responsible|coordinated|prepared|"
        r"documented|performed|handled|completed|executed|updated|"
        r"supported|assisted)\b",
        lower,
    ):
        return False

    return len(line.split()) <= 10


def split_title_company(line):
    """Strip company names from title-company patterns like 'Backend Trainee - Code Nest Academy'."""
    if not isinstance(line, str):
        return line

    text = line.strip()
    if not text:
        return text

    for separator in [" - ", " – ", " — ", " | "]:
        if separator not in text:
            continue

        left, right = [part.strip() for part in text.split(separator, 1)]
        if not left or not right:
            continue

        left_lower = left.lower()
        right_lower = right.lower()

        if re.search(r"(developer|engineer|analyst|manager|consultant|architect|specialist|scientist|intern|trainee|lead|assistant|designer)", left_lower) and not re.search(r"(developer|engineer|analyst|manager|consultant|architect|specialist|scientist|intern|trainee|lead|assistant|designer)", right_lower):
            return left

    return text


def parse_experience_lines(lines):
    """
    Parses records around date ranges without relying on a fixed template.
    """
    records = []
    date_indexes = [
        index for index, line in enumerate(lines)
        if DATE_RANGE_RE.search(line)
    ]

    for position, date_index in enumerate(date_indexes):
        next_date = (
            date_indexes[position + 1]
            if position + 1 < len(date_indexes)
            else len(lines)
        )

        block_start = date_indexes[position - 1] if position else 0
        block = lines[block_start:next_date]
        date_line = lines[date_index]

        before_date = lines[block.index(date_line):] if date_line in block else []
        preceding = lines[max(0, date_index - 3):date_index]

        title = None
        company = None

        # ----------------------------------------------------
        # TITLE / COMPANY
        # ----------------------------------------------------
        #
        # Common resume structure:
        #
        #     Job Title
        #     Company
        #     Date Range
        #
        # Therefore, when title and company are on separate
        # lines immediately before the date, the last line
        # is normally the company and the line before it is
        # normally the title.
        #
        # For combined formats such as:
        #
        #     Backend Trainee - Code Nest Academy
        #
        # split_title_company() separates the title first.
        # ----------------------------------------------------

        cleaned_preceding = []

        for line in preceding:

            if not isinstance(line, str):
                continue

            if _is_noise(line):
                continue

            cleaned = split_title_company(line)

            if not cleaned:
                continue

            cleaned_preceding.append(
                cleaned.strip()
            )

        if cleaned_preceding:

            # ------------------------------------------------
            # Case 1:
            # Title - Company
            # ------------------------------------------------

            combined_line = preceding[-1]

            if isinstance(combined_line, str):

                split_title = split_title_company(
                    combined_line
                )

                if split_title != combined_line.strip():

                    title = split_title

                    remaining = [
                        item
                        for item in cleaned_preceding
                        if item != title
                    ]

                    if remaining:
                        company = remaining[-1]

                else:

                    # ----------------------------------------
                    # Case 2:
                    # Separate lines:
                    #
                    # Title
                    # Company
                    # Date
                    # ----------------------------------------

                    if len(cleaned_preceding) >= 2:

                        title = cleaned_preceding[-2]
                        company = cleaned_preceding[-1]

                    else:

                        # Only one preceding line exists.
                        # Keep it as title because there is
                        # insufficient evidence to identify a
                        # separate company.
                        title = cleaned_preceding[-1]

        description = [
            line for line in lines[date_index + 1:next_date]
            if not _is_noise(line)
        ]

        records.append({
            "title": title,
            "company": company,
            "date_text": date_line,
            "description": description,
        })

    return records