from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import clean_text
from document_processing.job_description.job_description_normalizer import normalize_jd
from document_processing.common.handling_layout import fix_layout
from document_processing.job_description.heading import JD_HEADINGS
from document_processing.common.parser import parse_document
from document_processing.job_description.jd_entity_extractor import extract_entities
from document_processing.common.json_writer import save_file


def job_description_pipeline(file, job_id: str) -> dict:
    """
    Process a job description and extract structured entities.

    Pipeline:
        1. Extract raw text
        2. Clean text
        3. Normalize text
        4. Fix document layout
        5. Parse sections
        6. Extract JD entities
        7. Add job ID
        8. Save extracted data
    """

    if not job_id:
        raise ValueError("job_id must not be empty.")

    # 1. Extract raw text from the uploaded document.
    raw_text = extract_raw_text(file)

    if not raw_text or not raw_text.strip():
        raise ValueError("The job description contains no readable text.")

    # 2. Clean extracted text.
    cleaned_text = clean_text(raw_text)

    # 3. Normalize the job description.
    normalized_jd = normalize_jd(cleaned_text)

    # 4. Fix layout and heading alignment.
    handled_jd = fix_layout(
        normalized_jd,
        headings=JD_HEADINGS,
    )

    # 5. Parse the document into sections.
    parsed_jd = parse_document(
        handled_jd,
        JD_HEADINGS,
    )

    # 6. Extract structured entities.
    extracted_entity = extract_entities(parsed_jd)

    if not isinstance(extracted_entity, dict):
        raise TypeError(
            "extract_entities() must return a dictionary."
        )

    # 7. Preserve the authoritative job ID supplied by the caller.
    extracted_entity["job_id"] = job_id

    # 8. Save the extracted job description.
    save_file(extracted_entity, file)

    return extracted_entity
