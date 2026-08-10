from document_processing.common.reader import extract_raw_text
from document_processing.common.cleaner import clean_text
from document_processing.resume.resume_normalizer import normalize_text
from document_processing.common.handling_layout import fix_layout
from document_processing.common.json_writer import save_resume
from document_processing.resume.section_detector import detect_sections
from document_processing.resume.headings import headings
from document_processing.resume.entity_extracter.skill.synonym_resolver import resolve_synonyms
from document_processing.resume.entity_extracter.skill.stack_resolver import expand_skill_stacks
from document_processing.resume.entity_extracter.skill.skill_extractor import extract_skill
from document_processing.resume.entity_extracter.skill.spelling_resolver import resolve_spelling
from document_processing.resume.entity_extracter.skill.master_skill_validator import validate_skills
from document_processing.resume.entity_extracter.personal_information.personal_information_extractor import extract_personal_information

import sys
import os
from document_processing.resume.entity_extracter.experience.experinece_pipeline import experience_extractor
from document_processing.resume.candidate_profile.candidate_profile_builder import build_candidate_profile
from document_processing.resume.entity_extracter.education.education_pipeline import education_pipeline

from document_processing.resume.entity_extracter.certifications.certification_pipeline import certification_pipeline
from document_processing.resume.text_reconstruction import text_reconstructor
from document_processing.resume.entity_extracter.skill.skill_list_splitter import split_skill_line
def resume_pipeline(file):
    
    # file="data/resume/docx/vvyndmqmqqgs.docx"

    """extract raw text"""
    raw_text=extract_raw_text(file)
    
    cleaned_text=clean_text(raw_text)
    
    handled_text=fix_layout(cleaned_text)
    
    text_reconstructed=text_reconstructor(handled_text)
    
    normalized_text=normalize_text(text_reconstructed)
    
    section_detected_text=detect_sections(normalized_text,headings)
    print(section_detected_text.keys())
    print(section_detected_text)
    
    # ----------------personal information entity----------------------------
    personal_information = extract_personal_information(normalized_text)
    # ----------------skill entity----------------------------
    
    skill_extracter=section_detected_text.get("skills","")
    
    skill_splitter=split_skill_line(skill_extracter)
    
    if skill_splitter:
        skill_from_skill_extractor = skill_splitter
    else:
        skill_from_skill_extractor = extract_skill(skill_extracter)
    
    synonym_resolved_skill=resolve_synonyms(skill_from_skill_extractor)
    
    validated_skill=validate_skills(synonym_resolved_skill)
    
    stack_skills=expand_skill_stacks(validated_skill)
    
    
    # experience-----------------------------------------
    experience_section = section_detected_text.get("experience", [])

    experience_data = experience_extractor(experience_section)
   
    # education--------------------------------------------
    education_section = section_detected_text.get("education", [])
    education_data = education_pipeline(education_section)
 
 
    #----------------------------------------------------------
    # certification
    #----------------------------------------------------------
    certification_section=section_detected_text.get("certifications")
    certificate_data=certification_pipeline(certification_section)
    
    
    
    # -----------------build candidate profile-----------------
    candidate_profile = build_candidate_profile(
    personal_information=personal_information,
    education=education_data,
    experience=experience_data,
    skills=stack_skills,
    projects=section_detected_text.get("projects", []),
    certifications=certificate_data
)
    
    return candidate_profile
 
