import re

from document_processing.resume.entity_extracter.certifications.certification_block_splitter import (
    split_certification_blocks,
    split_flat_certification_lines,
    is_certification_start,
)
from document_processing.resume.entity_extracter.certifications.certification_name_extractor import (
    extract_certification_name,
)
from document_processing.resume.entity_extracter.certifications.organization_extractor import (
    extract_issuing_organization,
)

from document_processing.resume.entity_extracter.certifications.certification_date_extraction import extract_certification_date
from document_processing.resume.entity_extracter.certifications.creditiel_id_extractor import extract_credential_id

def certification_pipeline(lines):

    blocks = split_certification_blocks(lines)

    # Some returned blocks may still contain multiple title/org pairs
    # (e.g., ['Title1', 'Org1', 'Title2', 'Org2']). Further split those
    # using the flat-line splitter heuristics.
    refined_blocks = []

    for block in blocks:
        # Count how many lines look like certification starts
        starts = sum(1 for l in block if is_certification_start(l))
        if starts > 1:
            refined_blocks.extend(split_flat_certification_lines(block))
        else:
            # If there are multiple organization-like lines in a block,
            # split by pairing each organization line with the preceding
            # title line. This handles cases like
            # ['TensorFlow Developer Certificate', 'TensorFlow (2022)',
            #  'Python for Data Science', 'IBM (2021)']
            org_hint = re.compile(r"\b(?:microsoft|google\s+cloud|coursera|deep\s*learning\.ai|tensorflow|ibm)\b", re.IGNORECASE)
            year_hint = re.compile(r"\b(?:19|20)\d{2}\b")

            org_indices = [i for i, l in enumerate(block) if org_hint.search(l) or year_hint.search(l)]

            if org_indices and len(org_indices) >= 1 and len(block) > 2:
                used = set()
                for idx in org_indices:
                    if idx == 0:
                        continue
                    if idx - 1 in used:
                        continue
                    # form a subblock from previous line to this org line
                    refined_blocks.append([block[idx - 1], block[idx]])
                    used.add(idx)
                    used.add(idx - 1)
                # add any remaining lines that weren't used as individual blocks
                leftovers = [block[i] for i in range(len(block)) if i not in used]
                if leftovers:
                    refined_blocks.append(leftovers)
            else:
                refined_blocks.append(block)

    blocks = refined_blocks

    certifications = []

    for block in blocks:

        name = extract_certification_name(block)
        org = extract_issuing_organization(block)

        # Skip blocks that don't contain a meaningful certification name.
        if not name or not any(c.isalpha() for c in name):
            continue
        
        # certification_date---------
        print("================================")
        print("BLOCK:", repr(block))


        date=extract_certification_date(block)
        issue_date = date["issue_date"]
        expiration_date = date["expiration_date"]

        creditie_id=extract_credential_id(block)
        
        
        certification = {
            "certification_name": name,
            "issuing_organization": org,
            "issue_date": issue_date,
            "expiration_date": expiration_date,
            "credential_id": creditie_id,
        }

        certifications.append(certification)

    return certifications