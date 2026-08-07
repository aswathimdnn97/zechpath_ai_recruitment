import pdfplumber

def read_pdf(file):
    
    """Read a PDF resume and return its text"""
    
    text=""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text=page.page_text = page.extract_text(
                x_tolerance=2,
                y_tolerance=2
            )
            if(page_text):
                text=text+page_text+"\n"
    return text
