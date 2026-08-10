"""
credential_id_extractor.py

Extract credential IDs from certification blocks.

Examples supported:

    Credential ID: ABC123456
    Credential ID: AWS-123456

    Certification ID: AZ-204-123456

    Certificate ID: CERT-2024-001

    Credential Number: CRED-123456
    Certificate Number: 123456789

    Cert ID: AWS123456

    Credly:
    https://www.credly.com/badges/abc123xyz

Important:
    Do NOT extract words such as:

        Certified
        Certificate
        Certification
        Credential

    as credential IDs.
"""

import re


# ============================================================
# PATTERNS
# ============================================================

EXPLICIT_CREDENTIAL_ID_PATTERN = re.compile(
    r"""
    (?:
        credential\s+(?:id|number|no)
        |
        certification\s+(?:id|number|no)
        |
        certificate\s+(?:id|number|no)
        |
        cert\s+(?:id|number|no)
    )
    \s*
    [:#\-]?
    \s*
    (?P<credential_id>
        [A-Za-z0-9][A-Za-z0-9._/\-]{2,}
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# CREDLY URL
# ============================================================

CREDLY_URL_PATTERN = re.compile(
    r"""
    https?://
    (?:www\.)?
    credly\.com/
    (?:badges|earner|users)/
    (?P<credential_id>
        [A-Za-z0-9._\-]+
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


# ============================================================
# CLEAN
# ============================================================

def clean_credential_id(value):
    """
    Clean extracted credential ID.
    """

    if not value:
        return None

    value = value.strip()

    value = value.strip(
        " \t\r\n.,;:|()[]{}<>"
    )

    if not value:
        return None

    return value


# ============================================================
# VALIDATE
# ============================================================

def is_valid_credential_id(value):
    """
    Validate a credential ID.

    Returns:
        True / False
    """

    if not value:
        return False

    value = clean_credential_id(value)

    if not value:
        return False

    # --------------------------------------------------------
    # Length
    # --------------------------------------------------------

    if len(value) < 4:
        return False

    if len(value) > 100:
        return False

    # --------------------------------------------------------
    # Allowed characters
    # --------------------------------------------------------

    if not re.fullmatch(
        r"[A-Za-z0-9._/\-]+",
        value
    ):
        return False

    # --------------------------------------------------------
    # Forbidden words
    #
    # Prevent:
    #
    # Certified -> ified
    # Certificate
    # Credential
    # --------------------------------------------------------

    forbidden_words = {
        "certified",
        "certificate",
        "certification",
        "credential",
        "credentials",
        "cert",
        "id",
        "number",
        "no",
    }

    if value.lower() in forbidden_words:
        return False

    # --------------------------------------------------------
    # Pure year
    #
    # 2024 is NOT credential ID.
    # --------------------------------------------------------

    if re.fullmatch(
        r"(?:19|20)\d{2}",
        value
    ):
        return False

    # --------------------------------------------------------
    # Date
    #
    # 03/2024
    # 03-2024
    # --------------------------------------------------------

    if re.fullmatch(
        r"\d{1,2}[/-]\d{4}",
        value
    ):
        return False

    # --------------------------------------------------------
    # Date range
    #
    # 2024-2027
    # --------------------------------------------------------

    if re.fullmatch(
        r"\d{4}[/-]\d{4}",
        value
    ):
        return False

    return True


# ============================================================
# EXPLICIT CREDENTIAL ID
# ============================================================

def extract_explicit_credential_id(lines):
    """
    Extract credential ID from explicit labels.

    Examples:

        Credential ID: AWS-123456

        Certification ID: AZ-204-123456

        Certificate Number: CERT-2024-001
    """

    for line in lines:

        match = (
            EXPLICIT_CREDENTIAL_ID_PATTERN.search(
                line
            )
        )

        if not match:
            continue

        candidate = clean_credential_id(
            match.group(
                "credential_id"
            )
        )

        if is_valid_credential_id(
            candidate
        ):
            return candidate

    return None


# ============================================================
# CREDLY CREDENTIAL ID
# ============================================================

def extract_credly_credential_id(lines):
    """
    Extract credential ID from Credly URL.
    """

    for line in lines:

        match = (
            CREDLY_URL_PATTERN.search(
                line
            )
        )

        if not match:
            continue

        candidate = clean_credential_id(
            match.group(
                "credential_id"
            )
        )

        if is_valid_credential_id(
            candidate
        ):
            return candidate

    return None


# ============================================================
# MAIN FUNCTION
# ============================================================

def extract_credential_id(block):
    """
    Extract credential ID from a certification block.

    Parameters
    ----------
    block : list[str] | str

    Returns
    -------
    str | None
    """

    if not block:
        return None

    # --------------------------------------------------------
    # String
    # --------------------------------------------------------

    if isinstance(block, str):

        lines = block.splitlines()

    # --------------------------------------------------------
    # List
    # --------------------------------------------------------

    elif isinstance(block, list):

        lines = block

    else:

        return None

    # --------------------------------------------------------
    # Clean lines
    # --------------------------------------------------------

    cleaned_lines = []

    for line in lines:

        if not isinstance(line, str):
            continue

        line = line.strip()

        if line:
            cleaned_lines.append(line)

    if not cleaned_lines:
        return None

    # ========================================================
    # Priority 1
    #
    # Explicit credential ID
    # ========================================================

    credential_id = (
        extract_explicit_credential_id(
            cleaned_lines
        )
    )

    if credential_id:
        return credential_id

    # ========================================================
    # Priority 2
    #
    # Credly URL
    # ========================================================

    credential_id = (
        extract_credly_credential_id(
            cleaned_lines
        )
    )

    if credential_id:
        return credential_id

    # ========================================================
    # No credential ID
    # ========================================================

    return None


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_blocks = [

        # ----------------------------------------------------
        # No credential ID
        # ----------------------------------------------------

        [
            "Microsoft Certified: Azure Developer Associate",
            "Microsoft (2024)"
        ],

        [
            "Microsoft Certified: Azure AI Fundamentals",
            "Microsoft (2023)"
        ],

        [
            "Google Cloud Professional Data Engineer"
        ],

        [
            "Machine Learning Specialization",
            "Coursera / Deep Learning.AI (2022)"
        ],

        [
            "TensorFlow Developer Certificate",
            "TensorFlow (2022)"
        ],

        [
            "Python for Data Science",
            "IBM (2021)"
        ],

        # ----------------------------------------------------
        # Credential ID
        # ----------------------------------------------------

        [
            "AWS Certified Developer",
            "Credential ID: AWS-123456"
        ],

        # ----------------------------------------------------
        # Certification ID
        # ----------------------------------------------------

        [
            "Microsoft Certified Azure Developer",
            "Certification ID: AZ-204-123456"
        ],

        # ----------------------------------------------------
        # Certificate ID
        # ----------------------------------------------------

        [
            "Python for Data Science",
            "Certificate ID: CERT-2024-001"
        ],

        # ----------------------------------------------------
        # Credential Number
        # ----------------------------------------------------

        [
            "AWS Certified Developer",
            "Credential Number: CRED-123456"
        ],

        # ----------------------------------------------------
        # Certificate Number
        # ----------------------------------------------------

        [
            "Data Science Professional",
            "Certificate Number: 123456789"
        ],

        # ----------------------------------------------------
        # Cert ID
        # ----------------------------------------------------

        [
            "AWS Certified Developer",
            "Cert ID: AWS123456"
        ],

        # ----------------------------------------------------
        # Credly URL
        # ----------------------------------------------------

        [
            "AWS Certified Developer",
            "https://www.credly.com/badges/abc123xyz"
        ],
    ]


    for block in test_blocks:

        print(
            "\n========================================"
        )

        print(
            "BLOCK:",
            block
        )

        result = extract_credential_id(
            block
        )

        print(
            "CREDENTIAL ID:",
            result
        )
