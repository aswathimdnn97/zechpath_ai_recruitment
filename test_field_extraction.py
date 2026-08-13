"""Test field extraction directly"""

import re

line = 'B.Tech in Computer Science and Engineering ΓÇö Visvesvaraya Technological University | 2017 ΓÇô 2021'
lower_line = line.lower()

print(f"Line: {line}")
print(f"Lower: {lower_line}")
print(f"Has ' in ': {' in ' in lower_line}")

if " in " in lower_line:
    # Split on " in " to extract the field part
    parts = re.split(r"\s+in\s+", line, flags=re.IGNORECASE)
    print(f"Parts after split by ' in ': {parts}")
    
    if len(parts) > 1:
        # The part after "in" might contain field of study
        field_candidate = parts[1]
        print(f"Field candidate (before dash split): {field_candidate}")
        
        # Remove everything from dash onwards
        field_candidate = re.split(r"[\s—–\-ΓÇö~|]+", field_candidate)[0]
        print(f"Field candidate (after dash split): {field_candidate}")
        
        field_candidate = field_candidate.strip()
        print(f"Field candidate (after strip): {field_candidate}")
        
        # Check if this looks like a field of study
        FIELD_KEYWORDS = [
            "computer science",
            "computer applications",
            "information technology",
        ]
        
        if field_candidate:
            for keyword in FIELD_KEYWORDS:
                print(f"Checking if '{keyword.lower()}' in '{field_candidate.lower()}': {keyword.lower() in field_candidate.lower()}")
                if keyword.lower() in field_candidate.lower():
                    print(f"MATCH: {field_candidate}")
                    break
