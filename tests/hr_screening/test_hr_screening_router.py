
"""Integration tests for the ZechPath HR screening router."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes import hr_screening_router as router_module


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router_module.router)
    return TestClient(app)


# ============================================================
# QUESTION BANK ENDPOINTS
# ============================================================

def test_list_roles_success(client, monkeypatch):
    expected = [
        "PYTHON_DEV_FRESHER",
        "SENIOR_PYTHON_DEVELOPER",
        "HR_EXECUTIVE_FRESHER",
        "SENIOR_HR_EXECUTIVE",
    ]

    monkeypatch.setattr(
        router_module,
        "get_available_roles",
        lambda: expected,
    )

    response = client.get("/hr-screening/roles")

    assert response.status_code == 200
    assert response.json() == expected


def test_list_roles_question_bank_error(client, monkeypatch):
    def fail():
        raise router_module.QuestionBankError("Internal details")

    monkeypatch.setattr(
        router_module,
        "get_available_roles",
        fail,
    )

    response = client.get("/hr-screening/roles")

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Unable to load HR screening data."
    )
    assert "Internal details" not in response.text


def test_list_categories_success(client, monkeypatch):
    expected = [
        "INTRODUCTION",
        "EDUCATION",
        "EXPERIENCE",
        "SKILLS",
        "LOCATION",
        "SALARY",
        "NOTICE_PERIOD",
    ]

    monkeypatch.setattr(
        router_module,
        "get_available_categories",
        lambda: expected,
    )

    response = client.get("/hr-screening/categories")

    assert response.status_code == 200
    assert response.json() == expected


def test_list_categories_question_bank_error(client, monkeypatch):
    monkeypatch.setattr(
        router_module,
        "get_available_categories",
        lambda: (_ for _ in ()).throw(
            router_module.QuestionBankError("Internal details")
        ),
    )

    response = client.get("/hr-screening/categories")

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Unable to load HR screening data."
    )


def test_list_questions_success(client, monkeypatch):
    questions = [
        {
            "question_id": "PYF_INTRO_001",
            "question": "Tell us about yourself.",
            "category": "INTRODUCTION",
            "mandatory": True,
            "answer_type": "TEXT",
        }
    ]

    monkeypatch.setattr(
        router_module,
        "get_candidate_questions",
        lambda **kwargs: questions,
    )

    response = client.get(
        "/hr-screening/questions",
        params={"role_id": "PYTHON_DEV_FRESHER"},
    )

    assert response.status_code == 200

    body = response.json()
    assert body["success"] is True
    assert body["role_id"] == "PYTHON_DEV_FRESHER"
    assert body["requested_language"] == "en"
    assert body["category"] is None
    assert body["include_optional"] is True
    assert body["total_questions"] == 1
    assert body["questions"] == questions


def test_list_questions_passes_filters(client, monkeypatch):
    captured = {}

    def fake_get_questions(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        router_module,
        "get_candidate_questions",
        fake_get_questions,
    )

    response = client.get(
        "/hr-screening/questions",
        params={
            "role_id": "PYTHON_DEV_FRESHER",
            "language": "ml",
            "category": "SKILLS",
            "include_optional": "false",
        },
    )

    assert response.status_code == 200
    assert captured == {
        "role_id": "PYTHON_DEV_FRESHER",
        "language": "ml",
        "category": "SKILLS",
        "include_optional": False,
    }


def test_list_questions_mandatory_only(client, monkeypatch):
    captured = {}

    def fake_get_questions(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(
        router_module,
        "get_candidate_questions",
        fake_get_questions,
    )

    response = client.get(
        "/hr-screening/questions",
        params={
            "role_id": "PYTHON_DEV_FRESHER",
            "include_optional": "false",
        },
    )

    assert response.status_code == 200
    assert captured["include_optional"] is False


def test_list_questions_missing_role_id_returns_422(client):
    response = client.get("/hr-screening/questions")

    assert response.status_code == 422


def test_list_questions_invalid_role_returns_400(client, monkeypatch):
    def fail(**kwargs):
        raise ValueError("Unsupported role.")

    monkeypatch.setattr(
        router_module,
        "get_candidate_questions",
        fail,
    )

    response = client.get(
        "/hr-screening/questions",
        params={"role_id": "UNKNOWN_ROLE"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid screening question request."
    )


def test_list_questions_question_bank_error(client, monkeypatch):
    def fail(**kwargs):
        raise router_module.QuestionBankError("Internal details")

    monkeypatch.setattr(
        router_module,
        "get_candidate_questions",
        fail,
    )

    response = client.get(
        "/hr-screening/questions",
        params={"role_id": "PYTHON_DEV_FRESHER"},
    )

    assert response.status_code == 500
    assert "Internal details" not in response.text


def test_get_question_success(client, monkeypatch):
    question = {
        "question_id": "PYF_SKILL_001",
        "question": "What is Python?",
        "category": "SKILLS",
        "mandatory": True,
        "answer_type": "TEXT",
    }

    captured = {}

    def fake_get_question(**kwargs):
        captured.update(kwargs)
        return question

    monkeypatch.setattr(
        router_module,
        "get_candidate_question",
        fake_get_question,
    )

    response = client.get(
        "/hr-screening/questions/PYF_SKILL_001",
        params={"language": "en"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "question": question,
    }
    assert captured == {
        "question_id": "PYF_SKILL_001",
        "language": "en",
    }


def test_get_question_not_found(client, monkeypatch):
    monkeypatch.setattr(
        router_module,
        "get_candidate_question",
        lambda **kwargs: None,
    )

    response = client.get(
        "/hr-screening/questions/UNKNOWN_QUESTION"
    )

    assert response.status_code == 404


def test_get_question_invalid_request(client, monkeypatch):
    def fail(**kwargs):
        raise ValueError("Invalid request")

    monkeypatch.setattr(
        router_module,
        "get_candidate_question",
        fail,
    )

    response = client.get(
        "/hr-screening/questions/QUESTION_001"
    )

    assert response.status_code == 400


# ============================================================
# EVALUATION ENDPOINTS
# ============================================================

def test_evaluate_session_success(client, monkeypatch):
    report = {
        "evaluation_id": "EVAL_SCREEN_TEST001",
        "session_id": "SCREEN_TEST001",
        "status": "REVIEW_REQUIRED",
        "automatic_rejection": False,
    }

    captured = {}

    def fake_evaluate(session_id, *, force=False):
        captured["session_id"] = session_id
        captured["force"] = force
        return report

    monkeypatch.setattr(
        router_module,
        "evaluate_screening_session",
        fake_evaluate,
    )

    response = client.post(
        "/hr-screening/sessions/SCREEN_TEST001/evaluate"
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["evaluation"] == report
    assert captured == {
        "session_id": "SCREEN_TEST001",
        "force": False,
    }


def test_evaluate_session_force_recalculation(client, monkeypatch):
    captured = {}

    def fake_evaluate(session_id, *, force=False):
        captured["force"] = force
        return {"session_id": session_id}

    monkeypatch.setattr(
        router_module,
        "evaluate_screening_session",
        fake_evaluate,
    )

    response = client.post(
        "/hr-screening/sessions/SCREEN_TEST001/evaluate",
        params={"force": "true"},
    )

    assert response.status_code == 200
    assert captured["force"] is True


def test_evaluate_session_not_found(client, monkeypatch):
    def fail(session_id, *, force=False):
        raise router_module.ScreeningSessionNotFoundError(
            "Screening session not found."
        )

    monkeypatch.setattr(
        router_module,
        "evaluate_screening_session",
        fail,
    )

    response = client.post(
        "/hr-screening/sessions/SCREEN_MISSING/evaluate"
    )

    assert response.status_code == 404


def test_evaluate_session_response_not_found(client, monkeypatch):
    def fail(session_id, *, force=False):
        raise router_module.ScreeningResponseNotFoundError(
            "Responses not found."
        )

    monkeypatch.setattr(
        router_module,
        "evaluate_screening_session",
        fail,
    )

    response = client.post(
        "/hr-screening/sessions/SCREEN_TEST001/evaluate"
    )

    assert response.status_code == 404


def test_evaluate_session_not_submitted(client, monkeypatch):
    def fail(session_id, *, force=False):
        raise router_module.InvalidScreeningStateError(
            "Session is not submitted."
        )

    monkeypatch.setattr(
        router_module,
        "evaluate_screening_session",
        fail,
    )

    response = client.post(
        "/hr-screening/sessions/SCREEN_TEST001/evaluate"
    )

    assert response.status_code == 409


def test_evaluate_session_invalid_stored_data(client, monkeypatch):
    def fail(session_id, *, force=False):
        raise router_module.ScreeningDataError(
            "Invalid stored data."
        )

    monkeypatch.setattr(
        router_module,
        "evaluate_screening_session",
        fail,
    )

    response = client.post(
        "/hr-screening/sessions/SCREEN_TEST001/evaluate"
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Stored screening data is invalid."
    )


def test_evaluate_session_invalid_value_returns_400(
    client,
    monkeypatch,
):
    def fail(session_id, *, force=False):
        raise ValueError("Invalid evaluation input.")

    monkeypatch.setattr(
        router_module,
        "evaluate_screening_session",
        fail,
    )

    response = client.post(
        "/hr-screening/sessions/SCREEN_TEST001/evaluate"
    )

    assert response.status_code == 400


def test_evaluate_session_unexpected_error_returns_500(
    client,
    monkeypatch,
):
    def fail(session_id, *, force=False):
        raise RuntimeError("Sensitive internal details")

    monkeypatch.setattr(
        router_module,
        "evaluate_screening_session",
        fail,
    )

    response = client.post(
        "/hr-screening/sessions/SCREEN_TEST001/evaluate"
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "An unexpected error occurred during evaluation."
    )
    assert "Sensitive internal details" not in response.text


# ============================================================
# RETRIEVE SAVED EVALUATION REPORT
# ============================================================

def test_retrieve_evaluation_success(client, monkeypatch):
    report = {
        "evaluation_id": "EVAL_SCREEN_TEST001",
        "session_id": "SCREEN_TEST001",
        "status": "REVIEW_REQUIRED",
    }

    monkeypatch.setattr(
        router_module,
        "get_screening_evaluation",
        lambda session_id: report,
    )

    response = client.get(
        "/hr-screening/sessions/SCREEN_TEST001/evaluation"
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "evaluation": report,
    }


def test_retrieve_evaluation_missing(client, monkeypatch):
    def fail(session_id):
        raise router_module.ScreeningEvaluationError(
            "No evaluation report exists for this session."
        )

    monkeypatch.setattr(
        router_module,
        "get_screening_evaluation",
        fail,
    )

    response = client.get(
        "/hr-screening/sessions/SCREEN_TEST001/evaluation"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Screening evaluation report not found."
    )


def test_retrieve_evaluation_invalid_stored_data(
    client,
    monkeypatch,
):
    def fail(session_id):
        raise router_module.ScreeningDataError(
            "Invalid stored evaluation."
        )

    monkeypatch.setattr(
        router_module,
        "get_screening_evaluation",
        fail,
    )

    response = client.get(
        "/hr-screening/sessions/SCREEN_TEST001/evaluation"
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Stored screening data is invalid."
    )


def test_retrieve_evaluation_unexpected_error(
    client,
    monkeypatch,
):
    def fail(session_id):
        raise RuntimeError("Sensitive internal details")

    monkeypatch.setattr(
        router_module,
        "get_screening_evaluation",
        fail,
    )

    response = client.get(
        "/hr-screening/sessions/SCREEN_TEST001/evaluation"
    )

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Unable to retrieve screening evaluation."
    )
    assert "Sensitive internal details" not in response.text
