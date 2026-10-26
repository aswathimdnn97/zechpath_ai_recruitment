import json
from pathlib import Path

from document_processing.resume.section_detector import detect_sections


TEMPLATE_CASES = [
    {
        "name": "modern_single_column",
        "text": (
            "Backend Trainee\n"
            "Code Nest Academy\n"
            "Aug 2025 - Mar 2026\n"
            "Prepared SQL queries and documented application workflows.\n"
            "\n"
            "Bachelor of Technology in Computer Science and Engineering\n"
            "KTU\n"
            "2026\n"
            "\n"
            "Python, SQL, JavaScript, HTML, CSS, Git"
        ),
        "expected": {"experience", "education", "skills"},
    },
    {
        "name": "compact_unstructured",
        "text": (
            "Experienced Python Developer with 2 years in backend development. Built APIs using Django and FastAPI, worked with SQL, MySQL, PostgreSQL, AWS, Docker. "
            "Bachelor of Technology, Computer Science and Engineering, KTU, 2022. "
            "Skills: Python, SQL, FastAPI, Django, JavaScript, React, Git."
        ),
        "expected": {"experience", "education", "skills"},
    },
    {
        "name": "headings_present",
        "text": (
            "Skills\n"
            "Python, SQL, JavaScript, React, Django\n"
            "Experience\n"
            "Backend Trainee - Code Nest Academy\n"
            "Aug 2025 - Mar 2026\n"
            "Prepared SQL queries and documented application workflows.\n"
            "Education\n"
            "Bachelor of Technology in Computer Science and Engineering\n"
            "KTU\n"
            "2026"
        ),
        "expected": {"experience", "education", "skills"},
    },
    {
        "name": "dense_paragraph",
        "text": (
            "Backend Trainee at Code Nest Academy, Aug 2025 - Mar 2026. Prepared SQL queries and documented application workflows. "
            "Bachelor of Technology in Computer Science and Engineering from KTU, 2026. "
            "Skills: Python, SQL, JavaScript, React, Django, Git, AWS."
        ),
        "expected": {"experience", "education", "skills"},
    },
]


def benchmark_template_resilience():
    results = []
    for case in TEMPLATE_CASES:
        sections = detect_sections(case["text"])
        matched = set(sections.keys()) & case["expected"]
        score = len(matched) / len(case["expected"])
        results.append({
            "name": case["name"],
            "score": round(score, 3),
            "detected_sections": sorted(sections.keys()),
        })

    summary = {
        "average_score": round(sum(item["score"] for item in results) / len(results), 3),
        "results": results,
    }

    output_path = Path(__file__).resolve().parents[1] / "data" / "resume" / "benchmark" / "layout_benchmark.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    benchmark = benchmark_template_resilience()
    print(json.dumps(benchmark, indent=2))
