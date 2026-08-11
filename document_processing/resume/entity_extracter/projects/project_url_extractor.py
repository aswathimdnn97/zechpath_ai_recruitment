import re


# ============================================================
# Patterns
# ============================================================

URL_PATTERN = re.compile(
    r"""
    (?:
        https?://
        |
        www\.
    )
    [^\s<>()]+
    """,
    re.IGNORECASE | re.VERBOSE,
)


DOMAIN_PATTERN = re.compile(
    r"""
    (?:
        github\.com
        |
        gitlab\.com
        |
        bitbucket\.org
    )
    /[^\s<>()]+
    """,
    re.IGNORECASE | re.VERBOSE,
)


URL_LABEL_PATTERN = re.compile(
    r"""
    ^
    (?:
        github
        |gitlab
        |bitbucket
        |repository
        |repo
        |demo
        |live
        |website
        |url
        |link
    )
    \s*:\s*
    (.+)
    $
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# Helpers
# ============================================================

def clean_line(line):
    """
    Clean a single resume line.
    """

    if not line:
        return ""

    line = line.strip()

    # Remove common bullet characters
    line = re.sub(r"^[•●▪◦*-]\s*", "", line)

    # Normalize whitespace
    line = re.sub(r"\s+", " ", line)

    return line.strip()


def clean_url(url):
    """
    Remove punctuation accidentally captured after a URL.
    """

    if not url:
        return None

    url = url.strip()

    # Remove trailing punctuation commonly found in resumes
    url = url.rstrip(".,;:)]}>")

    return url


def normalize_url(url):
    """
    Add https:// to known domains when protocol is missing.
    """

    if not url:
        return None

    url = clean_url(url)

    if not url:
        return None

    if url.startswith(("http://", "https://")):
        return url

    if url.startswith("www."):
        return f"https://{url}"

    if re.match(
        r"^(github\.com|gitlab\.com|bitbucket\.org)/",
        url,
        re.IGNORECASE,
    ):
        return f"https://{url}"

    return url


# ============================================================
# Main Extractor
# ============================================================

def extract_project_url(block):
    """
    Extract the first URL from an individual project block.

    Supported examples:

        GitHub: https://github.com/user/project
        Demo: https://example.com
        https://github.com/user/project
        github.com/user/project

    Parameters
    ----------
    block : list[str] | str
        Individual project block.

    Returns
    -------
    str | None
        Extracted project URL.
    """

    if not block:
        return None

    # --------------------------------------------------------
    # Support string input
    # --------------------------------------------------------

    if isinstance(block, str):
        lines = block.splitlines()
    else:
        lines = block

    # --------------------------------------------------------
    # Search each line
    # --------------------------------------------------------

    for raw_line in lines:

        line = clean_line(raw_line)

        if not line:
            continue

        # ----------------------------------------------------
        # First check explicitly labelled URL
        # ----------------------------------------------------

        label_match = URL_LABEL_PATTERN.match(line)

        if label_match:

            value = label_match.group(1).strip()

            url_match = URL_PATTERN.search(value)

            if url_match:
                return normalize_url(url_match.group(0))

            domain_match = DOMAIN_PATTERN.search(value)

            if domain_match:
                return normalize_url(domain_match.group(0))

        # ----------------------------------------------------
        # Check normal URLs
        # ----------------------------------------------------

        url_match = URL_PATTERN.search(line)

        if url_match:
            return normalize_url(url_match.group(0))

        # ----------------------------------------------------
        # Check GitHub/GitLab/Bitbucket without protocol
        # ----------------------------------------------------

        domain_match = DOMAIN_PATTERN.search(line)

        if domain_match:
            return normalize_url(domain_match.group(0))

    return None