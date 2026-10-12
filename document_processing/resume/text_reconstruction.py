"""
text_reconstructor.py

Generic resume text reconstruction.

Purpose
-------
PDF extraction can sometimes remove spaces between words.

Examples:

    MachineLearning
        ->
    Machine Learning

    DjangoRESTFramework
        ->
    Django REST Framework

The module is intentionally conservative.

Important design rules:
    - Do not maintain company-name dictionaries here.
    - Do not use spelling_dictionary.json here.
    - Do not use skill_aliases.json here.
    - Do not use skill_stacks.json here.
    - Use master_skill_dictionary.json only to identify
      known canonical multi-word skills.
    - Unknown CamelCase/company names are preserved.
"""


import json
import re
from pathlib import Path


# ============================================================
# PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MASTER_SKILL_DICTIONARY_PATH = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "master_skill_dictionary.json"
)


# ============================================================
# MASTER SKILL DICTIONARY
# ============================================================

def load_master_skill_dictionary():
    """
    Load canonical skill names from the master dictionary.

    Returns:
        list[str]
    """

    if not MASTER_SKILL_DICTIONARY_PATH.exists():
        return []

    try:
        with open(
            MASTER_SKILL_DICTIONARY_PATH,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError
    ):
        return []

    if not isinstance(data, list):
        return []

    skills = []

    for item in data:

        if not isinstance(item, dict):
            continue

        name = item.get("name")

        if not isinstance(name, str):
            continue

        name = name.strip()

        if name:
            skills.append(name)

    return skills


# ============================================================
# NORMALIZE SKILL FOR COMPARISON
# ============================================================

def normalize_skill_for_comparison(value):
    """
    Convert a skill into a comparison-safe representation.

    Examples:

        Machine Learning
            ->
        machinelearning

        Machine-Learning
            ->
        machinelearning

        MachineLearning
            ->
        machinelearning

        Django REST Framework
            ->
        djangorestframework
    """

    if not isinstance(value, str):
        return ""

    return re.sub(
        r"[^a-z0-9]+",
        "",
        value.lower()
    )


# ============================================================
# BUILD KNOWN COMPOUND SKILL MAP
# ============================================================

def build_known_compound_skills():
    """
    Build:

        normalized compound
            ->
        canonical skill

    Example:

        machinelearning
            ->
        Machine Learning

        djangorestframework
            ->
        Django REST Framework
    """

    result = {}

    skills = load_master_skill_dictionary()

    for skill in skills:

        normalized = normalize_skill_for_comparison(
            skill
        )

        if not normalized:
            continue

        # Only relevant for skills containing
        # more than one logical word.
        #
        # We still keep compounds such as FastAPI
        # because they can occur as CamelCase-like
        # PDF extraction output.
        result[normalized] = skill

    return result


# ============================================================
# PDF ARTIFACTS
# ============================================================

PDF_ARTIFACTS = [
    r"\[\s*\*see\s+the\s+certificate\s*\*\]",
    r"\[\s*\*see\s+certificate\s*\*\]",
    r"\[\s*\*view\s+certificate\s*\*\]",
    r"\[\s*\*view\s+credential\s*\*\]",
    r"\[\s*\*visit\s+blog\s+page\s*\*\]",
    r"\[\s*\*visit\s+page\s*\*\]",
]


def remove_pdf_artifacts(text):
    """
    Remove common PDF extraction artifacts.
    """

    if not text:
        return ""

    for pattern in PDF_ARTIFACTS:

        text = re.sub(
            pattern,
            "",
            text,
            flags=re.IGNORECASE
        )

    return text


# ============================================================
# CAMEL CASE COMPONENTS
# ============================================================

def split_camel_case(text):
    """
    Split CamelCase into components.

    Example:

        MachineLearning
            ->
        Machine Learning

    This function itself does not decide whether
    splitting is safe.

    The caller must first verify that the complete
    token corresponds to a known canonical skill.
    """

    if not text:
        return text

    return re.sub(
        r"(?<=[a-z])(?=[A-Z])",
        " ",
        text
    )


# ============================================================
# SAFE KNOWN SKILL RECONSTRUCTION
# ============================================================

def reconstruct_known_skill(
    token,
    known_compound_skills
):
    """
    Reconstruct a token only when the complete token
    matches a canonical skill in the master dictionary.

    Examples:

        MachineLearning
            ->
        Machine Learning

        DjangoRESTFramework
            ->
        Django REST Framework

        CodeNest
            ->
        CodeNest

        BluePeak
            ->
        BluePeak
    """

    if not token:
        return token

    normalized_token = normalize_skill_for_comparison(
        token
    )

    if not normalized_token:
        return token

    canonical_skill = known_compound_skills.get(
        normalized_token
    )

    if canonical_skill is None:
        # Unknown token.
        #
        # This is extremely important:
        # do NOT split it.
        return token

    # --------------------------------------------------------
    # If the token already matches the canonical spelling,
    # preserve it.
    # --------------------------------------------------------

    if token.lower() == canonical_skill.lower():
        return token

    # --------------------------------------------------------
    # If the canonical skill contains multiple words,
    # return the canonical form.
    # --------------------------------------------------------

    if " " in canonical_skill:

        return canonical_skill

    # --------------------------------------------------------
    # Single-word canonical skills such as FastAPI,
    # NumPy, JavaScript, etc. should remain unchanged.
    # --------------------------------------------------------

    return token


# ============================================================
# RECONSTRUCT TOKEN
# ============================================================

def reconstruct_token(
    token,
    known_compound_skills
):
    """
    Reconstruct one whitespace-separated token.
    """

    if not token:
        return token

    # --------------------------------------------------------
    # URLs
    # --------------------------------------------------------

    if re.match(
        r"^(https?://|www\.)",
        token,
        flags=re.IGNORECASE
    ):
        return token

    # --------------------------------------------------------
    # Email addresses
    # --------------------------------------------------------

    if "@" in token:
        return token

    # --------------------------------------------------------
    # Numeric tokens
    # --------------------------------------------------------

    if re.fullmatch(
        r"[\d./:%+-]+",
        token
    ):
        return token

    # --------------------------------------------------------
    # Preserve punctuation around token
    # --------------------------------------------------------

    prefix_match = re.match(
        r"^[^A-Za-z0-9]*",
        token
    )

    suffix_match = re.search(
        r"[^A-Za-z0-9]*$",
        token
    )

    prefix = (
        prefix_match.group(0)
        if prefix_match
        else ""
    )

    suffix = (
        suffix_match.group(0)
        if suffix_match
        else ""
    )

    start = len(prefix)

    end = (
        len(token) - len(suffix)
        if suffix
        else len(token)
    )

    core = token[start:end]

    if not core:
        return token

    # --------------------------------------------------------
    # SAFE RECONSTRUCTION
    # --------------------------------------------------------

    reconstructed = reconstruct_known_skill(
        core,
        known_compound_skills
    )

    return (
        prefix
        + reconstructed
        + suffix
    )


# ============================================================
# RECONSTRUCT ONE LINE
# ============================================================

def reconstruct_line(
    line,
    known_compound_skills=None
):
    """
    Reconstruct one resume line.

    Existing whitespace structure is preserved as much
    as possible.
    """

    if not line:
        return ""

    if known_compound_skills is None:
        known_compound_skills = (
            build_known_compound_skills()
        )

    # --------------------------------------------------------
    # Remove PDF artifacts
    # --------------------------------------------------------

    line = remove_pdf_artifacts(line)

    # --------------------------------------------------------
    # Process existing tokens.
    # --------------------------------------------------------

    tokens = line.split()

    reconstructed = []

    for token in tokens:

        reconstructed_token = reconstruct_token(
            token,
            known_compound_skills
        )

        reconstructed.append(
            reconstructed_token
        )

    # --------------------------------------------------------
    # Normalize spaces.
    # --------------------------------------------------------

    result = " ".join(
        reconstructed
    )

    result = re.sub(
        r"\s+",
        " ",
        result
    )

    return result.strip()


# ============================================================
# RECONSTRUCT COMPLETE TEXT
# ============================================================

def reconstruct_text(text):
    """
    Reconstruct complete resume text.

    Each line is processed independently.
    """

    if not text:
        return ""

    known_compound_skills = (
        build_known_compound_skills()
    )

    lines = text.splitlines()

    result = []

    for line in lines:

        reconstructed = reconstruct_line(
            line,
            known_compound_skills
        )

        result.append(reconstructed)

    return "\n".join(result)


# ============================================================
# RECONSTRUCT LIST OF LINES
# ============================================================

def reconstruct_lines(lines):
    """
    Reconstruct a list of resume lines.
    """

    if not lines:
        return []

    known_compound_skills = (
        build_known_compound_skills()
    )

    result = []

    for line in lines:

        result.append(
            reconstruct_line(
                line,
                known_compound_skills
            )
        )

    return result


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def text_reconstructor(text):
    """
    Public entry point used by resume_pipeline.py.
    """

    return reconstruct_text(text)