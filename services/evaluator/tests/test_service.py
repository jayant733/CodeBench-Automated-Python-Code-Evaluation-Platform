from __future__ import annotations

from typing import cast

from ai_code_evaluator.models import (
    ExecutionOutcome,
    ExecutionTestResult,
    TaskDefinition,
)
from ai_code_evaluator.runner import DockerRunner
from ai_code_evaluator.service import EvaluationService
from ai_code_evaluator.tasks import TaskLoader


class RecordingRunner:
    def __init__(self, outcome: ExecutionOutcome) -> None:
        self.outcome = outcome
        self.calls = 0

    def available(self) -> bool:
        return True

    def evaluate(self, task: TaskDefinition, source_code: str) -> ExecutionOutcome:
        self.calls += 1
        return self.outcome


def test_syntax_error_is_reported_without_invoking_runner(
    task_loader: TaskLoader,
) -> None:
    runner = RecordingRunner(
        ExecutionOutcome(
            imported=True,
            function_exists=True,
            runtime_ms=1,
        )
    )
    service = EvaluationService(cast(DockerRunner, runner))

    report = service.evaluate(
        task_loader.get("palindrome-normalization"),
        "def is_normalized_palindrome(:\n    return True",
    )

    assert runner.calls == 0
    assert report.score < 20
    assert report.feedback[0].code == "syntax_error"
    assert all(result.status == "error" for result in report.visible_tests)


def test_missing_function_is_reported_without_invoking_runner(
    task_loader: TaskLoader,
) -> None:
    runner = RecordingRunner(
        ExecutionOutcome(
            imported=True,
            function_exists=True,
            runtime_ms=1,
        )
    )
    service = EvaluationService(cast(DockerRunner, runner))

    report = service.evaluate(
        task_loader.get("palindrome-normalization"),
        "def a_different_function():\n    return True\n",
    )

    assert runner.calls == 0
    assert report.feedback[0].code == "missing_function"


def test_report_exposes_visible_details_and_only_hidden_counts(
    task_loader: TaskLoader,
) -> None:
    task = task_loader.get("palindrome-normalization")
    results = [
        ExecutionTestResult(
            id=test.id,
            status="passed",
            runtime_ms=1,
        )
        for test in task.tests
    ]
    runner = RecordingRunner(
        ExecutionOutcome(
            imported=True,
            function_exists=True,
            runtime_ms=10,
            tests=results,
        )
    )
    report = EvaluationService(cast(DockerRunner, runner)).evaluate(
        task,
        "def is_normalized_palindrome(value):\n    return True\n",
    )

    assert report.score == 100
    assert report.passed
    assert report.hidden_test_summary.passed == len(task.hidden_tests)
    serialized = report.model_dump_json()
    for hidden_test in task.hidden_tests:
        assert hidden_test.id not in serialized
        assert hidden_test.name not in serialized


def test_runtime_exception_becomes_clear_feedback(
    task_loader: TaskLoader,
) -> None:
    task = task_loader.get("palindrome-normalization")
    runner = RecordingRunner(
        ExecutionOutcome(
            imported=True,
            function_exists=True,
            runtime_ms=2,
            fatal_code="import_error",
            fatal_message="Import failed with RuntimeError: configuration exploded",
        )
    )
    report = EvaluationService(cast(DockerRunner, runner)).evaluate(
        task,
        "def is_normalized_palindrome(value):\n    raise RuntimeError('boom')\n",
    )

    assert not report.passed
    assert report.feedback[0].code == "import_error"
    assert "configuration exploded" in report.feedback[0].message
