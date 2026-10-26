
"""
tests/test_transcript_service.py

Tests for:
    api/service/transcript_service.py

Coverage:
    - Input validation
    - Transcript creation and normalization
    - JSON persistence and retrieval
    - Session-specific transcript listing
    - Duplicate transcript protection
    - Invalid identifiers and payloads
    - Missing and corrupted transcript files
    - Storage failures

Run:
    python -m pytest tests/test_transcript_service.py -v
"""

import json
from datetime import datetime, timezone

import pytest

from api.schemas.transcript_schema import (
    TranscriptCreate,
    TranscriptStatus,
)
from api.service import transcript_service as service


# ---------------------------------------------------------
# Fixtures
# ---------------------------------------------------------


@pytest.fixture
def transcript_root(tmp_path, monkeypatch):
    """Isolate every test from production transcript storage."""

    root = tmp_path / "transcripts"
    monkeypatch.setattr(service, "TRANSCRIPT_ROOT", root)

    return root


@pytest.fixture
def valid_payload():
    """Return a valid payload compatible with TranscriptCreate."""

    return {
        "session_id": "SCREEN_24E4C01EA193",
        "candidate_id": "CAN_C0CC88823474",
        "job_id": "JOB_BF2FEFE4A4A3",
        "question_id": "PYF_SKILLS_001",
        "source": "VOICE",
        "language": "en",
        "original_text": "  I know   Python and FastAPI.  ",
        "transcription": {
            "provider": "test-provider",
            "model_version": "test-model-v1",
            "confidence": 0.95,
        },
    }

@pytest.fixture(autouse=True)
def mock_screening_session(monkeypatch, valid_payload):
    """Mock valid screening sessions for transcript service tests."""

    valid_session_ids = {
        valid_payload["session_id"],
        "SCREEN_OTHER000001",
    }

    def fake_get_screening_session(session_id):
        if session_id not in valid_session_ids:
            raise service.ScreeningSessionNotFoundError(
                "Screening session was not found."
            )

        return {
            "session_id": session_id,
            "candidate_id": valid_payload["candidate_id"],
            "job_id": valid_payload["job_id"],
            "language": valid_payload["language"],
            "questions": [
                {"question_id": "PYF_SKILLS_001"},
                {"question_id": "PYF_SKILLS_002"},
            ],
        }

    monkeypatch.setattr(
        service,
        "get_screening_session",
        fake_get_screening_session,
    )
# ---------------------------------------------------------
# 1. Input validation
# ---------------------------------------------------------


def test_validate_transcript_input_returns_schema(
    valid_payload,
):
    result = service.validate_transcript_input(valid_payload)

    assert isinstance(result, TranscriptCreate)
    assert result.session_id == valid_payload["session_id"]
    assert result.candidate_id == valid_payload["candidate_id"]


def test_validate_transcript_input_accepts_model(
    valid_payload,
):
    payload = TranscriptCreate.model_validate(valid_payload)

    result = service.validate_transcript_input(payload)

    assert isinstance(result, TranscriptCreate)
    assert result.session_id == payload.session_id


def test_validate_transcript_input_rejects_missing_required_field(
    valid_payload,
):
    valid_payload.pop("candidate_id")

    with pytest.raises(service.TranscriptInputError):
        service.validate_transcript_input(valid_payload)


def test_validate_transcript_input_rejects_unsafe_session_id(
    valid_payload,
):
    valid_payload["session_id"] = "../outside"

    with pytest.raises(service.TranscriptInputError):
        service.validate_transcript_input(valid_payload)


def test_validate_transcript_input_rejects_unsafe_candidate_id(
    valid_payload,
):
    valid_payload["candidate_id"] = "../candidate"

    with pytest.raises(service.TranscriptInputError):
        service.validate_transcript_input(valid_payload)


def test_validate_transcript_input_rejects_unsafe_job_id(
    valid_payload,
):
    valid_payload["job_id"] = "../job"

    with pytest.raises(service.TranscriptInputError):
        service.validate_transcript_input(valid_payload)


def test_validate_transcript_input_rejects_unsafe_question_id(
    valid_payload,
):
    valid_payload["question_id"] = "../question"

    with pytest.raises(service.TranscriptInputError):
        service.validate_transcript_input(valid_payload)


# ---------------------------------------------------------
# 2. Create transcript
# ---------------------------------------------------------


def test_create_transcript_saves_json(
    transcript_root,
    valid_payload,
):
    record = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000001",
    )

    assert record.transcript_id == "TRN_TEST000001"
    assert record.session_id == valid_payload["session_id"]
    assert record.status == TranscriptStatus.PROCESSED

    expected_path = (
        transcript_root
        / valid_payload["session_id"]
        / "TRN_TEST000001.json"
    )

    assert expected_path.is_file()

    saved_json = json.loads(
        expected_path.read_text(encoding="utf-8")
    )

    assert saved_json["transcript_id"] == "TRN_TEST000001"
    assert saved_json["original_text"] == valid_payload["original_text"]
    assert (
        saved_json["normalized_text"]
        == "I know Python and FastAPI."
    )


def test_create_transcript_generates_id_when_omitted(
    transcript_root,
    valid_payload,
):
    record = service.create_transcript(valid_payload)

    assert record.transcript_id.startswith("TRN_")
    assert len(record.transcript_id) == 16

    expected_path = (
        transcript_root
        / valid_payload["session_id"]
        / f"{record.transcript_id}.json"
    )

    assert expected_path.is_file()


def test_create_transcript_normalizes_text(
    transcript_root,
    valid_payload,
):
    record = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000002",
    )

    assert record.original_text == (
        "  I know   Python and FastAPI.  "
    )
    assert record.normalized_text == (
        "I know Python and FastAPI."
    )


def test_create_transcript_preserves_language(
    transcript_root,
    valid_payload,
):
    valid_payload["language"] = "ml"
    valid_payload["original_text"] = (
        "  എനിക്ക്   Python അറിയാം.  "
    )

    record = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000003",
    )

    assert record.language == "ml"
    assert record.original_text == (
        "  എനിക്ക്   Python അറിയാം.  "
    )
    assert record.normalized_text == "എനിക്ക് Python അറിയാം."
    assert record.normalization.language_preserved is True


def test_create_transcript_sets_timestamps(
    transcript_root,
    valid_payload,
):
    before = datetime.now(timezone.utc)

    record = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000004",
    )

    after = datetime.now(timezone.utc)

    assert before <= record.created_at <= after
    assert before <= record.updated_at <= after

    assert record.timing.transcribed_at is not None
    assert record.timing.transcribed_at.tzinfo is not None


def test_create_transcript_preserves_review_defaults(
    transcript_root,
    valid_payload,
):
    record = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000005",
    )

    assert record.review.status.value == "PENDING"
    assert record.review.corrected_text is None


def test_create_transcript_preserves_normalization_metadata(
    transcript_root,
    valid_payload,
):
    valid_payload["normalization"] = {
        "version": "old-version",
        "language_preserved": True,
        "pii_redacted": True,
    }

    record = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000006",
    )

    assert record.normalization.version == (
        service.normalize_transcript(
            valid_payload["original_text"],
            "en",
        ).normalization_version
    )
    assert record.normalization.pii_redacted is True


def test_create_transcript_does_not_mutate_input(
    transcript_root,
    valid_payload,
):
    original_payload = json.loads(json.dumps(valid_payload))

    service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000007",
    )

    assert valid_payload == original_payload


def test_create_transcript_rejects_duplicate_id(
    transcript_root,
    valid_payload,
):
    service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000008",
    )

    changed_payload = {
        **valid_payload,
        "original_text": "A different transcript.",
    }

    with pytest.raises(service.TranscriptAlreadyExistsError):
        service.create_transcript(
            changed_payload,
            transcript_id="TRN_TEST000008",
        )

    # The original transcript must remain unchanged.
    record = service.get_transcript(
        valid_payload["session_id"],
        "TRN_TEST000008",
    )

    assert record.original_text == valid_payload["original_text"]


def test_create_transcript_rejects_unsafe_transcript_id(
    transcript_root,
    valid_payload,
):
    with pytest.raises(service.TranscriptInputError):
        service.create_transcript(
            valid_payload,
            transcript_id="../outside",
        )


def test_create_transcript_rejects_invalid_language(
    transcript_root,
    valid_payload,
):
    valid_payload["language"] = "fr"

    with pytest.raises(service.TranscriptInputError):
        service.create_transcript(valid_payload)


def test_create_transcript_rejects_blank_text(
    transcript_root,
    valid_payload,
):
    valid_payload["original_text"] = "   "

    with pytest.raises(service.TranscriptInputError):
        service.create_transcript(valid_payload)


# ---------------------------------------------------------
# 3. Retrieve transcript
# ---------------------------------------------------------


def test_get_transcript_returns_saved_record(
    transcript_root,
    valid_payload,
):
    created = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000009",
    )

    retrieved = service.get_transcript(
        session_id=created.session_id,
        transcript_id=created.transcript_id,
    )

    assert retrieved.transcript_id == created.transcript_id
    assert retrieved.session_id == created.session_id
    assert retrieved.original_text == created.original_text
    assert retrieved.normalized_text == created.normalized_text
    assert retrieved.status == created.status


def test_get_transcript_rejects_missing_record(
    transcript_root,
):
    with pytest.raises(service.TranscriptNotFoundError):
        service.get_transcript(
            "SCREEN_24E4C01EA193",
            "TRN_MISSING0001",
        )


def test_get_transcript_rejects_unsafe_session_id(
    transcript_root,
):
    with pytest.raises(service.TranscriptInputError):
        service.get_transcript(
            "../outside",
            "TRN_TEST000010",
        )


def test_get_transcript_rejects_unsafe_transcript_id(
    transcript_root,
):
    with pytest.raises(service.TranscriptInputError):
        service.get_transcript(
            "SCREEN_24E4C01EA193",
            "../outside",
        )


def test_get_transcript_does_not_cross_sessions(
    transcript_root,
    valid_payload,
):
    created = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000011",
    )

    with pytest.raises(service.TranscriptNotFoundError):
        service.get_transcript(
            session_id="SCREEN_ANOTHER0001",
            transcript_id=created.transcript_id,
        )


# ---------------------------------------------------------
# 4. List transcripts
# ---------------------------------------------------------


def test_list_transcripts_returns_all_session_records(
    transcript_root,
    valid_payload,
):
    first = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000012",
    )

    second_payload = {
        **valid_payload,
        "question_id": "PYF_SKILLS_002",
        "original_text": "I also know Django.",
    }

    second = service.create_transcript(
        second_payload,
        transcript_id="TRN_TEST000013",
    )

    records = service.list_transcripts(first.session_id)

    assert len(records) == 2
    assert {
        record.transcript_id for record in records
    } == {
        first.transcript_id,
        second.transcript_id,
    }


def test_list_transcripts_returns_empty_for_unknown_session(
    transcript_root,
):
    records = service.list_transcripts(
        "SCREEN_UNKNOWN0001"
    )

    assert records == []


def test_list_transcripts_only_returns_requested_session(
    transcript_root,
    valid_payload,
):
    service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000014",
    )

    other_payload = {
        **valid_payload,
        "session_id": "SCREEN_OTHER000001",
    }

    service.create_transcript(
        other_payload,
        transcript_id="TRN_TEST000015",
    )

    records = service.list_transcripts(
        valid_payload["session_id"]
    )

    assert len(records) == 1
    assert records[0].session_id == valid_payload["session_id"]


def test_list_transcripts_rejects_unsafe_session_id(
    transcript_root,
):
    with pytest.raises(service.TranscriptInputError):
        service.list_transcripts("../outside")


# ---------------------------------------------------------
# 5. Corrupted persisted data
# ---------------------------------------------------------


def test_get_transcript_rejects_corrupted_json(
    transcript_root,
    valid_payload,
):
    record = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000016",
    )

    path = (
        transcript_root
        / record.session_id
        / f"{record.transcript_id}.json"
    )

    path.write_text("{invalid-json", encoding="utf-8")

    with pytest.raises(service.TranscriptPersistenceError):
        service.get_transcript(
            record.session_id,
            record.transcript_id,
        )


def test_get_transcript_rejects_schema_invalid_json(
    transcript_root,
    valid_payload,
):
    record = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000017",
    )

    path = (
        transcript_root
        / record.session_id
        / f"{record.transcript_id}.json"
    )

    path.write_text(
        json.dumps({"transcript_id": record.transcript_id}),
        encoding="utf-8",
    )

    with pytest.raises(service.TranscriptPersistenceError):
        service.get_transcript(
            record.session_id,
            record.transcript_id,
        )


def test_list_transcripts_rejects_corrupted_record(
    transcript_root,
    valid_payload,
):
    record = service.create_transcript(
        valid_payload,
        transcript_id="TRN_TEST000018",
    )

    path = (
        transcript_root
        / record.session_id
        / f"{record.transcript_id}.json"
    )

    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(service.TranscriptPersistenceError):
        service.list_transcripts(record.session_id)


# ---------------------------------------------------------
# 6. Persistence failures
# ---------------------------------------------------------


def test_create_transcript_reports_storage_failure(
    tmp_path,
    monkeypatch,
    valid_payload,
):
    # Use a regular file where the service expects a directory.
    root_file = tmp_path / "not_a_directory"
    root_file.write_text("not a directory", encoding="utf-8")

    monkeypatch.setattr(service, "TRANSCRIPT_ROOT", root_file)

    with pytest.raises(service.TranscriptPersistenceError):
        service.create_transcript(
            valid_payload,
            transcript_id="TRN_TEST000019",
        )


def test_list_transcripts_rejects_file_instead_of_directory(
    transcript_root,
    valid_payload,
):
    session_id = valid_payload["session_id"]
    session_path = transcript_root / session_id

    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text("not a directory", encoding="utf-8")

    with pytest.raises(service.TranscriptPersistenceError):
        service.list_transcripts(session_id)
