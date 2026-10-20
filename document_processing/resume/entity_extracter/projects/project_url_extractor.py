
import re


URL_PATTERN = re.compile(
    r"""(?ix)
    (?:
        https?://[^\s<>\[\]()]+
        |
        www\.[^\s<>\[\]()]+
        |
        (?:github\.com|gitlab\.com|bitbucket\.org)/
        [^\s<>\[\]()]+
    )
    """
)

URL_LABEL_PATTERN = re.compile(
    r"^\s*(?:github|gitlab|bitbucket|repository|repo|"
    r"demo|live|website|url|link)\s*:\s*(.*)$",
    re.IGNORECASE,
)


def clean_line(line):
    if not isinstance(line, str):
        return ""

    return re.sub(r"\s+", " ", line.strip())


def clean_url(url):
    if not url:
        return None

    url = url.strip().strip("<>\"'")

    # Remove common trailing punctuation.
    url = url.rstrip(".,;:!?")

    # A Markdown closing parenthesis may be attached to a URL.
    url = url.rstrip(")")

    return url or None


def normalize_url(url):
    url = clean_url(url)

    if not url:
        return None

    if url.lower().startswith(("http://", "https://")):
        return url

    if url.lower().startswith("www."):
        return "https://" + url

    if re.match(
        r"^(?:github\.com|gitlab\.com|bitbucket\.org)/",
        url,
        re.IGNORECASE,
    ):
        return "https://" + url

    return None


def extract_project_url(block):
    if not block:
        return None

    lines = block.splitlines() if isinstance(block, str) else block

    for raw_line in lines:
        line = clean_line(raw_line)

        if not line:
            continue

        # Prefer a URL inside a labeled repository/demo line.
        label_match = URL_LABEL_PATTERN.match(line)
        search_text = label_match.group(1) if label_match else line

        match = URL_PATTERN.search(search_text)

        if match:
            url = normalize_url(match.group(0))

            if url:
                return url

    return None
