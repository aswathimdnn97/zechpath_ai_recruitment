"""
experience_block_splitter.py

Responsibilities
----------------
1. Split the experience section into individual experience blocks.
2. Detect the beginning of each experience.
3. Preserve all lines belonging to the experience.
"""

import re


# ----------------------------------------------------
# Detect Experience Header
# ----------------------------------------------------

def is_new_experience(line):
    """
    Detects the first line of a new experience.

    Examples
    --------
    Software Engineer                  Jan 2022 - Present
    Python Developer                   June 2021 - Aug 2023
    Undergraduate Research Assistant   May 2020 - Present
    """

    line = line.strip()

    pattern = (
        r".+?"
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r".*?"
        r"\d{4}"
    )

    return bool(
        re.search(
            pattern,
            line,
            flags=re.IGNORECASE
        )
    )


# ----------------------------------------------------
# Split Experience Blocks
# ----------------------------------------------------

def split_experience_blocks(experience_section):
    """
    Parameters
    ----------
    experience_section : list

    Returns
    -------
    list[list[str]]
    """

    if not experience_section:
        return []

    # Flatten one level if required
    if (
        isinstance(experience_section, list)
        and experience_section
        and isinstance(experience_section[0], list)
    ):
        experience_section = experience_section[0]

    blocks = []

    current_block = []

    for line in experience_section:

        line = line.strip()

        if not line:
            continue

        # Start of a new experience
        if is_new_experience(line):

            if current_block:
                blocks.append(current_block)

            current_block = [line]

        else:

            current_block.append(line)

    if current_block:
        blocks.append(current_block)

    return blocks


# ----------------------------------------------------
# Testing
# ----------------------------------------------------

if __name__ == "__main__":

    sample = [

        "Undergraduate Research Assistant June 2020 - Present",
        "Texas A&M University College Station, TX",
        "Developed REST APIs",

        "Information Technology Support Specialist Sep. 2018 - Present",
        "Southwestern University Georgetown, TX",
        "Maintained printers",

        "Artificial Intelligence Research Assistant May 2019 - July 2019",
        "Southwestern University Georgetown, TX",
        "Developed Java game"

    ]

    from pprint import pprint

    pprint(split_experience_blocks(sample))