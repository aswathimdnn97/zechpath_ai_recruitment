"""
personal_attribute_masker.py

Responsibilities
----------------
1. Remove personal attributes from candidate profiles.
2. Remove personal information recursively.
3. Preserve job-relevant information.
4. Never modify the original candidate profile.
"""

import copy


# -------------------------------------------------------
# Personal Attributes
# -------------------------------------------------------

PERSONAL_ATTRIBUTE_KEYS = {
    # Identity
    "first_name",
    "last_name",
    "full_name",
    "name",

    # Contact information
    "email",
    "phone",
    "mobile",
    "telephone",

    # Social / personal profiles
    "linkedin",
    "linkedin_url",
    "github",
    "github_url",

    # Address / personal location
    "address",
    "home_address",
    "personal_address",

    # Personal information
    "date_of_birth",
    "dob",
    "gender",
    "age",
    "nationality",
    "marital_status",

    # Photos
    "photo",
    "profile_photo",

    # Entire personal information section
    "personal_information",
}


# -------------------------------------------------------
# Mask Personal Attributes
# -------------------------------------------------------

def mask_personal_attributes(profile):
    """
    Remove personal attributes from a candidate profile.

    The original profile is never modified.

    Parameters
    ----------
    profile : dict
        Candidate profile.

    Returns
    -------
    dict
        Masked candidate profile.
    """

    if not isinstance(profile, dict):
        raise TypeError(
            "profile must be a dictionary"
        )

    # ---------------------------------------------------
    # IMPORTANT:
    # Create a deep copy so the original profile
    # remains completely unchanged.
    # ---------------------------------------------------

    masked_profile = copy.deepcopy(profile)

    return _remove_personal_attributes(
        masked_profile
    )


# -------------------------------------------------------
# Recursive Attribute Removal
# -------------------------------------------------------

def _remove_personal_attributes(value):
    """
    Recursively remove personal attributes from
    dictionaries and lists.
    """

    # ---------------------------------------------------
    # Dictionary
    # ---------------------------------------------------

    if isinstance(value, dict):

        cleaned = {}

        for key, item in value.items():

            normalized_key = (
                str(key)
                .strip()
                .lower()
                .replace("-", "_")
                .replace(" ", "_")
            )

            # -------------------------------------------
            # Remove personal attribute completely
            # -------------------------------------------

            if normalized_key in PERSONAL_ATTRIBUTE_KEYS:
                continue

            # -------------------------------------------
            # Recursively clean nested values
            # -------------------------------------------

            cleaned[key] = _remove_personal_attributes(
                item
            )

        return cleaned

    # ---------------------------------------------------
    # List
    # ---------------------------------------------------

    if isinstance(value, list):

        return [
            _remove_personal_attributes(item)
            for item in value
        ]

    # ---------------------------------------------------
    # Primitive value
    # ---------------------------------------------------

    return value