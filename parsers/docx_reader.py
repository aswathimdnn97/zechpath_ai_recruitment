from docx import Document
def read_docx(file):
    """Read a DOCX resume and return its text."""
    document=Document(file)
    
    text_parts = []
    #read paragraph
    for paragraph in document.paragraphs:
        if(paragraph.text.strip()!=""):
            text_parts.append(paragraph.text + "\n")

    #read table
    for table in document.tables:
        for row in table.rows:
            for cell in row.cells:
                cell_text = cell.text.strip()
                if cell_text:
                    text_parts.append(cell.text + " ")
        text_parts.append("\n")
        
    return "".join(text_parts)