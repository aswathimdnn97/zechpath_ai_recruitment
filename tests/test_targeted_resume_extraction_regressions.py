from document_processing.resume.entity_extracter.certifications.certification_pipeline import (
    certification_pipeline,
)
from document_processing.resume.entity_extracter.experience.experince_block_splitter import (
    split_experience_blocks,
)
from document_processing.resume.entity_extracter.experience.experinece_pipeline import (
    experience_extractor,
)
from document_processing.resume.entity_extracter.skill.skill_extractor import (
    extract_skill,
)
from document_processing.resume.headings import headings
from document_processing.resume.resume_normalizer import normalize_text
from document_processing.resume.section_detector import detect_sections


def test_training_records_with_pipe_and_dates_are_split_into_certifications():
    lines = [[
        "Java With SpringBoot | ROGERSOFT Technology Private Limited",
        "May 2022 - July 2022",
        "Python Full-Stack Development | ROGERSOFT Technology Private Limited",
        "May 2026 - Present",
    ]]

    certifications = certification_pipeline(lines)

    assert [
        (
            item["certification_name"],
            item["issuing_organization"],
            item["issue_date"],
            item["expiration_date"],
        )
        for item in certifications
    ] == [
        (
            "Java With SpringBoot",
            "ROGERSOFT Technology Private Limited",
            "May 2022",
            "July 2022",
        ),
        (
            "Python Full-Stack Development",
            "ROGERSOFT Technology Private Limited",
            "May 2026",
            "Present",
        ),
    ]


def test_year_range_and_hr_assistant_title_start_a_new_experience():
    text = (
        "EMPLOYMENT HISTORY\n"
        "HR Executive - TalentBridge Solutions\n"
        "Jan 2021 - Present\n"
        "Chennai, Tamil Nadu\n"
        "Coordinated recruitment and interview scheduling.\n"
        "HR Assistant - OfficePeople\n"
        "2019 - 2020\n"
        "Chennai, Tamil Nadu\n"
        "Maintained employee documentation."
    )

    sections = detect_sections(normalize_text(text), headings)
    experience_lines = sections["experience"]

    assert any(
        line == "2019 - 2020"
        for block in experience_lines
        for line in block
    )

    blocks = split_experience_blocks(experience_lines)

    assert len(blocks) == 2
    assert "HR Executive - TalentBridge Solutions" in blocks[0]
    assert "HR Assistant - OfficePeople" in blocks[1]
    assert "2019 - 2020" in blocks[1]

    experiences = experience_extractor(experience_lines)

    assert len(experiences) == 2
    assert [
        (
            item["title"]["title"],
            item["company"]["company"],
            item["duration"]["start_date"],
            item["duration"]["end_date"],
        )
        for item in experiences
    ] == [
        ("HR Executive", "TalentBridge Solutions", "Jan 2021", "Present"),
        ("HR Assistant", "OfficePeople", "2019", "2020"),
    ]


def test_evaluation_banner_is_not_extracted_as_a_candidate_skill():
    text = (
        "Zechpath ATS Evaluation Resume - RES_EVAL_011 - Fictional test data\n"
        "SUMMARY\n"
        "HR professional experienced in talent acquisition and HR operations.\n"
        "SKILLS\n"
        "Talent Acquisition\n"
        "HR Operations"
    )

    sections = detect_sections(normalize_text(text), headings)
    skills = {
        item["skill"]
        for item in extract_skill(sections)
    }

    assert "Talent Acquisition" in skills
    assert "HR Operations" in skills
    assert "Applicant Tracking System" not in skills


def test_single_character_fragment_does_not_fuzzy_match_angular():
    skills = {
        item["skill"]
        for item in extract_skill({"skills": [["l"]]})
    }

    assert "Angular" not in skills


def test_explicit_angular_skill_is_still_extracted():
    skills = {
        item["skill"]
        for item in extract_skill({"skills": [["Angular"]]})
    }

    assert "Angular" in skills
