from document_processing.resume.entity_extracter.experience.company_extractor import (
    extract_companies,
)

from document_processing.resume.entity_extracter.experience.title_extractor import (
    remove_date,
)

test_cases = {
    "Software Engineer Jan 2022 - Present": "Software Engineer",
    "Python Developer 2021–2023": "Python Developer",
    "QA Tester Feb 2020 to Dec 2022": "QA Tester",
    "Data Scientist": "Data Scientist",
}

for source, expected in test_cases.items():
    actual = remove_date(source)
    status = "PASS" if actual == expected else "FAIL"

    print(f"{status}: {source!r} -> {actual!r}")

    assert actual == expected, (
        f"Expected {expected!r}, received {actual!r}"
    )


def test_extracts_unsuffixed_company_after_experience_title():
    experience_blocks = [
        [
            "Apr 2021 - Present",
            "Senior HR Executive",
            "PeopleSphere",
            "Bengaluru, Karnataka",
            "Managed end-to-end recruitment, interview coordination and onboarding.",
        ],
        [
            "Jun 2019 - Mar 2021",
            "HR Executive",
            "TalentWorks",
            "Bengaluru, Karnataka",
            "Handled HRMS updates, employee records and recruitment coordination.",
        ],
        [
            "Jul 2018 - May 2019",
            "HR Assistant",
            "CoreStaff",
            "Bengaluru, Karnataka",
            "Supported interview scheduling and HR documentation.",
        ],
    ]

    assert [
        extract_companies(block)
        for block in experience_blocks
    ] == [
        ["PeopleSphere"],
        ["TalentWorks"],
        ["CoreStaff"],
    ]


def test_does_not_extract_a_title_or_description_as_company():
    experience_block = [
        "Jul 2018 - May 2019",
        "HR Assistant",
        "Supported interview scheduling and HR documentation.",
    ]

    assert extract_companies(experience_block) == []
