from document_processing.resume.entity_extracter.skill import (
    skill_list_splitter,
)


def test_whitespace_skills_build_phrase_index_once(monkeypatch):
    monkeypatch.setattr(
        skill_list_splitter,
        "_load_master_skills",
        lambda: [
            "Java",
            "JavaScript",
            "Java Spring Boot",
            "Python",
            "SQL",
        ],
    )
    monkeypatch.setattr(
        skill_list_splitter,
        "_load_aliases",
        lambda: {},
    )

    build_phrase_index = (
        skill_list_splitter._build_known_skill_phrases
    )
    build_count = 0

    def count_phrase_index_builds(master_skills, aliases):
        nonlocal build_count
        build_count += 1
        return build_phrase_index(master_skills, aliases)

    monkeypatch.setattr(
        skill_list_splitter,
        "_build_known_skill_phrases",
        count_phrase_index_builds,
    )

    skills = skill_list_splitter.split_skill_line(
        [
            "Java Spring Boot Python",
            "JavaScript SQL",
        ]
    )

    assert skills == [
        "java spring boot",
        "python",
        "javascript",
        "sql",
    ]
    assert build_count == 1


def test_explicitly_separated_skills_skip_phrase_index(monkeypatch):
    monkeypatch.setattr(
        skill_list_splitter,
        "_load_master_skills",
        lambda: ["Python", "JavaScript"],
    )
    monkeypatch.setattr(
        skill_list_splitter,
        "_load_aliases",
        lambda: {},
    )

    def fail_if_built(master_skills, aliases):
        raise AssertionError(
            "Phrase matching is unnecessary for "
            f"{len(master_skills)} skills and {len(aliases)} aliases"
        )

    monkeypatch.setattr(
        skill_list_splitter,
        "_build_known_skill_phrases",
        fail_if_built,
    )

    assert skill_list_splitter.split_skill_line(
        ["Backend: Python, JavaScript"]
    ) == ["Python", "JavaScript"]
