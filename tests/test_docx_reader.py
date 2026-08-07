from parsers.docx_reader import read_docx

def test_docx_reader():
    file="data/resume/docx/vvyndmqmqqgs.docx"
    text=read_docx(file)
    
    assert text is not None
    assert isinstance(text,str)
    assert len(text)>0