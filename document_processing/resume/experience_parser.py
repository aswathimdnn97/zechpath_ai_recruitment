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

        # Prefer short non-sentence lines immediately before the date.
        candidates = []
        for line in reversed(preceding):
            if not _looks_like_title(line):
                continue
            cleaned = split_title_company(line)
            if cleaned and _looks_like_title(cleaned):
                candidates.append(cleaned)
            else:
                candidates.append(line)

        if candidates:
            title = candidates[0]

        # Company is usually another nearby non-sentence line.
        for line in preceding:
            cleaned = split_title_company(line)
            if cleaned != title and _looks_like_title(cleaned):
                company = cleaned
                break

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