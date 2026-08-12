import re

def clean_skills(skills):
    """
    Clean skill entries by removing filler phrases and extracting core skill names.
    
    Args:
        skills: List of skill strings that may contain filler phrases
        
    Returns:
        List of cleaned skill strings
    """
    if not skills:
        return []
    
    # Patterns to remove (filler phrases)
    filler_patterns = [
        r'experience\s+with\s+',
        r'experience\s+in\s+',
        r'knowledge\s+of\s+',
        r'knowledge\s+in\s+',
        r'familiar\s+with\s+',
        r'expertise\s+in\s+',
        r'expertise\s+with\s+',
        r'understanding\s+of\s+',
        r'good\s+understanding\s+of\s+',
        r'unit\s+testing\s+using\s+',
        r'testing\s+using\s+',
        r'hands[\s-]*on\s+experience\s+with\s+',
        r'hands[\s-]*on\s+experience\s+in\s+',
        r'proficiency\s+in\s+',
        r'proficiency\s+with\s+',
    ]
    
    cleaned = []
    
    for skill in skills:
        if not skill or not isinstance(skill, str):
            continue
            
        cleaned_skill = skill.strip()
        
        # Remove filler phrases
        for pattern in filler_patterns:
            cleaned_skill = re.sub(pattern, '', cleaned_skill, flags=re.IGNORECASE)
        
        # Clean up whitespace and extra punctuation
        cleaned_skill = cleaned_skill.strip()
        cleaned_skill = re.sub(r'\s+', ' ', cleaned_skill)  # normalize spaces
        cleaned_skill = re.sub(r'^\W+|\W+$', '', cleaned_skill)  # remove leading/trailing punctuation
        
        # Only add if not empty and not a duplicate
        if cleaned_skill and cleaned_skill not in cleaned:
            cleaned.append(cleaned_skill)
    
    return cleaned
