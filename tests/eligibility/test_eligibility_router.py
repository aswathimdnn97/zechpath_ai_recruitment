
import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.routes.eligibility_router as eligibility_router_module
from api.routes.eligibility_router import (
    router,
)


app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _write_test_json(path: Path, data: dict) -> None:
    """Write test data to a JSON file, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data),
        encoding="utf-8",
    )


def _setup_evaluation_test(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    job_ids: list[str],
    candidate_ids: list[str],
    fake_evaluator,
) -> Path:
    """Set up isolated rules, profiles, ATS scores, and result storage."""
    rules_dir = tmp_path / "eligibility_rules"
    profiles_dir = tmp_path / "candidate_profiles"
    scoring_dir = tmp_path / "scoring_results"
    results_dir = tmp_path / "eligibility_results"

    monkeypatch.setattr(
        eligibility_router_module,
        "ELIGIBILITY_RULES_DIR",
        rules_dir,
    )
    monkeypatch.setattr(
        eligibility_router_module,
        "CANDIDATE_PROFILE_DIR",
        profiles_dir,
    )
    monkeypatch.setattr(
        eligibility_router_module,
        "ATS_SCORING_RESULTS_DIR",
        scoring_dir,
    )
    monkeypatch.setattr(
        eligibility_router_module,
        "ELIGIBILITY_RESULTS_DIR",
        results_dir,
    )
    monkeypatch.setattr(
        eligibility_router_module,
        "evaluate_candidate_eligibility",
        fake_evaluator,
    )

    # Create rules and profiles for every requested job/candidate.
    for job_id in job_ids:
        jd_id = f"JD_{job_id}"

        _write_test_json(
            rules_dir / f"{job_id}.json",
            {
                "job_id": job_id,
                "jd_id": jd_id,
                "rule_version": "1.0",
                "mandatory_skills": ["Python"],
                "experience": {"minimum_years": 1},
            },
        )

        for candidate_id in candidate_ids:
            _write_test_json(
                scoring_dir / job_id / f"{candidate_id}.json",
                {
                    "job_id": job_id,
                    "jd_id": jd_id,
                    "candidate_id": candidate_id,
                    "candidate_score": {
                        "final_score": 85.0,
                    },
                },
            )

    for candidate_id in candidate_ids:
        _write_test_json(
            profiles_dir / f"{candidate_id}.json",
            {"candidate_id": candidate_id},
        )

    return results_dir


def test_get_candidate_eligibility_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    results_dir = tmp_path / "eligibility_results"
    job_id = "JOB_57C5EC85A717"
    candidate_id = "CAN_CB63A04EDA0B"

    expected_result = {
        "job_id": job_id,
        "jd_id": "SeniorPythonDeveloper",
        "candidate_id": candidate_id,
        "eligibility_status": "REVIEW_REQUIRED",
        "checks": {
            "skills": {
                "status": "REVIEW_REQUIRED",
                "missing_skills": ["Git", "API Testing"],
            },
            "experience": {
                "status": "PASS",
                "candidate_years": 7.33,
            },
            "education": {
                "status": "PREFERRED",
                "rules": [
                    {
                        "description": (
                            "B.Tech / B.E. / equivalent technical degree preferred."
                        ),
                        "enforcement": "preferred",
                    }
                ],
            },
        },
        "evaluated_at": "2026-10-12T15:05:00.886440+00:00",
        "rule_version": "1.0",
    }

    _write_test_json(
        results_dir / job_id / f"{candidate_id}.json",
        expected_result,
    )

    monkeypatch.setattr(
        eligibility_router_module,
        "ELIGIBILITY_RESULTS_DIR",
        results_dir,
    )

    response = client.get(
        f"/eligibility/jobs/{job_id}/candidates/{candidate_id}/result"
    )

    assert response.status_code == 200
    assert response.json() == expected_result
    assert response.json()["eligibility_status"] == "REVIEW_REQUIRED"
    assert response.json()["evaluated_at"] == expected_result["evaluated_at"]


def test_get_candidate_eligibility_result_not_found(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    results_dir = tmp_path / "eligibility_results"

    monkeypatch.setattr(
        eligibility_router_module,
        "ELIGIBILITY_RESULTS_DIR",
        results_dir,
    )

    response = client.get(
        "/eligibility/jobs/JOB_57C5EC85A717/"
        "candidates/CAN_CB63A04EDA0B/result"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Eligibility result not found."


def test_reevaluation_updates_existing_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "JOB_UPDATE_TEST"
    candidate_id = "CAN_UPDATE_TEST"
    calls = {"count": 0}

    def fake_evaluator(
        candidate_profile,
        generated_rules,
        ats_score=None,
    ):
        calls["count"] += 1

        return {
            "job_id": generated_rules["job_id"],
            "jd_id": generated_rules["jd_id"],
            "candidate_id": candidate_profile["candidate_id"],
            "eligibility_status": (
                "ELIGIBLE"
                if calls["count"] == 1
                else "REVIEW_REQUIRED"
            ),
            "checks": {},
        }

    results_dir = _setup_evaluation_test(
        tmp_path,
        monkeypatch,
        [job_id],
        [candidate_id],
        fake_evaluator,
    )

    endpoint = (
        f"/eligibility/jobs/{job_id}/"
        f"candidates/{candidate_id}/evaluate"
    )

    first_response = client.post(endpoint)
    second_response = client.post(endpoint)

    assert first_response.status_code == 200
    assert first_response.json()["eligibility_status"] == "ELIGIBLE"

    assert second_response.status_code == 200
    assert second_response.json()["eligibility_status"] == "REVIEW_REQUIRED"

    result_file = results_dir / job_id / f"{candidate_id}.json"
    saved_result = json.loads(result_file.read_text(encoding="utf-8"))

    assert saved_result["eligibility_status"] == "REVIEW_REQUIRED"
    assert saved_result["evaluated_at"] == second_response.json()["evaluated_at"]
    assert len(list((results_dir / job_id).glob("*.json"))) == 1
    assert calls["count"] == 2


def test_different_candidates_have_separate_results(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_id = "JOB_CANDIDATE_ISOLATION"
    candidate_a = "CAN_ISOLATION_A"
    candidate_b = "CAN_ISOLATION_B"

    def fake_evaluator(
        candidate_profile,
        generated_rules,
        ats_score=None,
    ):
        candidate_id = candidate_profile["candidate_id"]

        return {
            "job_id": generated_rules["job_id"],
            "jd_id": generated_rules["jd_id"],
            "candidate_id": candidate_id,
            "eligibility_status": (
                "ELIGIBLE"
                if candidate_id == candidate_a
                else "REVIEW_REQUIRED"
            ),
            "checks": {},
        }

    results_dir = _setup_evaluation_test(
        tmp_path,
        monkeypatch,
        [job_id],
        [candidate_a, candidate_b],
        fake_evaluator,
    )

    for candidate_id in [candidate_a, candidate_b]:
        response = client.post(
            f"/eligibility/jobs/{job_id}/"
            f"candidates/{candidate_id}/evaluate"
        )
        assert response.status_code == 200

    file_a = results_dir / job_id / f"{candidate_a}.json"
    file_b = results_dir / job_id / f"{candidate_b}.json"

    assert file_a.is_file()
    assert file_b.is_file()
    assert file_a != file_b

    saved_a = json.loads(file_a.read_text(encoding="utf-8"))
    saved_b = json.loads(file_b.read_text(encoding="utf-8"))

    assert saved_a["candidate_id"] == candidate_a
    assert saved_a["eligibility_status"] == "ELIGIBLE"

    assert saved_b["candidate_id"] == candidate_b
    assert saved_b["eligibility_status"] == "REVIEW_REQUIRED"


def test_same_candidate_has_separate_results_for_different_jobs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    job_a = "JOB_ISOLATION_A"
    job_b = "JOB_ISOLATION_B"
    candidate_id = "CAN_JOB_ISOLATION"

    def fake_evaluator(
        candidate_profile,
        generated_rules,
        ats_score=None,
    ):
        job_id = generated_rules["job_id"]

        return {
            "job_id": job_id,
            "jd_id": generated_rules["jd_id"],
            "candidate_id": candidate_profile["candidate_id"],
            "eligibility_status": (
                "ELIGIBLE"
                if job_id == job_a
                else "REVIEW_REQUIRED"
            ),
            "checks": {},
        }

    results_dir = _setup_evaluation_test(
        tmp_path,
        monkeypatch,
        [job_a, job_b],
        [candidate_id],
        fake_evaluator,
    )

    for job_id in [job_a, job_b]:
        response = client.post(
            f"/eligibility/jobs/{job_id}/"
            f"candidates/{candidate_id}/evaluate"
        )
        assert response.status_code == 200

    file_a = results_dir / job_a / f"{candidate_id}.json"
    file_b = results_dir / job_b / f"{candidate_id}.json"

    assert file_a.is_file()
    assert file_b.is_file()

    saved_a = json.loads(file_a.read_text(encoding="utf-8"))
    saved_b = json.loads(file_b.read_text(encoding="utf-8"))

    assert saved_a["job_id"] == job_a
    assert saved_a["eligibility_status"] == "ELIGIBLE"

    assert saved_b["job_id"] == job_b
    assert saved_b["eligibility_status"] == "REVIEW_REQUIRED"


@pytest.mark.parametrize(
    ("mismatched_field", "mismatched_value"),
    [
        ("job_id", "JOB_DIFFERENT"),
        ("candidate_id", "CAN_DIFFERENT"),
    ],
)
def test_get_result_rejects_mismatched_ids(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatched_field: str,
    mismatched_value: str,
):
    job_id = "JOB_MISMATCH_TEST"
    candidate_id = "CAN_MISMATCH_TEST"

    results_dir = tmp_path / "eligibility_results"

    saved_result = {
        "job_id": job_id,
        "jd_id": "JD_MISMATCH_TEST",
        "candidate_id": candidate_id,
        "eligibility_status": "ELIGIBLE",
        "checks": {},
        "evaluated_at": "2026-10-12T15:05:00+00:00",
        "rule_version": "1.0",
    }

    saved_result[mismatched_field] = mismatched_value

    result_file = results_dir / job_id / f"{candidate_id}.json"
    _write_test_json(result_file, saved_result)

    monkeypatch.setattr(
        eligibility_router_module,
        "ELIGIBILITY_RESULTS_DIR",
        results_dir,
    )

    response = client.get(
        f"/eligibility/jobs/{job_id}/"
        f"candidates/{candidate_id}/result"
    )

    assert response.status_code == 409
    assert "does not match" in response.json()["detail"]
