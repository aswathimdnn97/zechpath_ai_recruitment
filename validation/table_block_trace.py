import sys
from pathlib import Path


# ============================================================
# PROJECT ROOT
# ============================================================

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# PDF
# ============================================================

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "validation"
    / "edge_case_resumes"
    / "table_resume.pdf"
)


# ============================================================
# TARGETS
# ============================================================

TARGETS = [
    "CERTIFICATIONS",
    "Python Programming Fundamentals",
    "REST API Development with FastAPI",
    "SQL and PostgreSQL Essentials",
    "Backend Python",
    "Database PostgreSQL",
]


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("PYMUPDF BLOCK / POSITION TRACE")
    print("=" * 80)

    print()
    print("PDF:", PDF_PATH)

    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf

    document = pymupdf.open(str(PDF_PATH))

    try:

        for page_number, page in enumerate(
            document,
            start=1
        ):

            print()
            print("=" * 80)
            print(f"PAGE {page_number}")
            print("=" * 80)

            blocks = page.get_text("blocks")

            for index, block in enumerate(blocks):

                if len(block) < 5:
                    continue

                x0, y0, x1, y1, text = block[:5]

                text = text.strip()

                if not text:
                    continue

                print()
                print(
                    f"BLOCK {index}"
                )

                print(
                    f"POSITION : "
                    f"x0={x0:.1f}, "
                    f"y0={y0:.1f}, "
                    f"x1={x1:.1f}, "
                    f"y1={y1:.1f}"
                )

                print(
                    "TEXT:"
                )

                print(text)

                for target in TARGETS:

                    if target.lower() in text.lower():

                        print(
                            f"  >>> TARGET: {target}"
                        )

    finally:

        document.close()

    print()
    print("=" * 80)
    print("BLOCK TRACE COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()