
import re


DATE_PATTERN = re.compile(
    r"^(?:"
    r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
    r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|"
    r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{4}"
    r"|\d{4}"
    r"|\d{4}\s*[-–]\s*(?:\d{4}|present|current)"
    r")$",
    re.IGNORECASE,
)

URL_PATTERN = re.compile(
    r"(?:https?://|www\.|github\.com/|gitlab\.com/|"
    r"bitbucket\.org/)",
    re.IGNORECASE,
)

METADATA_LABELS = {
    "project", "projects", "project name", "description",
    "technologies", "technology", "tech stack", "tools",
    "skills", "role", "responsibilities", "github", "demo",
    "url", "repository", "repo",
}

ACTION_PATTERN = re.compile(
    r"\b(?:developed|built|designed|implemented|created|"
    r"engineered|architected|integrated|deployed|tested|"
    r"automated|managed|maintained|configured|validated)\b",
    re.IGNORECASE,
)


def _clean_line(line):
    if not isinstance(line, str):
        return ""

    line = line.strip()
    line = re.sub(r"^[•●▪◦*\-]+\s*", "", line)
    return re.sub(r"\s+", " ", line).strip()


def _remove_description(line):
    """
    Separate a project title from an inline description.
    Split only when the right-hand side starts with a
    recognizable action verb.
    """
    match = re.search(r"\s[-–—:]\s+", line)

    if match:
        title = line[:match.start()].strip()
        remainder = line[match.end():].strip()

        if title and ACTION_PATTERN.search(remainder):
            first_action = ACTION_PATTERN.search(remainder)

            if first_action and first_action.start() < 15:
                return title

    # Also support a title followed directly by an action.
    match = ACTION_PATTERN.search(line)

    if match and match.start() > 0:
        prefix = line[:match.start()].rstrip(" :-–—")
        if prefix and len(prefix.split()) <= 10:
            return prefix

    return line


def _is_invalid_project_name(line):
    normalized = line.lower().strip(" :-–—")

    return (
        not normalized
        or normalized in METADATA_LABELS
        or bool(DATE_PATTERN.fullmatch(normalized))
        or bool(URL_PATTERN.search(line))
        or bool(re.match(
            r"^(?:technologies|technology|tech stack|tools|"
            r"skills|github|demo|url|repository|repo)\s*:",
            line,
            re.IGNORECASE,
        ))
    )


def extract_project_name(block):
    if not block:
        return None

    lines = block.splitlines() if isinstance(block, str) else block

    for raw_line in lines:
        line = _clean_line(raw_line)

        if _is_invalid_project_name(line):
            continue

        name = _remove_description(line)
        name = name.strip(" :-–—")

        if not _is_invalid_project_name(name):
            return name

    return None
