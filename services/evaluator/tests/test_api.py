from __future__ import annotations

from typing import cast

from fastapi.testclient import TestClient

from ai_code_evaluator.api import create_app
from ai_code_evaluator.errors import DockerUnavailableError
from ai_code_evaluator.models import (
    ExecutionOutcome,
    ExecutionTestResult,
    TaskDefinition,
)
from ai_code_evaluator.runner import DockerRunner
from ai_code_evaluator.service import EvaluationService
from ai_code_evaluator.tasks import TaskLoader


class ApiRunner:
    def __init__(self, unavailable: bool = False) -> None:
        self.unavailable = unavailable

    def available(self) -> bool:
        return not self.unavailable

    def evaluate(self, task: TaskDefinition, source_code: str) -> ExecutionOutcome:
        if self.unavailable:
            raise DockerUnavailableError
        return ExecutionOutcome(
            imported=True,
            function_exists=True,
            runtime_ms=8,
            stdout="hello\n",
            tests=[
                ExecutionTestResult(
                    id=test.id,
                    status="passed",
                    runtime_ms=1,
                )
                for test in task.tests
            ],
        )


def client(task_loader: TaskLoader, runner: ApiRunner | None = None) -> TestClient:
    service = EvaluationService(cast(DockerRunner, runner or ApiRunner()))
    return TestClient(create_app(task_loader=task_loader, evaluation_service=service))


def test_lists_tasks_and_returns_public_task_detail(task_loader: TaskLoader) -> None:
    with client(task_loader) as api:
        listing = api.get("/api/tasks")
        detail = api.get("/api/tasks/palindrome-normalization")

    assert listing.status_code == 200
    assert len(listing.json()) == 5
    assert "tests" not in listing.json()[0]
    assert detail.status_code == 200
    payload = detail.json()
    assert len(payload["visible_tests"]) == payload["visible_test_count"]
    assert "hidden_tests" not in payload
    assert "pal-unicode" not in detail.text


def test_evaluates_submission_with_typed_report(task_loader: TaskLoader) -> None:
    with client(task_loader) as api:
        response = api.post(
            "/api/evaluations",
            json={
                "task_id": "palindrome-normalization",
                "source_code": (
                    "def is_normalized_palindrome(value):\n"
                    "    cleaned = ''.join(c.casefold() for c in value if c.isalnum())\n"
                    "    return cleaned == cleaned[::-1]\n"
                ),
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["score"] == 100
    assert payload["passed"] is True
    assert payload["score_breakdown"]["execution_signals"] == 10
    assert "code_quality" not in payload["score_breakdown"]
    assert payload["hidden_test_summary"] == {"passed": 4, "failed": 0, "total": 4}
    assert "pal-unicode" not in response.text


def test_unknown_task_returns_sanitized_404(task_loader: TaskLoader) -> None:
    with client(task_loader) as api:
        response = api.get("/api/tasks/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "task_not_found",
            "message": "The requested coding task does not exist.",
        }
    }


def test_malformed_request_is_rejected(task_loader: TaskLoader) -> None:
    with client(task_loader) as api:
        response = api.post(
            "/api/evaluations",
            json={"task_id": "palindrome-normalization", "source_code": ""},
        )

    assert response.status_code == 422


def test_docker_unavailable_returns_actionable_503(task_loader: TaskLoader) -> None:
    with client(task_loader, ApiRunner(unavailable=True)) as api:
        response = api.post(
            "/api/evaluations",
            json={
                "task_id": "palindrome-normalization",
                "source_code": "def is_normalized_palindrome(value):\n    return True\n",
            },
        )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "docker_unavailable"
    assert "Start Docker" in response.json()["error"]["message"]


def test_health_reports_runner_state(task_loader: TaskLoader) -> None:
    with client(task_loader, ApiRunner(unavailable=True)) as api:
        response = api.get("/health")

        assert response.json() == {
            "status": "degraded",
            "runner": "unavailable",
            "postgres": "available",
            "mlflow": "unavailable",
        }
