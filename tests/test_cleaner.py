from document_processing.common.cleaner import clean_text

def test_clean():
    
    text="Data Science\t\tEngineer\tIntern"
    cleaned_text=clean_text(text)
    assert "\t" not in cleaned_text
    assert cleaned_text=="Data Science Engineer Intern"

import pytest
    
@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (None, ""),
        ("", ""),
        ("  Python    Django  ", "Python Django"),
        ("Python\tDjango", "Python Django"),
        ("Python\n\n\nDjango", "Python\n\nDjango"),
        ("Python\x00Django", "PythonDjango"),
        ("C# C++ Node.js", "C# C++ Node.js"),
        ("Python\nReact", "Python\nReact"),
        ("• Python\n• Django", "- Python\n- Django"),
        ("Python\u00A0Django", "Python Django"),
    ],
)
def test_clean_text(source, expected):
    assert clean_text(source) == expected


def test_replacement_character_does_not_join_words():
    assert clean_text("Python\uFFFDDjango") == "Python Django"


def test_non_string_input_raises_type_error():
    with pytest.raises(TypeError):
        clean_text(123)

@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (None, ""),
        ("", ""),
        ("Python    Django", "Python Django"),
        ("Python\tDjango", "Python Django"),
        ("Python\x00Django", "Python Django"),
        ("C# C++", "C# C++"),
        ("Python_Course", "Python_Course"),
        ("RES_EVAL_010", "RES_EVAL_010"),
        ("100% complete", "100% complete"),
        ("Python\n\n\nDjango", "Python\n\nDjango"),
        ("\uFFFD", ""),
    ],
)
def test_clean_text(source, expected):
    assert clean_text(source) == expected


def test_phone_prefix_is_preserved():
    assert clean_text("+91 98XXXXXX73") == "+91 98XXXXXX73"


def test_stray_percent_before_phone_prefix():
    assert clean_text("% +91 98XXXXXX73") == "+91 98XXXXXX73"
    