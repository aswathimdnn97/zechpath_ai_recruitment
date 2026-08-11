from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import clean_text
from document_processing.job_description.job_description_normalizer import normalize_jd
from document_processing.common.handling_layout import fix_layout
from document_processing.job_description.heading import JD_HEADINGS
from document_processing.common.parser import parse_document
from document_processing.job_description.jd_entity_extractor import extract_entities
from document_processing.common.json_writer import save_resume



def job_description_pipeline(file):
    
    # extract raw text
    raw_text=extract_raw_text(file)
    
    # cleaned raw text
    cleaned_text=clean_text(raw_text)
    
    # normalize jd
    normalized_jd=normalize_jd(cleaned_text)
    
    # fixed handle_layout
    handled_jd=fix_layout(normalized_jd, headings=JD_HEADINGS)
    
    # parse_jd
    parsed_jd=parse_document(handled_jd,JD_HEADINGS)
    
    # extract entity from parsed jd
    extracted_entity=extract_entities(parsed_jd)
    
    #save extracted entity
    save_resume(extracted_entity,"jd_json")
    
    
    
    return extracted_entity