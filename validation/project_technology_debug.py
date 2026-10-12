from document_processing.resume.entity_extracter.projects.project_technologies_extractor import (
    extract_project_technologies,
)

from document_processing.resume.entity_extracter.projects.project_technology_normalizer import (
    normalize_project_technologies,
)


tests = [
    [
        "AI Resume Screening System",
        "Developed an AI-based resume screening platform.",
        "Technologies: Python, FastAPI, PostgreSQL",
    ],
    [
        "E-Commerce Platform",
        "Built a full-stack e-commerce application.",
        "Tech Stack: React | Node.js | Express | MongoDB",
    ],
    [
        "Cloud Deployment Project",
        "Deployed a web application to the cloud.",
        "Tools: Docker; Kubernetes; AWS; Git",
    ],
    [
        "Machine Learning Project",
        "Implemented a machine learning model.",
        "Technologies Used: Python, NumPy, Pandas",
    ],
]


for i, block in enumerate(tests, start=1):

    print()
    print("=" * 70)
    print(f"TEST {i}")
    print("=" * 70)

    print("\nBLOCK:")
    for line in block:
        print(repr(line))

    raw = extract_project_technologies(block)

    print("\nRAW TECHNOLOGIES:")
    print(raw)

    normalized = normalize_project_technologies(raw)

    print("\nNORMALIZED TECHNOLOGIES:")
    print(normalized)