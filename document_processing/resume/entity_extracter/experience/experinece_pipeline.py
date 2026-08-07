"""
experience_pipeline.py

Combines all experience extraction modules
and creates structured experience data.
"""


from document_processing.resume.entity_extracter.experience.experince_block_splitter import (
    split_experience_blocks
)


from document_processing.resume.entity_extracter.experience.title_extractor import (
    extract_titles
)

from document_processing.resume.entity_extracter.experience.title_alases_resolver import (
    resolve_title_alias
)

from document_processing.resume.entity_extracter.experience.title_validator import (
    validate_title
)



from document_processing.resume.entity_extracter.experience.company_extractor import (
    extract_companies
)

from document_processing.resume.entity_extracter.experience.company_alias_resolver import (
    resolve_company_aliases
)

from document_processing.resume.entity_extracter.experience.company_validator import (
    validate_companies
)



from document_processing.resume.entity_extracter.experience.duration_calculator import (
    extract_duration
)


from document_processing.resume.entity_extracter.experience.description_extraction import (
    extract_description
)


from document_processing.resume.entity_extracter.experience.location_extractor import (
    extract_location
)


from document_processing.resume.entity_extracter.experience.employement_type import (
    extract_employment_type
)


from document_processing.resume.entity_extracter.experience.department_extractor import (
    extract_department
)


from document_processing.resume.entity_extracter.experience.skill_extractor_from_experience import (
    extract_skills_from_experience
)

from document_processing.resume.entity_extracter.experience.experience_calculator import (
    calculate_experience
)



# ----------------------------------------------------
# Experience Extractor
# ----------------------------------------------------

def experience_extractor(experience_section):


    if not experience_section:

        return []



    # Split experience into blocks

    experience_blocks = split_experience_blocks(
        experience_section
    )


    experiences = []



    for block in experience_blocks:



        # ----------------------------
        # Title
        # ----------------------------

        titles = extract_titles(
            block
        )


        raw_title = (
            titles[0]
            if titles
            else None
        )


        resolved_title = (
            resolve_title_alias(
                raw_title
            )
            if raw_title
            else None
        )


        title = validate_title(
            resolved_title
        )



        # ----------------------------
        # Company
        # ----------------------------

        companies = extract_companies(
            block
        )


        resolved_companies = (
            resolve_company_aliases(
                companies
            )
        )


        company = validate_companies(
            resolved_companies
        )


        # take first company

        company = (
            company[0]
            if company
            else None
        )



        # ----------------------------
        # Duration
        # ----------------------------

        duration = extract_duration(
            block
        )


        total_experience = (
            calculate_experience(
                duration
            )
        )



        # ----------------------------
        # Description
        # ----------------------------

        description = extract_description(
            block
        )



        # ----------------------------
        # Location
        # ----------------------------

        location = extract_location(
            block
        )



        # ----------------------------
        # Employment Type
        # ----------------------------

        employment_type = (
            extract_employment_type(
                block
            )
        )



        # ----------------------------
        # Department
        # ----------------------------

        department = (
            extract_department(
                block
            )
        )



        # ----------------------------
        # Skills
        # ----------------------------

        skills = (
            extract_skills_from_experience(
                block
            )
        )



        # ----------------------------
        # Final Object
        # ----------------------------

        experiences.append({

            "title": title,

            "company": company,

            "duration": duration,

            "total_experience": total_experience,

            "location": location,

            "employment_type": employment_type,

            "department": department,

            "skills": skills,

            "description": description

        })


    return experiences