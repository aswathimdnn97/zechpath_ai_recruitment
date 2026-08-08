"""
education_post_processor.py

Post-processing layer for extracted education records.

Responsibilities
----------------
1. Clean extracted education values.
2. Detect board names incorrectly extracted as fields.
3. Move board values into the `board` field.
4. Clean invalid field-of-study values.
5. Classify school records.
6. Merge university continuation records with degree records.
7. Prevent school records from being merged into degree records.
8. Preserve a consistent education schema.
"""

import re


# =========================================================
# CONSTANTS
# =========================================================

BOARD_KEYWORDS = [
    "central board of secondary education",
    "cbse",
    "state board",
    "board of secondary education",
    "icse",
    "isc",
]


SCHOOL_KEYWORDS = [
    "all india senior school certificate",
    "senior school certificate",
    "senior secondary",
    "higher secondary",
    "higher secondary certificate",
    "all india secondary school examination",
    "secondary school examination",
    "secondary examination",
    "secondary school",
    "class xii",
    "class 12",
    "12th",
    "class x",
    "class 10",
    "10th",
]


DEGREE_KEYWORDS = [
    "bachelor",
    "master",
    "b.e",
    "b.tech",
    "b.sc",
    "bca",
    "m.e",
    "m.tech",
    "m.sc",
    "mca",
    "mba",
    "phd",
    "doctor of philosophy",
    "diploma",
]


# =========================================================
# CLEAN VALUE
# =========================================================

def clean_education_value(value):
    """
    Clean one education value.

    Returns None for empty values.
    """

    if value is None:
        return None

    if not isinstance(value, str):
        return value

    # Replace non-breaking spaces
    value = value.replace("\xa0", " ")

    # Normalize whitespace
    value = re.sub(
        r"\s+",
        " ",
        value
    )

    # Remove leading/trailing whitespace
    value = value.strip()

    if not value:
        return None

    return value


# =========================================================
# BOARD DETECTION
# =========================================================

def extract_board_from_field(value):
    """
    Detect whether a field_of_study value is actually
    an education board.

    Example
    -------
    "Central Board of Secondary Education"
        -> same value

    "Computer Science"
        -> None
    """

    value = clean_education_value(
        value
    )

    if not value:
        return None

    lower_value = value.lower()

    for keyword in BOARD_KEYWORDS:

        if keyword in lower_value:
            return value

    return None


# =========================================================
# FIELD OF STUDY CLEANING
# =========================================================

def clean_field_of_study(value):
    """
    Remove values that are actually education boards.
    """

    value = clean_education_value(
        value
    )

    if not value:
        return None

    if extract_board_from_field(value):
        return None

    return value


# =========================================================
# DEGREE DETECTION
# =========================================================

def has_degree(record):
    """
    Determine whether a record represents a university/
    college degree.
    """

    if not record:
        return False

    degree_type = (
        record.get("degree_type")
        or ""
    )

    degree_type = degree_type.lower()

    if not degree_type:
        return False

    # School classifications are not university degrees.
    if degree_type in {
        "secondary",
        "higher secondary",
    }:
        return False

    return any(
        keyword in degree_type
        for keyword in DEGREE_KEYWORDS
    )


# =========================================================
# SCHOOL DETECTION
# =========================================================

def is_school_record(record):
    """
    Determine whether an education record represents
    school-level education.
    """

    if not record:
        return False

    degree_type = (
        record.get("degree_type")
        or ""
    ).lower()

    if degree_type in {
        "secondary",
        "higher secondary",
    }:
        return True

    institution = (
        record.get("institution")
        or ""
    ).lower()

    board = (
        record.get("board")
        or ""
    ).lower()

    field = (
        record.get("field_of_study")
        or ""
    ).lower()

    text = (
        f"{institution} "
        f"{board} "
        f"{field}"
    )

    return any(
        keyword in text
        for keyword in SCHOOL_KEYWORDS
    )


# =========================================================
# SCHOOL CLASSIFICATION
# =========================================================

def classify_school_record(record):
    """
    Classify an already-extracted school record.

    Returns
    -------
    dict
        Updated record.
    """

    if not record:
        return record

    record = record.copy()

    degree_type = (
        record.get("degree_type")
        or ""
    ).lower()

    # Already classified
    if degree_type in {
        "higher secondary",
        "secondary",
    }:
        return record

    institution = (
        record.get("institution")
        or ""
    ).lower()

    board = (
        record.get("board")
        or ""
    ).lower()

    field = (
        record.get("field_of_study")
        or ""
    ).lower()

    text = (
        f"{institution} "
        f"{board} "
        f"{field}"
    )

    # -----------------------------------------------------
    # Higher Secondary
    # -----------------------------------------------------

    higher_secondary_keywords = [
        "all india senior school certificate",
        "senior school certificate",
        "senior secondary",
        "higher secondary",
        "higher secondary certificate",
        "class xii",
        "class 12",
        "12th",
    ]

    if any(
        keyword in text
        for keyword in higher_secondary_keywords
    ):
        record["degree_type"] = (
            "Higher Secondary"
        )

        return record

    # -----------------------------------------------------
    # Secondary
    # -----------------------------------------------------

    secondary_keywords = [
        "all india secondary school examination",
        "secondary school examination",
        "secondary examination",
        "secondary school",
        "class x",
        "class 10",
        "10th",
    ]

    if any(
        keyword in text
        for keyword in secondary_keywords
    ):
        record["degree_type"] = (
            "Secondary"
        )

        return record

    return record


# =========================================================
# NORMALIZE ONE RECORD
# =========================================================

def normalize_education_record(record):
    """
    Normalize one education record.

    Returns None for invalid records.
    """

    if not record:
        return None

    if not isinstance(
        record,
        dict
    ):
        return None

    record = record.copy()

    # -----------------------------------------------------
    # Clean all values
    # -----------------------------------------------------

    for key in record:

        record[key] = (
            clean_education_value(
                record[key]
            )
        )

    # -----------------------------------------------------
    # Move board accidentally extracted as field
    # -----------------------------------------------------

    field_value = (
        record.get("field_of_study")
    )

    board_from_field = (
        extract_board_from_field(
            field_value
        )
    )

    if (
        not record.get("board")
        and board_from_field
    ):
        record["board"] = (
            board_from_field
        )

    # -----------------------------------------------------
    # Clean field of study
    # -----------------------------------------------------

    record["field_of_study"] = (
        clean_field_of_study(
            field_value
        )
    )

    # -----------------------------------------------------
    # School classification
    # -----------------------------------------------------

    if is_school_record(record):

        record = classify_school_record(
            record
        )

        if record is None:
            return None

        # Schools do not have universities.
        record["university"] = None

    # -----------------------------------------------------
    # Consistent schema
    # -----------------------------------------------------

    record.setdefault(
        "degree_type",
        None
    )

    record.setdefault(
        "field_of_study",
        None
    )

    record.setdefault(
        "institution",
        None
    )

    record.setdefault(
        "university",
        None
    )

    record.setdefault(
        "board",
        None
    )

    record.setdefault(
        "graduation_year",
        None
    )

    return record


# =========================================================
# MERGE DEGREE RECORDS
# =========================================================

def merge_degree_records(education):
    """
    Merge fragmented degree records.

    Example
    -------

    Record 1:
        Bachelor of Engineering
        PES Institute

    Record 2:
        Visvesvaraya Technological University
        Computer Science

    Result:
        Bachelor of Engineering
        PES Institute
        Visvesvaraya Technological University
        Computer Science

    School records are never merged into degrees.
    """

    if not education:
        return []

    merged = []

    i = 0

    while i < len(education):

        current = education[i]

        if not current:
            i += 1
            continue

        current = current.copy()

        # -------------------------------------------------
        # Degree record
        # -------------------------------------------------

        if has_degree(current):

            if i + 1 < len(education):

                next_record = (
                    education[i + 1]
                )

                if next_record:

                    next_record = (
                        next_record.copy()
                    )

                    # -----------------------------------------
                    # Do not merge school records
                    # -----------------------------------------

                    if (
                        not has_degree(
                            next_record
                        )
                        and not is_school_record(
                            next_record
                        )
                    ):

                        # -------------------------------------
                        # Field of study
                        # -------------------------------------

                        if (
                            not current.get(
                                "field_of_study"
                            )
                            and next_record.get(
                                "field_of_study"
                            )
                        ):
                            current[
                                "field_of_study"
                            ] = (
                                next_record[
                                    "field_of_study"
                                ]
                            )

                        # -------------------------------------
                        # University
                        # -------------------------------------

                        next_institution = (
                            next_record.get(
                                "institution"
                            )
                        )

                        if (
                            next_institution
                            and current.get(
                                "institution"
                            )
                        ):
                            current[
                                "university"
                            ] = (
                                next_institution
                            )

                        # -------------------------------------
                        # Graduation year
                        # -------------------------------------

                        if (
                            not current.get(
                                "graduation_year"
                            )
                            and next_record.get(
                                "graduation_year"
                            )
                        ):
                            current[
                                "graduation_year"
                            ] = (
                                next_record[
                                    "graduation_year"
                                ]
                            )

                        # -------------------------------------
                        # Board
                        # -------------------------------------

                        if (
                            not current.get(
                                "board"
                            )
                            and next_record.get(
                                "board"
                            )
                        ):
                            current[
                                "board"
                            ] = (
                                next_record[
                                    "board"
                                ]
                            )

                        # Continuation consumed
                        i += 1

            merged.append(current)

        else:

            # -------------------------------------------------
            # Standalone school / other record
            # -------------------------------------------------

            merged.append(current)

        i += 1

    return merged


# =========================================================
# FINAL POST PROCESSOR
# =========================================================

def post_process_education(education):
    """
    Main education post-processing pipeline.

    Steps
    -----
    1. Normalize records.
    2. Remove invalid records.
    3. Merge university continuation records.
    4. Normalize merged records.
    5. Return final structured education.
    """

    if not education:
        return []

    # -----------------------------------------------------
    # First normalization
    # -----------------------------------------------------

    normalized = []

    for record in education:

        cleaned = (
            normalize_education_record(
                record
            )
        )

        if cleaned is not None:
            normalized.append(
                cleaned
            )

    # -----------------------------------------------------
    # Merge degree records
    # -----------------------------------------------------

    merged = merge_degree_records(
        normalized
    )

    # -----------------------------------------------------
    # Final normalization
    # -----------------------------------------------------

    final = []

    for record in merged:

        cleaned = (
            normalize_education_record(
                record
            )
        )

        if cleaned is None:
            continue

        final.append(
            cleaned
        )

    return final

