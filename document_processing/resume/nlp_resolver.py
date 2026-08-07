import spacy
from document_processing.resume.headings import headings

# Load spaCy model once
nlp = spacy.load("en_core_web_md")
print(nlp.meta["name"])
print(nlp.vocab.vectors_length)

def build_section_docs(section_names):
    """
    Create spaCy Doc objects for all normalized section names.
    """
    return {
        section: nlp(section)
        for section in section_names
    }


def resolve_heading(heading, section_docs, threshold=0.75):
    """
    Try to resolve an unknown heading to the closest
    normalized section name.
    """

    heading_doc = nlp(heading.lower())

    best_section = None
    best_score = 0

    for section, section_doc in section_docs.items():

        score = heading_doc.similarity(section_doc)

        if score > best_score:
            best_score = score
            best_section = section

    if best_score >= threshold:
        return best_section

    return None