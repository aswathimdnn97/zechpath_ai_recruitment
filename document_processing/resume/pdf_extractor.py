import pdfplumber


def extract_pdf_text(path):
    pages = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text(
                x_tolerance=2,
                y_tolerance=3,
                layout=True,
            )
            if text:
                pages.append(text)

    return "\n".join(pages)