from document_processing.resume.resume_normalizer import normalize_text

def test_norrmalizer():
    
    text="""Aswathi Madanan
    Technical Skills
    * Python
    
    * Numpy
    * Java
    """
    
    normalized_text=normalize_text(text)
    print(normalized_text)
    assert "skill" in normalized_text
    assert "Technical Skills" not in normalized_text