
import json

import pytest

from api.service import transcript_skill_extraction_persistence_service as service


@pytest.fixture
def transcript():
    return {
        "session_id": "SCREEN_3F897D8A2CDE",
        "candidate_id": "CAN_123456789ABC",
        "job_id": "JOB_BF2FEFE4A4A3",
        "question_id": "PYF_EDU_001",
        "source": "VOICE",
        "language": "en",
        "original_text": "I have learned Python and SQL.",
        "normalized_text": "I have learned Python and SQL.",
        "transcript_id": "TRN_428A03F8246C",
        "status": "PROCESSED",
    }


@pytest.fixture
def mock_extractor(monkeypatch):
    calls = []

    def fake_extract(payload):
        calls.append(payload)
        return {
            "original_text": payload["original_text"],
            "normalized_text": payload["normalized_text"],
            "language": payload["language"],
            "recognized_skills": [
                {"skill": "Python"},
                {"skill": "SQL"},
            ],
            "skill_count": 2,
        }

    monkeypatch.setattr(
        service,
        "extract_transcript_skills",
        fake_extract,
    )
    return calls


def test_persists_result_and_preserves_metadata(
    transcript, tmp_path, mock_extractor
):
    result = service.process_and_save_transcript_skills(
        transcript,
        output_dir=tmp_path,
    )

    expected_path = (
        tmp_path
        / transcript["session_id"]
        / f"{transcript['transcript_id']}.json"
    )

    assert expected_path.exists()
    saved = json.loads(expected_path.read_text(encoding="utf-8"))

    assert saved == result
    assert result["session_id"] == transcript["session_id"]
    assert result["candidate_id"] == transcript["candidate_id"]
    assert result["job_id"] == transcript["job_id"]
    assert result["question_id"] == transcript["question_id"]
    assert result["transcript_id"] == transcript["transcript_id"]
    assert result["source"] == "VOICE"
    assert result["skill_count"] == 2
    assert result["status"] == "COMPLETED"
    assert len(mock_extractor) == 1


def test_repeated_call_reuses_existing_result(
    transcript, tmp_path, mock_extractor
):
    first = service.process_and_save_transcript_skills(
        transcript, output_dir=tmp_path
    )
    second = service.process_and_save_transcript_skills(
        transcript, output_dir=tmp_path
    )

    assert second == first
    assert len(mock_extractor) == 1


def test_changed_normalized_text_recalculates_result(
    transcript, tmp_path, mock_extractor
):
    first = service.process_and_save_transcript_skills(
        transcript, output_dir=tmp_path
    )

    updated_transcript = {
        **transcript,
        "normalized_text": "I have learned Python, SQL, and HTML.",
    }

    second = service.process_and_save_transcript_skills(
        updated_transcript, output_dir=tmp_path
    )

    assert second["result_id"] == first["result_id"]
    assert second["input_text_sha256"] != first["input_text_sha256"]
    assert len(mock_extractor) == 2


def test_rejects_transcript_that_is_not_processed(
    transcript, tmp_path
):
    transcript["status"] = "IN_PROGRESS"

    with pytest.raises(service.TranscriptSkillPersistenceError):
        service.process_and_save_transcript_skills(
            transcript, output_dir=tmp_path
        )


def test_rejects_unsupported_language(transcript, tmp_path):
    transcript["language"] = "fr"

    with pytest.raises(service.TranscriptSkillPersistenceError):
        service.process_and_save_transcript_skills(
            transcript, output_dir=tmp_path
        )


def test_rejects_missing_transcript_metadata(transcript, tmp_path):
    del transcript["question_id"]

    with pytest.raises(service.TranscriptSkillPersistenceError):
        service.process_and_save_transcript_skills(
            transcript, output_dir=tmp_path
        )


def test_reports_storage_failure(
    transcript, tmp_path, mock_extractor, monkeypatch
):
    def fail_write(destination, payload):
        raise service.TranscriptSkillPersistenceError(
            "Simulated storage failure"
        )

    monkeypatch.setattr(service, "_write_json_atomically", fail_write)

    with pytest.raises(service.TranscriptSkillPersistenceError):
        service.process_and_save_transcript_skills(
            transcript, output_dir=tmp_path
        )
