from document_processing.common.cleaner import clean_text

def test_clean():
    
    text="Data Science\t\tEngineer\tIntern"
    cleaned_text=clean_text(text)
    assert "\t" not in cleaned_text
    assert cleaned_text=="Data Science Engineer Intern"
    
    