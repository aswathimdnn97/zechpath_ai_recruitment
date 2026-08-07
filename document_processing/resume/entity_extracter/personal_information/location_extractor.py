def extract_location(text):

    lines = text.splitlines()

    for line in lines[:10]:

        if "," in line:

            return line.strip()

    return None