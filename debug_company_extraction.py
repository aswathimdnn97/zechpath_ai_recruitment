"""Debug script to examine raw resume text and experience blocks"""

from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import clean_text
from document_processing.resume.resume_normalizer import normalize_text
from document_processing.common.handling_layout import fix_layout
from document_processing.resume.text_reconstruction import text_reconstructor
from document_processing.resume.section_detector import detect_sections
from document_processing.resume.headings import headings
from document_processing.resume.entity_extracter.experience.experince_block_splitter import split_experience_blocks
from document_processing.resume.entity_extracter.experience.company_extractor import extract_companies

# Extract and process resume
file = "data/resume/pdf/python_django.pdf"
raw_text = extract_raw_text(file)
print("=" * 80)
print("RAW TEXT FROM PDF:")
print("=" * 80)
print(raw_text)
print("\n" + "=" * 80)

# Clean and normalize
cleaned_text = clean_text(raw_text)
handled_text = fix_layout(cleaned_text)
text_reconstructed = text_reconstructor(handled_text)
normalized_text = normalize_text(text_reconstructed)
section_detected_text = detect_sections(normalized_text, headings)

# Get experience section
if "experience" in section_detected_text:
    experience_section = section_detected_text["experience"]
    print("\nEXPERIENCE SECTION:")
    print("=" * 80)
    print(experience_section)
    print("\n" + "=" * 80)
    
    # Split into blocks
    experience_blocks = split_experience_blocks(experience_section)
    print("\nEXPERIENCE BLOCKS:")
    print("=" * 80)
    for i, block in enumerate(experience_blocks):
        print(f"\n--- BLOCK {i} ---")
        for line in block:
            print(repr(line))
        
        # Try to extract companies from this block
        companies = extract_companies(block)
        print(f"Extracted companies: {companies}")
