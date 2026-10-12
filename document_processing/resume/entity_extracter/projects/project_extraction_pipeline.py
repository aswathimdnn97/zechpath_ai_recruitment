from document_processing.resume.entity_extracter.projects.project_block_splitter import (
    split_project_blocks,
)

from document_processing.resume.entity_extracter.projects.project_name_extractor import (
    extract_project_name,
)

from document_processing.resume.entity_extracter.projects.project_description_extractor import (
    extract_project_description,
)

from document_processing.resume.entity_extracter.projects.project_technologies_extractor import (
    extract_project_technologies,
)

from document_processing.resume.entity_extracter.projects.project_technology_normalizer import (
    normalize_project_technologies,
)

from document_processing.resume.entity_extracter.projects.project_url_extractor import (
    extract_project_url,
)


def extract_projects(section):

    if not section:
        return []

    project_blocks = split_project_blocks(
        section
    )

    projects = []

    for block in project_blocks:

        project_name = extract_project_name(
            block
        )

        description = extract_project_description(
            block
        )

        raw_technologies = extract_project_technologies(
            block
        )

        technologies = normalize_project_technologies(
            raw_technologies
        )

        url = extract_project_url(
            block
        )

        project = {
            "project_name": project_name,
            "description": description,
            "technologies": technologies,
            "url": url,
        }

        projects.append(project)

    return projects