import re


# ============================================================
# URL PATTERNS
# ============================================================

URL_PATTERN = re.compile(
    r"""
    (?:
        https?://
        |
        www\.
        |
        github\.com/
        |
        gitlab\.com/
        |
        bitbucket\.org/
    )
    [^\s<>\[\]()]+
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
    /
    [^\s<>\[\]()]+
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# URL LABEL
# ============================================================

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
# CLEAN LINE
# ============================================================

def clean_line(line):

    if not line:
        return ""

    line = str(line).strip()

    line = re.sub(
        r"^[•●▪◦*\-]\s*",
        "",
        line,
    )

    line = re.sub(
        r"\s+",
        " ",
        line,
    )

    return line.strip()


# ============================================================
# CLEAN URL
# ============================================================

def clean_url(url):

    if not url:
        return None

    url = url.strip()

    # Remove markdown brackets
    url = url.strip(
        "[]()<>"
    )

    # Remove trailing punctuation
    url = url.rstrip(
        ".,;:)]}>"
    )

    return url


# ============================================================
# NORMALIZE URL
# ============================================================

def normalize_url(url):

    if not url:
        return None

    url = clean_url(url)

    if not url:
        return None

    # Already has protocol
    if url.startswith(
        ("http://", "https://")
    ):
        return url

    # www
    if url.startswith("www."):

        return f"https://{url}"

    # Known domains
    if re.match(
        r"^(?:"
        r"github\.com"
        r"|gitlab\.com"
        r"|bitbucket\.org"
        r")/",
        url,
        re.IGNORECASE,
    ):

        return f"https://{url}"

    return url


# ============================================================
# EXTRACT PROJECT URL
# ============================================================

def extract_project_url(block):

    if not block:
        return None

    if isinstance(block, str):

        lines = block.splitlines()

    elif isinstance(block, list):

        lines = block

    else:
        return None

    for raw_line in lines:

        if not isinstance(raw_line, str):
            continue

        line = clean_line(raw_line)

        if not line:
            continue

        # ----------------------------------------------------
        # Labelled URL
        # ----------------------------------------------------

        label_match = URL_LABEL_PATTERN.match(
            line
        )

        if label_match:

            value = label_match.group(1).strip()

            # Full URL
            url_match = URL_PATTERN.search(
                value
            )

            if url_match:

                return normalize_url(
                    url_match.group(0)
                )

            # GitHub/GitLab/etc without protocol
            domain_match = DOMAIN_PATTERN.search(
                value
            )

            if domain_match:

                return normalize_url(
                    domain_match.group(0)
                )

        # ----------------------------------------------------
        # Any URL in line
        # ----------------------------------------------------

        url_match = URL_PATTERN.search(
            line
        )

        if url_match:

            return normalize_url(
                url_match.group(0)
            )

        # ----------------------------------------------------
        # Known domain without protocol
        # ----------------------------------------------------

        domain_match = DOMAIN_PATTERN.search(
            line
        )

        if domain_match:

            return normalize_url(
                domain_match.group(0)
            )

    return None