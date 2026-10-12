import json

import pytest

from api.service import recruitment_job_service
from jobs import recruitment_job_store


@pytest.fixture
def recruitment_job_storage(tmp_path, monkeypatch):
    storage_dir = tmp_path / "recruitment_jobs"
    storage_dir.mkdir()
    monkeypatch.setattr(
        recruitment_job_service,
        "RECRUITMENT_JOB_STORAGE_DIR",
        storage_dir,
    )
    monkeypatch.setattr(
        recruitment_job_store,
        "RECRUITMENT_JOB_STORAGE_DIR",
        storage_dir,
    )
    return storage_dir


def _write_job(storage_dir, job_id, jd_id, created_at):
    job = {
        "job_id": job_id,
        "jd_id": jd_id,
        "status": recruitment_job_service.RECRUITMENT_JOB_ACTIVE,
        "created_at": created_at,
        "closed_at": None,
    }
    (storage_dir / f"{job_id}.json").write_text(
        json.dumps(job),
        encoding="utf-8",
    )


def test_create_reuses_active_recruitment_job_for_same_jd(
    recruitment_job_storage,
):
    first = recruitment_job_service.create_recruitment_job(
        "PythonDeveloperFresher"
    )
    second = recruitment_job_service.create_recruitment_job(
        "PythonDeveloperFresher"
    )

    assert first["job_id"] == second["job_id"]
    assert len(list(recruitment_job_storage.glob("JOB_*.json"))) == 1


def test_jd_lookup_chooses_stable_canonical_legacy_job(
    recruitment_job_storage,
):
    _write_job(
        recruitment_job_storage,
        "JOB_LATER",
        "PythonDeveloperFresher",
        "2026-10-02T00:00:00+00:00",
    )
    _write_job(
        recruitment_job_storage,
        "JOB_EARLIER",
        "PythonDeveloperFresher",
        "2026-09-01T00:00:00+00:00",
    )

    result = recruitment_job_service.get_active_recruitment_job_by_jd(
        "pythondeveloperfresher"
    )

    assert result["job_id"] == "JOB_EARLIER"


def test_unknown_job_id_resolves_from_jd_association(
    recruitment_job_storage,
):
    job = recruitment_job_service.create_recruitment_job(
        "PythonDeveloperFresher"
    )

    result = recruitment_job_service.resolve_recruitment_job_id(
        job_id="JOB_UNKNOWN",
        jd_id="PythonDeveloperFresher",
    )

    assert result == job["job_id"]


def test_known_duplicate_job_id_resolves_to_canonical_jd_job(
    recruitment_job_storage,
):
    _write_job(
        recruitment_job_storage,
        "JOB_CANONICAL",
        "PythonDeveloperFresher",
        "2026-09-01T00:00:00+00:00",
    )
    _write_job(
        recruitment_job_storage,
        "JOB_DUPLICATE",
        "PythonDeveloperFresher",
        "2026-10-01T00:00:00+00:00",
    )

    result = recruitment_job_service.resolve_recruitment_job_id(
        job_id="JOB_DUPLICATE",
        jd_id="PythonDeveloperFresher",
    )

    assert result == "JOB_CANONICAL"


def test_unknown_job_id_without_registered_jd_fails_clearly(
    recruitment_job_storage,
):
    with pytest.raises(ValueError, match="Create or retrieve it"):
        recruitment_job_service.resolve_recruitment_job_id(
            job_id="JOB_UNKNOWN",
            jd_id="UnknownJD",
        )


def test_known_job_id_for_different_jd_is_not_replaced(
    recruitment_job_storage,
):
    job = recruitment_job_service.create_recruitment_job(
        "PythonDeveloperFresher"
    )
    recruitment_job_service.create_recruitment_job(
        "SeniorPythonDeveloper"
    )

    with pytest.raises(ValueError, match="does not belong"):
        recruitment_job_service.resolve_recruitment_job_id(
            job_id=job["job_id"],
            jd_id="SeniorPythonDeveloper",
        )
