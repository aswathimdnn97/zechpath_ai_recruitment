"""
Project Extraction Validation
-----------------------------

Validates the complete project extraction pipeline.

Fields:
    - project_name
    - description
    - technologies
    - url
"""

from document_processing.resume.entity_extracter.projects.project_extraction_pipeline import (
    extract_projects,
)


TOTAL = 0
PASSED = 0
FAILED = 0


# ============================================================
# TEST RUNNER
# ============================================================

def run_test(test_name, section, expected):
    global TOTAL, PASSED, FAILED

    TOTAL += 1

    try:
        result = extract_projects(section)

        success = True
        failures = []

        # ----------------------------------------------------
        # Validate project count
        # ----------------------------------------------------

        expected_count = expected.get("_count")

        if expected_count is not None:
            if len(result) != expected_count:
                success = False
                failures.append(
                    f"project count: expected {expected_count}, "
                    f"got {len(result)}"
                )

        # ----------------------------------------------------
        # Validate project fields
        # ----------------------------------------------------

        expected_projects = expected.get("projects", [])

        for index, expected_project in enumerate(expected_projects):

            if index >= len(result):
                success = False
                failures.append(
                    f"project[{index}]: missing"
                )
                continue

            actual_project = result[index]

            for field, expected_value in expected_project.items():

                actual_value = actual_project.get(field)

                if actual_value != expected_value:
                    success = False
                    failures.append(
                        f"project[{index}].{field}: "
                        f"expected {expected_value!r}, "
                        f"got {actual_value!r}"
                    )

        if success:
            PASSED += 1
            print(f"[PASS] {test_name}")

        else:
            FAILED += 1
            print(f"[FAIL] {test_name}")

            for failure in failures:
                print(f"       {failure}")

            print(f"       RESULT: {result}")

    except Exception as exc:

        FAILED += 1

        print(f"[FAIL] {test_name}")
        print(
            f"       Exception: "
            f"{type(exc).__name__}: {exc}"
        )


# ============================================================
# 1. BASIC PROJECT
# ============================================================

run_test(
    "Basic project extraction",
    [
        "AI Resume Screening System",
        "Developed an AI-based resume screening platform.",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "AI Resume Screening System",
                "description": (
                    "Developed an AI-based resume screening platform."
                ),
            }
        ],
    },
)


# ============================================================
# 2. PROJECT + TECHNOLOGIES
# ============================================================

run_test(
    "Project technology extraction",
    [
        "AI Resume Screening System",
        "Developed an AI-based resume screening platform.",
        "Technologies: Python, FastAPI, PostgreSQL",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "AI Resume Screening System",
                "description": (
                    "Developed an AI-based resume screening platform."
                ),
                "technologies": [
                    "Python",
                    "FastAPI",
                    "PostgreSQL",
                ],
            }
        ],
    },
)


# ============================================================
# 3. TECH STACK
# ============================================================

run_test(
    "Tech stack extraction",
    [
        "E-Commerce Platform",
        "Built a full-stack e-commerce application.",
        "Tech Stack: React | Node.js | Express | MongoDB",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "E-Commerce Platform",
                "technologies": [
                    "React",
                    "Node.js",
                    "Express.js",
                    "MongoDB",
                ],
            }
        ],
    },
)


# ============================================================
# 4. TOOLS
# ============================================================

run_test(
    "Tools extraction",
    [
        "Cloud Deployment Project",
        "Deployed a web application to the cloud.",
        "Tools: Docker; Kubernetes; AWS; Git",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "Cloud Deployment Project",
                "technologies": [
                    "Docker",
                    "Kubernetes",
                    "AWS",
                    "Git",
                ],
            }
        ],
    },
)


# ============================================================
# 5. TECHNOLOGIES USED
# ============================================================

run_test(
    "Technologies used extraction",
    [
        "Machine Learning Project",
        "Implemented a machine learning model.",
        "Technologies Used: Python, NumPy, Pandas",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "Machine Learning Project",
                "technologies": [
                    "Python",
                    "NumPy",
                    "Pandas",
                ],
            }
        ],
    },
)


# ============================================================
# 6. URL EXTRACTION
# ============================================================

run_test(
    "Project GitHub URL",
    [
        "AI Resume Screening System",
        "Developed an ATS platform.",
        "GitHub: https://github.com/example/project",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "AI Resume Screening System",
                "url": "https://github.com/example/project",
            }
        ],
    },
)


# ============================================================
# 7. URL WITHOUT PROTOCOL
# ============================================================

run_test(
    "Project GitHub URL without protocol",
    [
        "AI Resume Screening System",
        "Developed an ATS platform.",
        "GitHub: github.com/example/project",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "url": "https://github.com/example/project",
            }
        ],
    },
)


# ============================================================
# 8. DEMO URL
# ============================================================

run_test(
    "Project demo URL",
    [
        "Portfolio Website",
        "Created a personal portfolio website.",
        "Demo: https://example.com",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "url": "https://example.com",
            }
        ],
    },
)


# ============================================================
# 9. MARKDOWN URL
# ============================================================

run_test(
    "Markdown GitHub URL",
    [
        "AI Resume Screening System",
        "Developed an ATS platform.",
        "GitHub: [https://github.com/example/project]"
    ],
    {
        "_count": 1,
        "projects": [
            {
                "url": "https://github.com/example/project",
            }
        ],
    },
)


# ============================================================
# 10. DESCRIPTION MULTIPLE LINES
# ============================================================

run_test(
    "Multi-line project description",
    [
        "Student Management System",
        "Developed a web application for managing students.",
        "Implemented authentication and role-based access.",
        "Added CRUD functionality for student records.",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "Student Management System",
                "description": (
                    "Developed a web application for managing students. "
                    "Implemented authentication and role-based access. "
                    "Added CRUD functionality for student records."
                ),
            }
        ],
    },
)


# ============================================================
# 11. METADATA SHOULD NOT ENTER DESCRIPTION
# ============================================================

run_test(
    "Metadata excluded from description",
    [
        "AI Resume Screening System",
        "Developed an AI-based resume screening platform.",
        "Technologies: Python, FastAPI",
        "GitHub: https://github.com/example/project",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "description": (
                    "Developed an AI-based resume screening platform."
                ),
                "technologies": [
                    "Python",
                    "FastAPI",
                ],
                "url": "https://github.com/example/project",
            }
        ],
    },
)


# ============================================================
# 12. EXPLICIT PROJECT LABEL
# ============================================================

run_test(
    "Explicit Project label",
    [
        "Project: AI Resume Screening System",
        "Developed an ATS platform.",
        "Technologies: Python, FastAPI",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "AI Resume Screening System",
                "description": "Developed an ATS platform.",
                "technologies": [
                    "Python",
                    "FastAPI",
                ],
            }
        ],
    },
)


# ============================================================
# 13. PROJECT NAME WITH DASH
# ============================================================

run_test(
    "Project label with hyphen",
    [
        "Project - E-Commerce Platform",
        "Built a full-stack shopping application.",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "E-Commerce Platform",
            }
        ],
    },
)


# ============================================================
# 14. PROJECT NAME SHOULD NOT BE DATE
# ============================================================

run_test(
    "Date should not become project name",
    [
        "AI Resume Screening System",
        "2025",
        "Developed an ATS platform.",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "AI Resume Screening System",
            }
        ],
    },
)


# ============================================================
# 15. PROJECT NAME SHOULD NOT BE TECHNOLOGY LABEL
# ============================================================

run_test(
    "Technology label should not become project name",
    [
        "AI Resume Screening System",
        "Technologies: Python, FastAPI",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "AI Resume Screening System",
            }
        ],
    },
)


# ============================================================
# 16. MULTIPLE PROJECTS
# ============================================================

run_test(
    "Multiple projects",
    [
        "AI Resume Screening System",
        "Developed an ATS platform.",
        "Technologies: Python, FastAPI",
        "E-Commerce Platform",
        "Built an online shopping application.",
        "Technologies: React, Node.js, MongoDB",
    ],
    {
        "_count": 2,
        "projects": [
            {
                "project_name": "AI Resume Screening System",
                "technologies": [
                    "Python",
                    "FastAPI",
                ],
            },
            {
                "project_name": "E-Commerce Platform",
                "technologies": [
                    "React",
                    "Node.js",
                    "MongoDB",
                ],
            },
        ],
    },
)


# ============================================================
# 17. MULTIPLE PROJECTS WITH EXPLICIT LABELS
# ============================================================

run_test(
    "Multiple explicitly labelled projects",
    [
        "Project: Resume Analyzer",
        "Developed a resume parsing application.",
        "Technologies: Python, spaCy",
        "Project: E-Commerce Platform",
        "Developed an online shopping platform.",
        "Technologies: Django, React, PostgreSQL",
    ],
    {
        "_count": 2,
        "projects": [
            {
                "project_name": "Resume Analyzer",
            },
            {
                "project_name": "E-Commerce Platform",
            },
        ],
    },
)


# ============================================================
# 18. DUPLICATE TECHNOLOGIES
# ============================================================

run_test(
    "Duplicate technologies removed",
    [
        "AI Platform",
        "Developed an AI platform.",
        "Technologies: Python, Python, FastAPI, Python",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "technologies": [
                    "Python",
                    "FastAPI",
                ],
            }
        ],
    },
)


# ============================================================
# 19. EMPTY INPUT
# ============================================================

run_test(
    "Empty input",
    [],
    {
        "_count": 0,
    },
)


# ============================================================
# 20. NONE INPUT
# ============================================================

run_test(
    "None input",
    None,
    {
        "_count": 0,
    },
)


# ============================================================
# 21. PROJECT WITH ONLY NAME
# ============================================================

run_test(
    "Project with only name",
    [
        "Weather Application",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "Weather Application",
                "description": None,
                "technologies": [],
                "url": None,
            }
        ],
    },
)


# ============================================================
# 22. REALISTIC PROJECT
# ============================================================

run_test(
    "Realistic full project",
    [
        "AI Resume Screening System",
        "Developed an AI-powered recruitment platform that "
        "automatically parses resumes and compares candidates "
        "against job descriptions.",
        "Technologies: Python, FastAPI, PostgreSQL, spaCy",
        "GitHub: https://github.com/example/ats",
    ],
    {
        "_count": 1,
        "projects": [
            {
                "project_name": "AI Resume Screening System",
                "technologies": [
                    "Python",
                    "FastAPI",
                    "PostgreSQL",
                    "spaCy",
                ],
                "url": "https://github.com/example/ats",
            }
        ],
    },
)


# ============================================================
# FINAL REPORT
# ============================================================

print()
print("=" * 70)
print("PROJECT EXTRACTION VALIDATION")
print("=" * 70)

print(f"Total tests : {TOTAL}")
print(f"Passed      : {PASSED}")
print(f"Failed      : {FAILED}")

pass_rate = (
    (PASSED / TOTAL) * 100
    if TOTAL
    else 0.0
)

print(f"Pass rate   : {pass_rate:.2f}%")
print("-" * 70)

if FAILED == 0:
    print("STATUS      : PASS")
else:
    print("STATUS      : FAIL")

print("=" * 70)