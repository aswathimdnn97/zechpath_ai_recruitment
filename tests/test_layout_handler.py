from document_processing.common.handling_layout import fix_layout
from document_processing.job_description.heading import JD_HEADINGS


def test_layout_handler():
    text="""Worked on ZechPath AI
    recruitment system using python"""
    handled_text=fix_layout(text)
    assert "Worked on ZechPath AI recruitment system using python" in handled_text


def test_fix_layout_preserves_normalized_headings():
    text = (
        "location\n"
        "Bangalore, Karnataka\n"
        "employment_type\n"
        "Full-time\n"
        "experience\n"
        "2 - 4 Years\n"
        "job_summary\n"
        "We are looking for a passionate Python Developer to join our engineering team.\n"
    )

    handled_text = fix_layout(text, headings=JD_HEADINGS)

    assert "Bangalore, Karnataka\nemployment_type" in handled_text
    assert "Full-time\nexperience" in handled_text
    assert "2 - 4 Years\njob_summary" in handled_text
