"""
experience_calculator.py

Responsibilities
-----------------
1. Calculate total experience duration.
2. Convert dates into months.
3. Handle Present/current jobs.
"""

from datetime import datetime
import re


# ----------------------------------------------------
# Month Mapping
# ----------------------------------------------------

MONTHS = {

    "jan": 1,
    "january": 1,

    "feb": 2,
    "february": 2,

    "mar": 3,
    "march": 3,

    "apr": 4,
    "april": 4,

    "may": 5,

    "jun": 6,
    "june": 6,

    "jul": 7,
    "july": 7,

    "aug": 8,
    "august": 8,

    "sep": 9,
    "september": 9,

    "oct": 10,
    "october": 10,

    "nov": 11,
    "november": 11,

    "dec": 12,
    "december": 12
}



# ----------------------------------------------------
# Parse Date
# ----------------------------------------------------

def parse_date(date_text):

    """
    Converts:

    June 2020

    into:

    (2020,6)
    """

    if not date_text:

        return None



    date_text = date_text.lower()



    year_match = re.search(
        r"\d{4}",
        date_text
    )


    if not year_match:

        return None



    year = int(
        year_match.group()
    )



    month = 1


    for name, number in MONTHS.items():

        if name in date_text:

            month = number

            break



    return year, month



# ----------------------------------------------------
# Calculate Experience
# ----------------------------------------------------

def calculate_experience(duration):


    if not duration:

        return {

            "total_months": 0,

            "total_years": 0

        }



    start_date = parse_date(
        duration.get(
            "start_date"
        )
    )


    end_text = duration.get(
        "end_date"
    )



    # Current job

    if (
        end_text
        and
        end_text.lower()
        in [
            "present",
            "current",
            "now"
        ]
    ):

        end_date = (
            datetime.now().year,
            datetime.now().month
        )

    else:

        end_date = parse_date(
            end_text
        )



    if not start_date or not end_date:

        return {

            "total_months": None,

            "total_years": None

        }



    start_year, start_month = start_date

    end_year, end_month = end_date



    total_months = (

        (end_year - start_year)
        *
        12

        +

        (end_month - start_month)

    )



    # include current month

    total_months += 1



    return {

        "total_months":
            total_months,

        "total_years":
            round(
                total_months / 12,
                1
            )

    }