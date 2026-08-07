from document_processing.common.handling_layout import fix_layout

def test_layout_handler():
    text="""Worked on ZechPath AI
    recruitment system using python"""
    handled_text=fix_layout(text)
    assert "Worked on ZechPath AI recruitment system using python" in handled_text
