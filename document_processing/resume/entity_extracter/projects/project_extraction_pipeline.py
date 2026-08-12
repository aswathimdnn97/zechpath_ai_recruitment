from document_processing.resume.entity_extracter.projects.project_block_splitter import split_project_blocks
from document_processing.resume.entity_extracter.projects.project_name_extractor import extract_project_name
from document_processing.resume.entity_extracter.projects.project_description_extractor import extract_project_description
from document_processing.resume.entity_extracter.projects.project_technologies_extractor import extract_project_technologies
from document_processing.resume.entity_extracter.projects.project_technology_normalizer import normalize_project_technologies
from document_processing.resume.entity_extracter.projects.project_url_extractor import extract_project_url


def extract_projects(section):
    blocks = split_project_blocks(section)
    
        
    if not section:
        return []

    # ========================================================
    # Step 1: Split into individual project blocks
    # ========================================================

    project_blocks = split_project_blocks(section)

    projects = []

    # ========================================================
    # Step 2: Process each project
    # ========================================================

    for block in project_blocks:

        # ----------------------------------------------------
        # Extract project name
        # ----------------------------------------------------

        project_name = extract_project_name(block)

        # ----------------------------------------------------
        # Extract description
        # ----------------------------------------------------

        description = extract_project_description(block)

        # ----------------------------------------------------
        # Extract raw technologies
        # ----------------------------------------------------

        raw_technologies = extract_project_technologies(block)

        # ----------------------------------------------------
        # Normalize technologies
        # ----------------------------------------------------

        technologies = normalize_project_technologies(
            raw_technologies
        )

        # ----------------------------------------------------
        # Extract URL
        # ----------------------------------------------------

        url = extract_project_url(block)

        # ----------------------------------------------------
        # Build project object
        # ----------------------------------------------------

        project = {
            "project_name": project_name,
            "description": description,
            "technologies": technologies,
            "url": url
        }

        projects.append(project)

    return projects