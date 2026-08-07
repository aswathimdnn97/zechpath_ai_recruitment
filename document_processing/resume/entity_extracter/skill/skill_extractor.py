import re

def extract_skill(skill_section):
    
    if not skill_section:
        return []
    
    # skill section returning list of another list so flatten
    if isinstance(skill_section,list):
       skill_section=skill_section[0]
    
    candidate_skill=[]
    
    for skill in skill_section:

        if(skill):
            candidate_skill.append(skill)
            
    return list(dict.fromkeys(candidate_skill)) 