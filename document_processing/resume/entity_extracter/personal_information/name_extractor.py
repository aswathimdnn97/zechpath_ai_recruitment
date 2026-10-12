import re


# ============================================================
# COMMON RESUME SECTION HEADINGS
# ============================================================

SECTION_HEADINGS = {
    "professional summary",
    "summary",
    "profile",
    "professional profile",
    "objective",
    "career objective",
    "about me",
    "contact",
    "contact information",
    "personal information",
    "skills",
    "technical skills",
    "education",
    "experience",
    "work experience",
    "professional experience",
    "projects",
    "certifications",
    "certificates",
    "achievements",
    "languages",
    "interests",
    "references",
}


# ============================================================
# JOB TITLE / ROLE KEYWORDS
# ============================================================

TITLE_KEYWORDS = {
    "developer",
    "engineer",
    "software",
    "intern",
    "fresher",
    "junior",
    "senior",
    "lead",
    "manager",
    "analyst",
    "architect",
    "consultant",
    "specialist",
    "student",
    "graduate",
    "trainee",
    "associate",
    "designer",
    "administrator",
    "administrator",
    "scientist",
    "tester",
    "qa",
    "devops",
    "recruiter",
    "director",
}


# ============================================================
# TECHNICAL / SKILL KEYWORDS
# ============================================================

TECHNICAL_KEYWORDS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "reactjs",
    "angular",
    "vue",
    "django",
    "flask",
    "fastapi",
    "sql",
    "mysql",
    "postgresql",
    "postgres",
    "mongodb",
    "oracle",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "git",
    "github",
    "html",
    "css",
    "node",
    "nodejs",
    "numpy",
    "pandas",
    "tensorflow",
    "pytorch",
    "machine",
    "learning",
    "deep",
    "ai",
    "api",
}


# ============================================================
# HELPERS
# ============================================================

def _is_section_heading(line):
    normalized = re.sub(r"\s+", " ", line.strip().lower())
    return normalized in SECTION_HEADINGS


def _contains_title_keyword(line):
    lower = line.lower()

    return any(
        re.search(
            rf"\b{re.escape(keyword)}\b",
            lower,
        )
        for keyword in TITLE_KEYWORDS
    )


def _looks_like_technical_line(line):
    words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]*", line.lower())

    if not words:
        return False

    technical_matches = sum(
        word in TECHNICAL_KEYWORDS
        for word in words
    )

    # A line containing multiple technical terms is
    # much more likely to be a skills line than a name.
    return technical_matches >= 2


def _looks_like_name(line):
    words = line.split()

    if not 2 <= len(words) <= 4:
        return False

    # Names should normally contain alphabetic words.
    if not all(re.fullmatch(r"[A-Za-z][A-Za-z.'-]*", word) for word in words):
        return False

    if _is_section_heading(line):
        return False

    if _contains_title_keyword(line):
        return False

    if _looks_like_technical_line(line):
        return False

    return True


# ============================================================
# NAME EXTRACTION
# ============================================================

def extract_name(text):

    if not text:
        return None

    lines = text.splitlines()

    for line in lines[:5]:

        line = line.strip()

        if not line:
            continue

        # Contact information is not a name.
        if "@" in line:
            continue

        if "linkedin.com" in line.lower():
            continue

        if "github.com" in line.lower():
            continue

        # Phone numbers / numeric content are not names.
        if re.search(r"\d", line):
            continue

        if _looks_like_name(line):
            return line

    return None