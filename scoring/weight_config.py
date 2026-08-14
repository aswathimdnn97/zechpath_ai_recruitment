from typing import Any, Dict


# ============================================================
# Default weights
# ============================================================

DEFAULT_WEIGHTS = {
    "skill": 0.40,
    "experience": 0.30,
    "education": 0.10,
    "semantic": 0.20,
}


# ============================================================
# Role-category weights
# ============================================================

ROLE_CATEGORY_WEIGHTS = {

    # Backend development roles
    "backend": {
        "skill": 0.45,
        "experience": 0.30,
        "education": 0.10,
        "semantic": 0.15,
    },

    # Frontend development roles
    "frontend": {
        "skill": 0.45,
        "experience": 0.25,
        "education": 0.10,
        "semantic": 0.20,
    },

    # Data science / ML / AI roles
    "data_ml": {
        "skill": 0.40,
        "experience": 0.25,
        "education": 0.15,
        "semantic": 0.20,
    },

    # DevOps / cloud / infrastructure roles
    "devops": {
        "skill": 0.45,
        "experience": 0.30,
        "education": 0.10,
        "semantic": 0.15,
    },

    # Management / leadership roles
    "management": {
        "skill": 0.25,
        "experience": 0.40,
        "education": 0.10,
        "semantic": 0.25,
    },

    # Entry-level roles
    "entry_level": {
        "skill": 0.35,
        "experience": 0.15,
        "education": 0.25,
        "semantic": 0.25,
    },

    # General software roles
    "general": {
        "skill": 0.40,
        "experience": 0.30,
        "education": 0.10,
        "semantic": 0.20,
    },
}


# ============================================================
# Role-category aliases
# ============================================================

ROLE_CATEGORY_ALIASES = {

    "backend": [
        "backend",
        "back end",
        "python developer",
        "django developer",
        "flask developer",
        "java developer",
        "spring developer",
        "node developer",
        "node.js developer",
        "backend engineer",
        "backend developer",
        "software backend engineer",
    ],

    "frontend": [
        "frontend",
        "front end",
        "frontend developer",
        "frontend engineer",
        "react developer",
        "angular developer",
        "vue developer",
        "ui developer",
        "web developer",
    ],

    "data_ml": [
        "data scientist",
        "data science",
        "machine learning",
        "machine learning engineer",
        "ml engineer",
        "ai engineer",
        "artificial intelligence",
        "deep learning",
        "data analyst",
        "nlp engineer",
    ],

    "devops": [
        "devops",
        "devops engineer",
        "cloud engineer",
        "cloud developer",
        "site reliability engineer",
        "sre",
        "platform engineer",
        "infrastructure engineer",
    ],

    "management": [
        "engineering manager",
        "technical manager",
        "project manager",
        "product manager",
        "engineering lead",
        "tech lead",
        "team lead",
        "development manager",
    ],

    "entry_level": [
        "intern",
        "internship",
        "trainee",
        "fresher",
        "entry level",
        "junior developer",
        "graduate developer",
    ],
}


# ============================================================
# Normalize text
# ============================================================

def normalize_job_title(
    job_title: Any
) -> str:
    """
    Normalize job title before category matching.
    """

    if not isinstance(job_title, str):
        return ""

    return " ".join(
        job_title.lower().strip().split()
    )


# ============================================================
# Detect role category
# ============================================================

def detect_role_category(
    job_title: str
) -> str:
    """
    Detect broad role category from job title.

    Returns:

        backend
        frontend
        data_ml
        devops
        management
        entry_level
        general
    """

    normalized_title = normalize_job_title(
        job_title
    )

    if not normalized_title:
        return "general"

    # Exact / phrase matching
    for category, aliases in (
        ROLE_CATEGORY_ALIASES.items()
    ):

        for alias in aliases:

            normalized_alias = (
                normalize_job_title(alias)
            )

            if (
                normalized_alias
                in normalized_title
            ):
                return category

    return "general"


# ============================================================
# Validate weights
# ============================================================

def validate_weights(
    weights: Dict[str, float]
) -> bool:
    """
    Validate scoring weights.

    Required components:

        skill
        experience
        education
        semantic

    Total must equal 1.0.
    """

    required_components = {
        "skill",
        "experience",
        "education",
        "semantic",
    }

    if set(weights.keys()) != required_components:
        return False

    if any(
        not isinstance(value, (int, float))
        for value in weights.values()
    ):
        return False

    if any(
        value < 0 or value > 1
        for value in weights.values()
    ):
        return False

    total = sum(weights.values())

    return abs(total - 1.0) < 0.0001


# ============================================================
# Get weights
# ============================================================

def get_weights(
    job_title: str = "",
    custom_weights: Dict[str, float] = None,
) -> Dict[str, Any]:
    """
    Get scoring weights dynamically.

    Priority:

        1. Custom weights
        2. Role-category weights
        3. Default weights
    """

    # --------------------------------------------------------
    # Custom configuration
    # --------------------------------------------------------

    if custom_weights is not None:

        if not validate_weights(
            custom_weights
        ):
            raise ValueError(
                "Invalid custom weights. "
                "Weights must contain skill, "
                "experience, education and semantic "
                "and must sum to 1.0."
            )

        return {
            "weights": custom_weights.copy(),
            "source": "custom",
            "role_category": detect_role_category(
                job_title
            ),
            "job_title": job_title,
        }

    # --------------------------------------------------------
    # Detect role category
    # --------------------------------------------------------

    role_category = detect_role_category(
        job_title
    )

    # --------------------------------------------------------
    # Role-specific category weights
    # --------------------------------------------------------

    if role_category in ROLE_CATEGORY_WEIGHTS:

        return {
            "weights": (
                ROLE_CATEGORY_WEIGHTS[
                    role_category
                ].copy()
            ),

            "source": "role_category",

            "role_category":
                role_category,

            "job_title":
                job_title,
        }

    # --------------------------------------------------------
    # Default
    # --------------------------------------------------------

    return {
        "weights": DEFAULT_WEIGHTS.copy(),

        "source": "default",

        "role_category":
            "general",

        "job_title":
            job_title,
    }