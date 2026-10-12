
import re


SPECIAL_CHARACTER_REPLACEMENTS = {
    "\x13": "- ",
    "\x11": " ",
    "\x1F": "- ",
    "\u00B7": "- ",
    "\u2022": "- ",
    "\u2023": "- ",
    "\u2043": "- ",
    "\u25AA": "- ",
    "\u25CF": "- ",
    "\u2030": " ",
    "\u00BD": "Location: ",
    "\uFFFD": " ",
    "\uFFFE": " ",
    "\uFFFF": " ",
    "(cid:19)": " ",
    "(cid:17)": " ",
    "(cid:31)": " ",
    "(cid:135)": " ",
    "(cid:211)": " ",
    "(cid:41)": " ",
    "(cid:37)": " ",
    "(cid:45)": " ",
    "(cid:218)": " ",
    "(cid:123)": " ",
    "(cid:72)": " ",
    "(cid:66)": " ",
    "(cid:127)": " ",
}

CONTROL_CHARACTER_PATTERN = re.compile(
    r"[\x00-\x08\x0B-\x1F\x7F]"
)

EXCESSIVE_BLANK_LINES_PATTERN = re.compile(
    r"\n[ \t]*\n(?:[ \t]*\n)+"
)

MULTIPLE_SPACES_PATTERN = re.compile(r"[ ]{2,}")
TRAILING_LINE_SPACES_PATTERN = re.compile(r"[ \t]+\n")
LEADING_LINE_SPACES_PATTERN = re.compile(r"\n[ \t]+")


def clean_text(text):
    """
    Clean extracted resume text while preserving meaningful symbols.

    - Normalize tabs and non-breaking spaces.
    - Replace known PDF artifacts.
    - Preserve symbols such as C#, C++, %, and underscores.
    - Replace control characters with spaces to prevent joined words.
    - Normalize repeated spaces and excessive blank lines.
    """
    if text is None:
        return ""

    if not isinstance(text, str):
        raise TypeError(
            f"clean_text() expects str or None, "
            f"received {type(text).__name__}"
        )

    if not text:
        return ""

    text = text.replace("\t", " ")
    text = text.replace("\u00A0", " ")

    for old, new in SPECIAL_CHARACTER_REPLACEMENTS.items():
        text = text.replace(old, new)

    # Remove a stray percent sign immediately before an Indian phone prefix.
    text = re.sub(
        r"(?<!\S)%[ \t]*(?=\+91\b)",
        "",
        text,
    )

    # Use a space instead of deleting control characters.
    text = CONTROL_CHARACTER_PATTERN.sub(" ", text)

    # Normalize repeated spaces.
    text = MULTIPLE_SPACES_PATTERN.sub(" ", text)

    # Preserve one blank line between paragraphs.
    text = EXCESSIVE_BLANK_LINES_PATTERN.sub("\n\n", text)

    text = TRAILING_LINE_SPACES_PATTERN.sub("\n", text)
    text = LEADING_LINE_SPACES_PATTERN.sub("\n", text)

    return text.strip()