import re
from typing import Iterable, Optional


# ============================================================
# Patterns
# ============================================================

BULLET_PATTERN = re.compile(
    r"^(?:[•●▪◦‣⁃∙·*➢➤►▸-])\s+"
)

DATE_PATTERN = re.compile(
    r"""
    ^
    (?:
        \d{4}
        |
        \d{1,2}[/-]\d{4}
        |
        (?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)
        [a-z]*\s+\d{4}
        |
        (?:19|20)\d{2}\s*[-–—]\s*(?:present|current|(19|20)\d{2})
    )
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Common resume section headings.
DEFAULT_HEADINGS = {
    "summary",
    "professional summary",
    "profile",
    "objective",
    "career objective",
    "skills",
    "technical skills",
    "technical skill",
    "key skills",
    "core skills",
    "technical competencies",
    "experience",
    "work experience",
    "professional experience",
    "employment",
    "employment history",
    "work history",
    "education",
    "educational qualifications",
    "academic qualifications",
    "academic background",
    "certifications",
    "certificates",
    "projects",
    "project",
    "achievements",
    "awards",
    "languages",
    "interests",
    "hobbies",
    "contact",
    "contact information",
    "personal information",
    "references",
}


# ============================================================
# Basic helpers
# ============================================================

def _normalize_line(line: str) -> str:
    """
    Normalize whitespace without destroying useful content.
    """

    if not line:
        return ""

    # Normalize tabs.
    line = line.replace("\t", " ")

    # Normalize non-breaking spaces.
    line = line.replace("\u00a0", " ")

    # Normalize different dash characters.
    line = line.replace("–", "-").replace("—", "-")

    # Collapse repeated whitespace.
    line = re.sub(r"[ \t]+", " ", line)

    return line.strip()


def _is_heading(line: str, heading_set: set[str]) -> bool:
    """
    Check whether a line is a known resume heading.
    """

    normalized = line.strip().lower()

    if normalized in heading_set:
        return True

    return False


def _is_bullet(line: str) -> bool:
    """
    Check whether a line starts with a resume bullet.
    """

    return bool(BULLET_PATTERN.match(line))


def _is_date_line(line: str) -> bool:
    """
    Detect common standalone date/year lines.
    """

    return bool(DATE_PATTERN.match(line.strip()))


def _is_short_entity_like_line(line: str) -> bool:
    """
    Detect short lines that are more likely to represent an entity
    than a sentence continuation.

    Examples:
        Python
        Django
        SQL
        ABC Technologies
        B.Tech
    """

    words = line.split()

    if len(words) <= 4 and not line.endswith(
        (".", ",", ";", ":", "!", "?", "(", "/", "-")
    ):
        return True

    return False


def _looks_like_sentence_start(line: str) -> bool:
    """
    Detect whether the current line looks like the beginning of
    a new sentence/content block.
    """

    if not line:
        return False

    first_word = line.split()[0]

    # A lowercase first character is a strong continuation signal.
    if first_word[0].islower():
        return True

    return False


def _previous_line_requires_continuation(line: str) -> bool:
    """
    Detect punctuation indicating that the previous line is incomplete.
    """

    if not line:
        return False

    return line.endswith(
        (
            ",",
            "/",
            "-",
            "(",
            "[",
            "{",
            "&",
        )
    )


def _remove_duplicate_spacing(line: str) -> str:
    """
    Final whitespace cleanup.
    """

    return re.sub(r"\s+", " ", line).strip()


# ============================================================
# Continuation logic
# ============================================================

def _should_merge(
    previous: str,
    current: str,
    heading_set: set[str],
) -> bool:
    """
    Decide conservatively whether `current` is a continuation
    of `previous`.

    The function intentionally prefers NOT merging when uncertain.
    This prevents corruption of skills, companies, dates, titles,
    and other resume entities.
    """

    if not previous or not current:
        return False

    # Never merge headings.
    if _is_heading(current, heading_set):
        return False

    # Never merge bullet lines into non-bullet content.
    if _is_bullet(current):
        return False

    # Standalone dates should remain independent.
    if _is_date_line(current):
        return False

    # If the previous line clearly indicates an unfinished sentence,
    # merging is usually safe.
    if _previous_line_requires_continuation(previous):
        return True

    # Lowercase continuation is useful, but only when the current
    # line does not look like a short entity.
    if _looks_like_sentence_start(current):
        if not _is_short_entity_like_line(current):
            return True

    # If the previous line is very short and entity-like, don't
    # attach another line to it.
    if _is_short_entity_like_line(previous):
        return False

    return False


# ============================================================
# Main layout fixer
# ============================================================

def fix_layout(
    text: str,
    headings: Optional[Iterable[str]] = None,
) -> str:
    """
    Clean and normalize resume text while preserving document structure.

    This function performs TEXT-LEVEL layout normalization only.
    It does not attempt to reconstruct PDF columns or tables.

    Features
    --------
    - Normalizes tabs and whitespace.
    - Normalizes common dash/space characters.
    - Preserves meaningful blank-line boundaries.
    - Preserves bullet structure.
    - Protects section headings.
    - Protects standalone dates.
    - Conservatively merges soft-wrapped continuation lines.
    - Avoids merging short entity-like lines such as skills,
      company names, job titles, and technologies.
    - Produces deterministic output.

    Parameters
    ----------
    text:
        Raw extracted text.

    headings:
        Optional iterable of known section headings.

    Returns
    -------
    str
        Cleaned and layout-normalized text.
    """

    if not text or not text.strip():
        return ""

    # --------------------------------------------------------
    # Prepare headings
    # --------------------------------------------------------

    heading_set = set(DEFAULT_HEADINGS)

    if headings:
        heading_set.update(
            str(heading).strip().lower()
            for heading in headings
            if heading
        )

    # --------------------------------------------------------
    # Normalize raw lines
    # --------------------------------------------------------

    raw_lines = text.splitlines()

    normalized_lines = []

    for raw_line in raw_lines:
        line = _normalize_line(raw_line)

        if line:
            normalized_lines.append(line)
        else:
            # Preserve blank lines temporarily.
            normalized_lines.append("")

    # --------------------------------------------------------
    # Process lines
    # --------------------------------------------------------

    output = []

    pending_line: Optional[str] = None
    pending_is_bullet = False

    for line in normalized_lines:

        # ====================================================
        # Blank line
        # ====================================================

        if not line:

            if pending_line is not None:
                output.append(pending_line)
                pending_line = None
                pending_is_bullet = False

            # Preserve only ONE blank line.
            if output and output[-1] != "":
                output.append("")

            continue

        # ====================================================
        # Heading
        # ====================================================

        if _is_heading(line, heading_set):

            if pending_line is not None:
                output.append(pending_line)
                pending_line = None
                pending_is_bullet = False

            output.append(line)
            continue

        # ====================================================
        # Bullet
        # ====================================================

        if _is_bullet(line):

            if pending_line is not None:
                output.append(pending_line)

            pending_line = line
            pending_is_bullet = True
            continue

        # ====================================================
        # First content line
        # ====================================================

        if pending_line is None:

            pending_line = line
            pending_is_bullet = False
            continue

        # ====================================================
        # Bullet continuation
        # ====================================================

        if pending_is_bullet:

            # A bullet's wrapped continuation is commonly indented
            # in the original document. After extraction, indentation
            # may be lost, so use sentence-like characteristics.

            if (
                line[0].islower()
                or _previous_line_requires_continuation(pending_line)
            ):
                pending_line = f"{pending_line} {line}"
                continue

            # Otherwise treat it as a new line/entity.
            output.append(pending_line)
            pending_line = line
            pending_is_bullet = False
            continue

        # ====================================================
        # Normal continuation
        # ====================================================

        if _should_merge(
            previous=pending_line,
            current=line,
            heading_set=heading_set,
        ):
            pending_line = f"{pending_line} {line}"
            continue

        # ====================================================
        # New independent line
        # ====================================================

        output.append(pending_line)

        pending_line = line
        pending_is_bullet = False

    # --------------------------------------------------------
    # Flush remaining line
    # --------------------------------------------------------

    if pending_line is not None:
        output.append(pending_line)

    # --------------------------------------------------------
    # Final cleanup
    # --------------------------------------------------------

    final_lines = []

    for line in output:

        line = _remove_duplicate_spacing(line)

        if line:
            final_lines.append(line)
        elif final_lines and final_lines[-1] != "":
            final_lines.append("")

    # Remove leading/trailing blank lines.
    while final_lines and final_lines[0] == "":
        final_lines.pop(0)

    while final_lines and final_lines[-1] == "":
        final_lines.pop()

    return "\n".join(final_lines)