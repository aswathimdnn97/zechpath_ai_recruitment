
import re
from  document_processing.resume.nlp_resolver import resolve_heading,build_section_docs
from document_processing.resume.headings import headings

# Build the SpaCy documents
section_docs = build_section_docs(headings)

def normalize_text(text):
   
    heading = {
        "professional summary": "summary",
        "summary": "summary",
        "career summary": "summary",
        "profile summary": "summary",
        "objective": "summary",
        "career objective": "summary",

        "technical skills": "skills",
        "core skills": "skills",
        "key skills": "skills",
        "skills": "skills",
        "skills and interests":"skills",

        "education": "education",
        "academic qualification": "education",
        "academic qualifications": "education",
        "qualification": "education",
        "qualifications": "education",

        "experience": "experience",
        "work experience": "experience",
        "professional experience": "experience",
        "employment history": "experience",
        "employment history": "experience",
        "position of responsibility":"experience",

        "projects": "projects",
        "academic projects": "projects",
        "personal projects": "projects",

        "certifications": "certifications",
        "certification": "certifications",

        "achievements": "achievements",
        "awards": "achievements",

        "languages": "languages",

        "interests": "interests",

        "references": "references",
        "other activities and projects":"projects",
        "extra-cirrucular":"activities",
        "extra-cirrucular activities":"activities",
        "documentations":"activities",
        "declaration":"declaration",
        "internship/trainings":"experience",
        "experience / internship / training":"experience",
        "research publication": "publications",
        "publications": "publications",
        "publication": "publications",
        "articles": "publications",
    }
    
    # 3. Process line-by-line
    lines = text.split("\n")
    normalized_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Normalize bullet points
        line = re.sub(r"^[•●◦▪■*-]\s*", "", line)
        
        # Normalize headings
        lower_line = line.lower().rstrip(":")

        if lower_line in heading:
            line = heading[lower_line]

        # NLP----------------------------------
        else:
            resolved_heading = resolve_heading(lower_line,section_docs)

        if resolved_heading:
            line = resolved_heading
            
        #------------------------------------------ 
            
        normalized_lines.append(line)

    return "\n".join(normalized_lines)

# text="""EDUCATION
# Bachelor of Engineering in Chemical Engineering August 2016 - Present
# National Insititute of Technology,Warangal.
# CGPA upto 6th semister :6.70/10
# Intermediate Education August 2012 - May2014
# Narayana Junior College.
# Board Of Intermediate Education,A.P, Percentage: 96.8
# SSC, Class X March 2011 - March 2012
# St.Mary’s High school,Kankipadu,CGPA:9.5
# SKILLS
# Autocad Beginner
# C++ Intermediate
# Ms office Intermediate
# POSITION OF RESPONSIBILITY
# .Executive Member at Film Committee September 2017 -May 2018
# .Joint Secretary at Film Committee
# .Representing as Mess Representative at 2nd Mess.
# .Worked as SUBCORE in Publicity and Media relations,Technozion 20"""
# print(normalize_text(text))
# line = "· Joint Secretary at Film Committee"

# print(ord("·"))
# print(ord(line[0]))
# print(repr(line))



    