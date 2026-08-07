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
from document_processing.resume.candidate_profile.candidate_profile_builder import (
    build_candidate_profile
)

def resume_pipeline(file):
    
    # file="data/resume/docx/vvyndmqmqqgs.docx"

    """extract raw text"""
    raw_text=extract_raw_text(file)
    
    cleaned_text=clean_text(raw_text)
    
    handled_text=fix_layout(cleaned_text)
    
    normalized_text=normalize_text(handled_text)
    
    section_detected_text=detect_sections(normalized_text,headings)
    print(section_detected_text.keys())
    print(section_detected_text)
    
    # ----------------personal information entity----------------------------
    personal_information = extract_personal_information(normalized_text)
    # ----------------skill entity----------------------------
    
    skill_extracter=section_detected_text.get("skills","")
    
    skill_from_skill_extractor=extract_skill(skill_extracter)
    
    synonym_resolved_skill=resolve_synonyms(skill_from_skill_extractor)
    
    validated_skill=validate_skills(synonym_resolved_skill)
    
    stack_skills=expand_skill_stacks(validated_skill)
    
    # save_resume(normalized_text,"resume1")
    
    # experience-----------------------------------------
    experience_section = section_detected_text.get("experience", [])

    experience_data = experience_extractor(experience_section)
   
    # print(type(experience_section))
    # print(experience_section)
   
    # return experience_data

 # return validated_skill
 
    # -----------------build candidate profile-----------------
    candidate_profile = build_candidate_profile(
        personal_information=personal_information,
        education=section_detected_text.get("education", []),
        experience=experience_data,
        skills=stack_skills,
        projects=section_detected_text.get("projects", []),
        certifications=section_detected_text.get("certifications", [])
    )
    
    return candidate_profile
 
