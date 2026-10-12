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
# REAL ATS PIPELINE
# ============================================================

from parsers.pdf_reader import read_pdf

from document_processing.common.cleaner import clean_text
from document_processing.common.handling_layout import fix_layout
from document_processing.resume.text_reconstruction import reconstruct_text
from document_processing.resume.resume_normalizer import normalize_text


# ============================================================
# TEST PDF
# ============================================================

PDF_PATH = (
    PROJECT_ROOT
    / "data"
    / "validation"
    / "edge_case_resumes"
    / "table_resume.pdf"
)


# ============================================================
# PROBLEMATIC CONTENT
# ============================================================

TARGETS = [
    "Area",
    "Technologies / Tools",
    "Period",
    "Role / Company",
    "Responsibilities",
    "Stack",
    "Description",
    "Backend Python",
    "Database PostgreSQL",
]


# ============================================================
# PRINT STAGE
# ============================================================

def print_stage(
    stage_name,
    text,
):
    print()
    print("=" * 80)
    print(stage_name)
    print("=" * 80)

    if not text:
        print("<EMPTY>")
        return

    print(text)

    print()
    print("-" * 80)
    print("TARGET DETECTION")
    print("-" * 80)

    lowered = text.lower()

    found_count = 0

    for target in TARGETS:

        if target.lower() in lowered:

            print(
                f"[FOUND] {target}"
            )

            found_count += 1

        else:

            print(
                f"[NOT FOUND] {target}"
            )

    print()
    print(
        f"Targets found : "
        f"{found_count}/{len(TARGETS)}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 80)
    print("TABLE RESUME PIPELINE TRACE")
    print("=" * 80)

    print()
    print(
        f"PDF: {PDF_PATH}"
    )

    if not PDF_PATH.exists():

        print()
        print(
            "ERROR: PDF not found"
        )

        return 1

    # --------------------------------------------------------
    # 1. PDF READER
    # --------------------------------------------------------

    raw_text = read_pdf(
        str(PDF_PATH)
    )

    print_stage(
        "STAGE 1 - read_pdf()",
        raw_text,
    )

    # --------------------------------------------------------
    # 2. CLEANER
    # --------------------------------------------------------

    cleaned = clean_text(
        raw_text
    )

    print_stage(
        "STAGE 2 - clean_text()",
        cleaned,
    )

    # --------------------------------------------------------
    # 3. LAYOUT
    # --------------------------------------------------------

    layout_fixed = fix_layout(
        cleaned
    )

    print_stage(
        "STAGE 3 - fix_layout()",
        layout_fixed,
    )

    # --------------------------------------------------------
    # 4. RECONSTRUCTION
    # --------------------------------------------------------

    reconstructed = reconstruct_text(
        layout_fixed
    )

    print_stage(
        "STAGE 4 - reconstruct_text()",
        reconstructed,
    )

    # --------------------------------------------------------
    # 5. NORMALIZATION
    # --------------------------------------------------------

    normalized = normalize_text(
        reconstructed
    )

    print_stage(
        "STAGE 5 - normalize_text()",
        normalized,
    )

    # --------------------------------------------------------
    # FINAL ANALYSIS
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("PIPELINE TRACE RESULT")
    print("=" * 80)

    stages = [
        ("read_pdf", raw_text),
        ("clean_text", cleaned),
        ("fix_layout", layout_fixed),
        ("reconstruct_text", reconstructed),
        ("normalize_text", normalized),
    ]

    print()

    for stage_name, text in stages:

        lowered = (
            text.lower()
            if text
            else ""
        )

        found = [
            target
            for target in TARGETS
            if target.lower() in lowered
        ]

        print(
            f"{stage_name:<20} "
            f"{len(found):>2}/{len(TARGETS)} "
            f"targets"
        )

        if found:

            print(
                "  -> "
                + ", ".join(found)
            )

    print()
    print("=" * 80)
    print("TRACE COMPLETE")
    print("=" * 80)

    return 0


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    sys.exit(main())