import re

def normalize_jd(text):
    headings = {
    "job title": "job_title",
    "position": "job_title",
    "role": "job_title",

    "company": "company",

    "location": "location",

    "job summary": "job_summary",
    "job overview": "job_summary",
    "job description": "job_summary",
    "overview": "job_summary",

    "responsibilities": "responsibilities",
    "key responsibilities": "responsibilities",
    "roles and responsibilities": "responsibilities",

    "required skills": "required_skills",
    "skills required": "required_skills",
    "technical skills": "required_skills",
    "mandatory skills": "required_skills",

    "preferred skills": "preferred_skills",
    "good to have": "preferred_skills",
    "nice to have": "preferred_skills",

    "experience": "experience",
    "experience required": "experience",
    "required experience": "experience",
    "years of experience": "experience",
    "experience requirements":"experience",

    "education": "education",
    "qualifications": "education",
    "education qualification": "education",

    "employment type": "employment_type",
    "job type": "employment_type",

    "soft skills": "soft_skills",

    "salary": "salary",

    "notice period": "availability",

    "requirements": "requirements",
}
        
#  Process line-by-line
    # 3. Process line-by-line
    lines = text.split("\n")
    normalized_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Normalize bullet points
        line = re.sub(r"^[•●◦▪■*-]\s*", "", line)
        
        if ":" in line:

            parts = line.split(":", 1)

            heading = parts[0].strip().lower()

            if heading in headings:

                normalized_lines.append(headings[heading])

                if parts[1].strip():
                    normalized_lines.append(parts[1].strip())

                continue
        
        # remove : only if at the end of the heading
        line=re.sub(r"\s*:\s*$","",line)
        lower_line = line.lower()

        if lower_line in headings:
            line = headings[lower_line]

        normalized_lines.append(line)

    return "\n".join(normalized_lines)
        
        