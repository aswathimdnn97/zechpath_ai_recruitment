import re
from pathlib import Path

import pymupdf
import pdfplumber


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RESUME_DIR = PROJECT_ROOT / "data" / "resumes"


def extract_pdfplumber(file_path: Path) -> str:

    text_parts = []

    with pdfplumber.open(file_path) as pdf:

        for page in pdf.pages:

            page_text = page.extract_text(
                x_tolerance=2,
                y_tolerance=2
            )

            if page_text:
                text_parts.append(page_text)

    return "\n".join(text_parts)


def extract_pymupdf(file_path: Path) -> str:

    text_parts = []

    with pymupdf.open(str(file_path)) as document:

        for page in document:

            page_text = page.get_text("text")

            if page_text:
                text_parts.append(page_text)

    return "\n".join(text_parts)


def normalize_text(text: str) -> str:

    text = text.lower()

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Normalize common punctuation spacing
    text = re.sub(r"\s+([,.;:])", r"\1", text)

    return text.strip()


def compare_files(file_path: Path):

    pdfplumber_text = extract_pdfplumber(file_path)
    pymupdf_text = extract_pymupdf(file_path)

    normalized_pdfplumber = normalize_text(pdfplumber_text)
    normalized_pymupdf = normalize_text(pymupdf_text)

    words_pdfplumber = normalized_pdfplumber.split()
    words_pymupdf = normalized_pymupdf.split()

    set_pdfplumber = set(words_pdfplumber)
    set_pymupdf = set(words_pymupdf)

    common_words = set_pdfplumber & set_pymupdf

    if set_pdfplumber or set_pymupdf:

        word_similarity = (
            len(common_words)
            / len(set_pdfplumber | set_pymupdf)
        ) * 100

    else:

        word_similarity = 100.0

    return {
        "pdfplumber_chars": len(pdfplumber_text),
        "pymupdf_chars": len(pymupdf_text),

        "pdfplumber_words": len(words_pdfplumber),
        "pymupdf_words": len(words_pymupdf),

        "word_similarity": word_similarity,

        "pdfplumber_text": normalized_pdfplumber,
        "pymupdf_text": normalized_pymupdf,
    }


def main():

    files = sorted(
        file_path
        for file_path in RESUME_DIR.iterdir()
        if file_path.suffix.lower() == ".pdf"
    )

    print("=" * 100)
    print("PDF TEXT EXTRACTION COMPARISON")
    print("=" * 100)

    total_pdfplumber_words = 0
    total_pymupdf_words = 0

    for file_path in files:

        result = compare_files(file_path)

        total_pdfplumber_words += result["pdfplumber_words"]
        total_pymupdf_words += result["pymupdf_words"]

        print()
        print(file_path.name)

        print(
            f"  pdfplumber : "
            f"{result['pdfplumber_words']} words, "
            f"{result['pdfplumber_chars']} chars"
        )

        print(
            f"  PyMuPDF    : "
            f"{result['pymupdf_words']} words, "
            f"{result['pymupdf_chars']} chars"
        )

        print(
            f"  Word similarity : "
            f"{result['word_similarity']:.2f}%"
        )

        if result["word_similarity"] < 95:

            print("  ⚠ REVIEW REQUIRED")

            print()
            print("  pdfplumber:")
            print(" ", result["pdfplumber_text"][:500])

            print()
            print("  PyMuPDF:")
            print(" ", result["pymupdf_text"][:500])

    print()
    print("=" * 100)
    print("TOTAL")
    print("=" * 100)

    print(
        f"pdfplumber total words : "
        f"{total_pdfplumber_words}"
    )

    print(
        f"PyMuPDF total words    : "
        f"{total_pymupdf_words}"
    )


if __name__ == "__main__":
    main()