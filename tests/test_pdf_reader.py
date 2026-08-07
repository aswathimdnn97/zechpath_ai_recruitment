from parsers.pdf_reader import read_pdf

def test_pdf_reader():
    file="data/resume/pdf/ptvypkdbzzyk.pdf"
    
    text=read_pdf(file)
    
    assert text is not None
    assert isinstance(text,str)
    assert len(text)>0
    
