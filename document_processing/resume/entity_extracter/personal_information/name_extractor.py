import re


def extract_name(text):

    lines = text.splitlines()

    for line in lines[:5]:

        line = line.strip()

        if not line:
            continue

        if "@" in line:
            continue

        if re.search(r"\d", line):
            continue

        words = line.split()

        if 2 <= len(words) <= 4:

            return line

    return None