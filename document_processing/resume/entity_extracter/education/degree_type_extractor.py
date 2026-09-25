"""
degree_type_extractor.py

Responsibilities
----------------
1. Extract degree type from an education block.
2. Support full degree names and common abbreviations.
3. Support punctuation variations such as B.Com, B.Com., BCom.
4. Return the extracted degree exactly as it appears in the resume.
"""

import re


# =========================================================
# DEGREE PATTERNS
# =========================================================

DEGREE_PATTERNS = [

    # -----------------------------------------------------
    # FULL DEGREE NAMES
    # -----------------------------------------------------

    r"\bBachelor\s+of\s+Technology\b",
    r"\bBachelor\s+of\s+Engineering\b",
    r"\bBachelor\s+of\s+Science\b",
    r"\bBachelor\s+of\s+Arts\b",
    r"\bBachelor\s+of\s+Commerce\b",
    r"\bBachelor\s+of\s+Computer\s+Applications\b",
    r"\bBachelor\s+of\s+Business\s+Administration\b",
    r"\bBachelor\s+of\s+Management\s+Studies\b",
    r"\bBachelor\s+of\s+Pharmacy\b",
    r"\bBachelor\s+of\s+Architecture\b",
    r"\bBachelor\s+of\s+Design\b",
    r"\bBachelor\s+of\s+Fine\s+Arts\b",
    r"\bBachelor\s+of\s+Laws\b",
    r"\bBachelor\s+of\s+Social\s+Work\b",
    r"\bBachelor\s+of\s+Library\s+and\s+Information\s+Science\b",
    r"\bBachelor\s+of\s+Hotel\s+Management\b",
    r"\bBachelor\s+of\s+Physiotherapy\b",
    r"\bBachelor\s+of\s+Dental\s+Surgery\b",
    r"\bBachelor\s+of\s+Human\s+Resource\s+Management\b",
    r"\bBachelor\s+of\s+Journalism\s+and\s+Mass\s+Communication\b",
    r"\bBachelor\s+of\s+Travel\s+and\s+Tourism\s+Management\b",

    # -----------------------------------------------------
    # MASTER DEGREE NAMES
    # -----------------------------------------------------

    r"\bMaster\s+of\s+Technology\b",
    r"\bMaster\s+of\s+Engineering\b",
    r"\bMaster\s+of\s+Science\b",
    r"\bMaster\s+of\s+Arts\b",
    r"\bMaster\s+of\s+Commerce\b",
    r"\bMaster\s+of\s+Computer\s+Applications\b",
    r"\bMaster\s+of\s+Business\s+Administration\b",
    r"\bMaster\s+of\s+Pharmacy\b",

    # -----------------------------------------------------
    # DOCTORATE
    # -----------------------------------------------------

    r"\bDoctor\s+of\s+Philosophy\b",

    # -----------------------------------------------------
    # BACHELOR ABBREVIATIONS
    # -----------------------------------------------------

    # B.Tech / BTech
    r"\bB\.?\s*Tech\.?\b",

    # B.E / BE
    r"\bB\.?\s*E\.?\b",

    # B.Sc / BSc
    r"\bB\.?\s*Sc\.?\b",

    # B.A / BA
    r"\bB\.?\s*A\.?\b",

    # B.Com / BCom
    r"\bB\.?\s*Com\.?\b",

    # BCA
    r"\bB\.?\s*C\.?\s*A\.?\b",

    # BBA
    r"\bB\.?\s*B\.?\s*A\.?\b",

    # BMS
    r"\bB\.?\s*M\.?\s*S\.?\b",

    # B.Pharm / BPharm
    r"\bB\.?\s*Pharm\.?\b",

    # B.Arch / BArch
    r"\bB\.?\s*Arch\.?\b",

    # B.Des / BDes
    r"\bB\.?\s*Des\.?\b",

    # BFA
    r"\bB\.?\s*F\.?\s*A\.?\b",

    # LLB
    r"\bL\.?\s*L\.?\s*B\.?\b",

    # BSW
    r"\bB\.?\s*S\.?\s*W\.?\b",

    # BLIS
    r"\bB\.?\s*L\.?\s*I\.?\s*S\.?\b",

    # BHM
    r"\bB\.?\s*H\.?\s*M\.?\b",

    # BJMC
    r"\bB\.?\s*J\.?\s*M\.?\s*C\.?\b",

    # BPT
    r"\bB\.?\s*P\.?\s*T\.?\b",

    # BDS
    r"\bB\.?\s*D\.?\s*S\.?\b",

    # MBBS
    r"\bM\.?\s*B\.?\s*B\.?\s*S\.?\b",

    # BHRM
    r"\bB\.?\s*H\.?\s*R\.?\s*M\.?\b",

    # BTTM
    r"\bB\.?\s*T\.?\s*T\.?\s*M\.?\b",

    # -----------------------------------------------------
    # MASTER ABBREVIATIONS
    # -----------------------------------------------------

    # M.Tech / MTech
    r"\bM\.?\s*Tech\.?\b",

    # M.E / ME
    r"\bM\.?\s*E\.?\b",

    # M.Sc / MSc
    r"\bM\.?\s*Sc\.?\b",

    # M.A / MA
    r"\bM\.?\s*A\.?\b",

    # M.Com / MCom
    r"\bM\.?\s*Com\.?\b",

    # MCA
    r"\bM\.?\s*C\.?\s*A\.?\b",

    # MBA
    r"\bM\.?\s*B\.?\s*A\.?\b",

    # M.Pharm
    r"\bM\.?\s*Pharm\.?\b",

    # -----------------------------------------------------
    # PhD
    # -----------------------------------------------------

    r"\bPh\.?\s*D\.?\b",

    # -----------------------------------------------------
    # OTHER QUALIFICATIONS
    # -----------------------------------------------------

    r"\bAssociate(?:'s)?\s+Degree\b",
    r"\bAssociate\b",
    r"\bDiploma\b",
]


# =========================================================
# EXTRACT DEGREE TYPE
# =========================================================

def extract_degree_type(education_block):
    """
    Extract degree type from an education block.

    Parameters
    ----------
    education_block : list[str] | str

    Returns
    -------
    str | None
        Extracted degree exactly as found in the text.
    """

    if not education_block:
        return None

    # -----------------------------------------------------
    # Handle string input
    # -----------------------------------------------------

    if isinstance(education_block, str):
        text = education_block

    # -----------------------------------------------------
    # Handle list input
    # -----------------------------------------------------

    elif isinstance(education_block, list):

        # Flatten nested list
        if (
            education_block
            and isinstance(
                education_block[0],
                list
            )
        ):
            flattened = []

            for item in education_block:
                if isinstance(item, list):
                    flattened.extend(item)
                else:
                    flattened.append(item)

            education_block = flattened

        text = " ".join(
            str(line)
            for line in education_block
            if line
        )

    else:
        return None

    # -----------------------------------------------------
    # Normalize whitespace
    # -----------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    if not text:
        return None

    # -----------------------------------------------------
    # Search degree patterns
    # -----------------------------------------------------

    for pattern in DEGREE_PATTERNS:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        if match:
            return match.group().strip()

    return None


# =========================================================
# TESTING
# =========================================================

if __name__ == "__main__":

    test_cases = [

        [
            "Bachelor of Technology in Computer Science",
            "APJ Abdul Kalam Technological University",
            "2019 - 2023"
        ],

        [
            "B.Com - Finance 2025",
            "Finance"
        ],

        [
            "B.Com. Finance 2025"
        ],

        [
            "BCom Finance 2025"
        ],

        [
            "Bachelor of Commerce - Finance"
        ],

        [
            "B.Tech Computer Science 2024"
        ],

        [
            "BSc Computer Science 2023"
        ],

        [
            "MBA Human Resources 2025"
        ],

        [
            "MCA Computer Applications 2024"
        ],

        [
            "Ph.D. Computer Science"
        ],
    ]

    for education in test_cases:

        result = extract_degree_type(
            education
        )

        print(
            f"{education[0]}  -->  {result}"
        )