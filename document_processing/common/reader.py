import os

from parsers.pdf_reader import read_pdf
from parsers.docx_reader import read_docx


def extract_raw_text(
    file_path,
    debug=False,
):
    """
    Extract raw text from a supported resume file.
    """

    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        return read_pdf(
            file_path,
            debug=debug,
        )

    if extension == ".docx":
        return read_docx(file_path)

    raise ValueError(
        f"Unsupported file format: {extension}"
    )