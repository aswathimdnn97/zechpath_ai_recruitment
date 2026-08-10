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

    Optimizeprocurementprocessanddemandplanningcycle
        ->
    Optimize procurement process and demand planning cycle

The module is intentionally conservative.

If the system is not confident about a reconstruction,
the original text is returned unchanged.

This module is generic and can be used for:

    - Summary
    - Experience
    - Skills
    - Education
    - Certifications
    - Projects
    - Other resume sections
"""

import json
import re
from pathlib import Path


# ============================================================
# PATH
# ============================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[3]

WORD_DICTIONARY_PATH = (
    PROJECT_ROOT
    / "data"
    / "resume"
    / "word_dictionary.json"
)


# ============================================================
# WORD DICTIONARY
# ============================================================

DEFAULT_WORDS = {
    # General resume words
    "a",
    "about",
    "academic",
    "achievement",
    "achievements",
    "analysis",
    "and",
    "application",
    "applications",
    "artificial",
    "as",
    "at",
    "backend",
    "business",
    "by",
    "cloud",
    "code",
    "coding",
    "communication",
    "computer",
    "configuration",
    "consulting",
    "data",
    "database",
    "deep",
    "degree",
    "demand",
    "deployment",
    "development",
    "developer",
    "developing",
    "digital",
    "education",
    "engineering",
    "engineer",
    "end",
    "enterprise",
    "experience",
    "experienced",
    "for",
    "from",
    "frontend",
    "full",
    "functional",
    "github",
    "google",
    "in",
    "information",
    "infrastructure",
    "integration",
    "intelligence",
    "international",
    "job",
    "learning",
    "machine",
    "maintained",
    "management",
    "managing",
    "marketing",
    "microsoft",
    "model",
    "models",
    "network",
    "of",
    "on",
    "optimization",
    "optimize",
    "organization",
    "planning",
    "platform",
    "process",
    "processing",
    "professional",
    "programming",
    "project",
    "projects",
    "python",
    "real",
    "research",
    "resume",
    "sales",
    "science",
    "scientist",
    "security",
    "server",
    "service",
    "services",
    "software",
    "solution",
    "solutions",
    "stack",
    "technical",
    "technology",
    "testing",
    "the",
    "to",
    "tools",
    "training",
    "used",
    "using",
    "various",
    "web",
    "with",
    "work",
    "worked",
    "working",
    "year",
    "years",

    # Common technical words
    "algorithm",
    "algorithms",
    "analytics",
    "azure",
    "big",
    "business",
    "classification",
    "computer",
    "computing",
    "container",
    "containers",
    "dashboard",
    "data",
    "engineering",
    "framework",
    "frameworks",
    "frontend",
    "backend",
    "javascript",
    "java",
    "kubernetes",
    "machine",
    "micro",
    "mysql",
    "mongodb",
    "node",
    "python",
    "react",
    "sql",
    "tensorflow",
    "testing",
    "typescript",

    # Common action words
    "built",
    "created",
    "designed",
    "developed",
    "implemented",
    "improved",
    "increased",
    "managed",
    "optimized",
    "reduced",
    "responsible",
    "supported",
}


# ============================================================
# WORD DICTIONARY LOADER
# ============================================================

def load_word_dictionary():
    """
    Load additional words from JSON.

    Supported JSON:

    {
        "words": [
            "machine",
            "learning",
            "procurement"
        ]
    }

    If the JSON file does not exist, the default
    vocabulary is used.
    """

    words = set(DEFAULT_WORDS)

    if not WORD_DICTIONARY_PATH.exists():
        return words

    try:
        with open(
            WORD_DICTIONARY_PATH,
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)

    except (
        OSError,
        json.JSONDecodeError
    ):
        return words

    if isinstance(data, dict):
        values = data.get(
            "words",
            []
        )

    elif isinstance(data, list):
        values = data

    else:
        return words

    for word in values:

        if not isinstance(
            word,
            str
        ):
            continue

        word = word.strip().lower()

        if word:
            words.add(word)

    return words


# ============================================================
# PDF ARTIFACTS
# ============================================================

PDF_ARTIFACTS = [
    r"\[\s*see\s+the\s+certificate\s*\]",
    r"\[\s*see\s+certificate\s*\]",
    r"\[\s*view\s+certificate\s*\]",
    r"\[\s*view\s+credential\s*\]",
    r"\[\s*visit\s+blog\s+page\s*\]",
    r"\[\s*visit\s+page\s*\]",
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
# KNOWN COMPOUND WORDS
# ============================================================

KNOWN_COMPOUND_WORDS = {
    "javascript",
    "typescript",
    "github",
    "gitlab",
    "tensorflow",
    "pytorch",
    "mongodb",
    "postgresql",
    "mysql",
    "nodejs",
    "reactjs",
    "angularjs",
    "expressjs",
    "powerbi",
    "devops",
    "fullstack",
    "machinelearning",
    "deepfake",
}


def is_known_compound(word):
    """
    Return True when a word should normally be preserved.

    Example:

        JavaScript

    should not become:

        Java Script
    """

    return (
        word.lower()
        in KNOWN_COMPOUND_WORDS
    )


# ============================================================
# CAMEL CASE
# ============================================================

def split_camel_case(text):
    """
    Split obvious camel-case words.

    Example:

        MachineLearning

    becomes:

        Machine Learning
    """

    if not text:
        return ""

    return re.sub(
        r"(?<=[a-z])(?=[A-Z])",
        " ",
        text
    )


# ============================================================
# WORD SEGMENTATION
# ============================================================

def find_word_split(
    word,
    vocabulary
):
    """
    Find a safe segmentation for a concatenated word.

    Example:

        machinelearning

    becomes:

        ["machine", "learning"]

    If no reliable segmentation exists,
    return None.
    """

    original = word

    clean_word = re.sub(
        r"[^A-Za-z]",
        "",
        word
    )

    if not clean_word:
        return None

    lower_word = clean_word.lower()

    # --------------------------------------------------------
    # Already a known word.
    # --------------------------------------------------------

    if lower_word in vocabulary:

        return None

    # --------------------------------------------------------
    # Known technical compound.
    # --------------------------------------------------------

    if is_known_compound(
        lower_word
    ):
        return None

    length = len(
        lower_word
    )

    # --------------------------------------------------------
    # Don't attempt very short words.
    # --------------------------------------------------------

    if length < 8:
        return None

    # --------------------------------------------------------
    # Dynamic programming table.
    #
    # best[i] = best segmentation from
    # beginning up to position i.
    # --------------------------------------------------------

    best = [None] * (
        length + 1
    )

    best[0] = []

    for end in range(
        1,
        length + 1
    ):

        candidates = []

        for start in range(
            0,
            end
        ):

            previous = best[start]

            if previous is None:
                continue

            part = lower_word[
                start:end
            ]

            if part not in vocabulary:
                continue

            # Avoid extremely short pieces.
            if len(part) < 2:
                continue

            candidate = (
                previous
                + [part]
            )

            candidates.append(
                candidate
            )

        if candidates:

            # Prefer:
            # 1. fewer words
            # 2. longer words

            best[end] = min(
                candidates,
                key=lambda item: (
                    len(item),
                    -sum(
                        len(word)
                        for word in item
                    )
                )
            )

    result = best[length]

    if not result:
        return None

    # --------------------------------------------------------
    # We need at least two words.
    # --------------------------------------------------------

    if len(result) < 2:
        return None

    # --------------------------------------------------------
    # Too many pieces usually means
    # a bad reconstruction.
    # --------------------------------------------------------

    if len(result) > 8:
        return None

    # --------------------------------------------------------
    # Safety check:
    # don't split a word into tiny pieces.
    # --------------------------------------------------------

    for part in result:

        if len(part) < 2:
            return None

    return result


# ============================================================
# RECONSTRUCT ONE TOKEN
# ============================================================

def reconstruct_token(
    token,
    vocabulary
):
    """
    Reconstruct one whitespace-separated token.
    """

    if not token:
        return token

    # --------------------------------------------------------
    # Keep URLs unchanged.
    # --------------------------------------------------------

    if re.match(
        r"^(https?://|www\.)",
        token,
        flags=re.IGNORECASE
    ):
        return token

    # --------------------------------------------------------
    # Keep email addresses unchanged.
    # --------------------------------------------------------

    if "@" in token:
        return token

    # --------------------------------------------------------
    # Keep numbers unchanged.
    # --------------------------------------------------------

    if re.fullmatch(
        r"[\d./:%+-]+",
        token
    ):
        return token

    # --------------------------------------------------------
    # Preserve punctuation around the word.
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
        len(token)
        - len(suffix)
        if suffix
        else len(token)
    )

    core = token[
        start:end
    ]

    if not core:
        return token

    # --------------------------------------------------------
    # Known compound technical word.
    # --------------------------------------------------------

    if is_known_compound(
        core
    ):
        return token

    # --------------------------------------------------------
    # First try camel case.
    # --------------------------------------------------------

    camel_result = split_camel_case(
        core
    )

    if camel_result != core:

        return (
            prefix
            + camel_result
            + suffix
        )

    # --------------------------------------------------------
    # Then try dictionary segmentation.
    # --------------------------------------------------------

    split = find_word_split(
        core,
        vocabulary
    )

    if not split:
        return token

    return (
        prefix
        + " ".join(split)
        + suffix
    )


# ============================================================
# RECONSTRUCT ONE LINE
# ============================================================

def reconstruct_line(
    line,
    vocabulary=None
):
    """
    Reconstruct one resume line.
    """

    if not line:
        return ""

    if vocabulary is None:
        vocabulary = (
            load_word_dictionary()
        )

    # --------------------------------------------------------
    # Remove PDF artifacts.
    # --------------------------------------------------------

    line = remove_pdf_artifacts(
        line
    )

    # --------------------------------------------------------
    # Process each existing token.
    #
    # Existing spaces are preserved.
    # We only reconstruct tokens where
    # there is strong evidence.
    # --------------------------------------------------------

    tokens = line.split()

    reconstructed = []

    for token in tokens:

        new_token = reconstruct_token(
            token,
            vocabulary
        )

        reconstructed.append(
            new_token
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

def reconstruct_text(
    text,
    vocabulary=None
):
    """
    Reconstruct complete resume text.

    Lines are processed independently so that
    resume layout is preserved.
    """

    if not text:
        return ""

    if vocabulary is None:
        vocabulary = (
            load_word_dictionary()
        )

    lines = text.splitlines()

    result = []

    for line in lines:

        reconstructed = reconstruct_line(
            line,
            vocabulary
        )

        result.append(
            reconstructed
        )

    return "\n".join(
        result
    )


# ============================================================
# RECONSTRUCT LIST OF LINES
# ============================================================

def reconstruct_lines(
    lines,
    vocabulary=None
):
    """
    Reconstruct a list of resume lines.
    """

    if not lines:
        return []

    if vocabulary is None:
        vocabulary = (
            load_word_dictionary()
        )

    result = []

    for line in lines:

        result.append(
            reconstruct_line(
                line,
                vocabulary
            )
        )

    return result


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def text_reconstructor(text):
    """
    Main public function.

    This is the function that should be called
    from resume_pipeline.py.
    """

    return reconstruct_text(
        text
    )