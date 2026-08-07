import os
from parsers.pdf_reader import read_pdf
from parsers.docx_reader import read_docx
import sys

def extract_raw_text(file):
    sys.stdout.reconfigure(encoding="utf-8")


    extension=os.path.splitext(file)[1].lower()

    if(extension==".pdf"):
        text=read_pdf(file)
    elif(extension==".docx"):
        text=read_docx(file)
    else:
        print("Unsupported file format.")
        exit()
    return(text)