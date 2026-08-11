 
def extract_entities(sections):

    entities = {}

    entities["job_title"] = " ".join(sections.get("job_title", []))
    
    entities["company"] = " ".join(sections.get("company", []))
    
    entities["job_summary"] = " ".join(sections.get("job_summary", []))
    
    entities["location"] = " ".join(sections.get("location", []))
    
    entities["employment_type"] = " ".join(sections.get("employment_type", []))
    
    entities["salary"] = " ".join(sections.get("salary", []))
    
    entities["availability"] = " ".join(sections.get("availability", []))
    
    entities["responsibilities"] = sections.get("responsibilities", [])
    
    entities["required_skills"] = sections.get("required_skills", [])
    
    entities["preferred_skills"] = sections.get("preferred_skills", [])
    
    entities["education"] = sections.get("education", [])
    
    entities["soft_skills"] = sections.get("soft_skills", [])

    # Experience (keep as string if only one value)
    experience = sections.get("experience", [])
    entities["experience"] = sections.get("experience", [])
    entities["requirements"]=sections.get("requirements",[])

    return entities