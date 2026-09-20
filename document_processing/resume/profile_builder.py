def merge_skills(section_skills, experience_records):
    result = []
    seen = set()

    for skill in section_skills or []:
        value = skill.get("skill") if isinstance(skill, dict) else str(skill)
        key = value.strip().lower()

        if key and key not in seen:
            result.append(skill)
            seen.add(key)

    for experience in experience_records or []:
        for skill in experience.get("skills", []):
            value = skill.get("skill") if isinstance(skill, dict) else str(skill)
            key = value.strip().lower()

            if key and key not in seen:
                result.append(skill)
                seen.add(key)

    return result


def enrich_profile_skills(profile=None, parsed_sections=None):
    profile = profile or {}
    parsed_sections = parsed_sections or {}

    profile["skills"] = merge_skills(
        parsed_sections.get("skills", []),
        profile.get("experience", []),
    )
    return profile
