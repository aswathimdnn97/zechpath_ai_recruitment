import re

def clean_text(text):
    """
    Clean extracted resume text by:
    - Removing tabs
    - Replacing PDF special symbols
    - Removing unwanted symbols
    - Removing control characters
    - Removing extra spaces and blank lines
    """

    # Handle None input
    if text is None:
        return ""

    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Replace special characters commonly found in PDF extraction
    replacements = {
        "\x13": "- ",          #  -> Bullet
        "\x11": " ",           #  -> Separator
        "\x1F": "- ",          #  -> Bullet
        "\u00B7": "- ",        # · -> Bullet
        "\u2022": "- ",        # • -> Bullet
        "\u2030": " ",         # ‰ -> Remove location icon
        "\u00BD": "Location: ",# ½ -> Location symbol
        "\uFFFD": "",          # � -> Replacement character
        "\uFFFE": "",          # Invisible Unicode character
        "￾": "",               # Another invisible character
        "(cid:19)": " ",
        "(cid:17)": " ",
        "(cid:31)": " ",
        "(cid:135)": " ",
        "(cid:211)": " ",
        "(cid:41)" : " ",
        "(cid:37)" : " ",
        "(cid:45)" : " ",
        "(cid:218)" : " " 
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove unwanted symbols (keep email, phone, punctuation)
    text = re.sub(r"[#$%^&*_=+~`]+", " ", text)

    # Remove remaining control characters
    text = re.sub(r"[\x00-\x09\x0B-\x1F\x7F]", "", text)

    # Remove multiple spaces
    text = re.sub(r"[ ]{2,}", " ", text)

    # Remove multiple blank lines
    text = re.sub(r"\n\s*\n+", "\n", text)

    # Remove spaces before newline
    text = re.sub(r" +\n", "\n", text)

    # Remove spaces after newline
    text = re.sub(r"\n +", "\n", text)

    # Remove leading/trailing spaces
    text = text.strip()

    return text