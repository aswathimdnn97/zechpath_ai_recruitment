import re


PORTFOLIO_PATTERN = re.compile(
    r"https?://[^\s]+",
    re.IGNORECASE
)


def extract_portfolio(text):

    urls = PORTFOLIO_PATTERN.findall(text)

    for url in urls:

        if "github" in url.lower():
            continue

        if "linkedin" in url.lower():
            continue

        return url

    return None