"""Debug script to examine education extraction"""

from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import clean_text
from document_processing.resume.resume_normalizer import normalize_text
from document_processing.common.handling_layout import fix_layout
from document_processing.resume.text_reconstruction import text_reconstructor
from document_processing.resume.section_detector import detect_sections
from document_processing.resume.headings import headings
from document_processing.resume.entity_extracter.education.education_block_splitter import split_education_blocks
from document_processing.resume.entity_extracter.education.institution_extractor import extract_institution, clean_institution_name
from document_processing.resume.entity_extracter.education.field_of_study_extractor import extract_field_of_study

# Extract and process resume
file = "data/resume/pdf/python_django.pdf"
raw_text = extract_raw_text(file)

# Clean and normalize
cleaned_text = clean_text(raw_text)
handled_text = fix_layout(cleaned_text)
text_reconstructed = text_reconstructor(handled_text)
normalized_text = normalize_text(text_reconstructed)
section_detected_text = detect_sections(normalized_text, headings)

# Get education section
if "education" in section_detected_text:
    education_section = section_detected_text["education"]
    print("\n" + "=" * 80)
    print("EDUCATION SECTION:")
    print("=" * 80)
    print(education_section)
    print("\n" + "=" * 80)
    
    # Split into blocks
    education_blocks = split_education_blocks(education_section)
    print("\nEDUCATION BLOCKS:")
    print("=" * 80)
    for i, block in enumerate(education_blocks):
        print(f"\n--- BLOCK {i} ---")
        for line in block:
            print(repr(line))
        
        # Try to extract institution and field
        institution = extract_institution(block)
        field = extract_field_of_study(block)
        print(f"Extracted Institution: {institution}")
        print(f"Extracted Field: {field}")
