"""Evaluation orchestration and report construction."""

from __future__ import annotations

import uuid

from .analysis import analyze_source
from .models import (
    EvaluationReport,
    ExecutionOutcome,
    ExecutionTestResult,
    FeedbackItem,
    HiddenTestSummary,
    ScoreSignals,
    TaskDefinition,
    TestResult,
)
from .runner import DockerRunner
from .scoring import calculate_score


class EvaluationService:
    def __init__(self, runner: DockerRunner | None = None) -> None:
        self.runner = runner or DockerRunner()

    def evaluate(self, task: TaskDefinition, source_code: str) -> EvaluationReport:
        analysis = analyze_source(source_code, task.function_name)
        if not analysis.syntax_valid:
            outcome = self._fatal_outcome(task, "syntax_error", analysis.syntax_message or "")
        elif not analysis.function_exists:
            outcome = self._fatal_outcome(
                task,
                "missing_function",
                f"Define the required function '{task.function_name}' at module scope.",
            )
        else:
            outcome = self.runner.evaluate(task, source_code)

        execution_by_id = {result.id: result for result in outcome.tests}
        normalized_results = [
            execution_by_id.get(
                test.id,
                ExecutionTestResult(
                    id=test.id,
                    status="error",
                    runtime_ms=0,
                    message=outcome.fatal_message or "The test did not run.",
                ),
            )
            for test in task.tests
        ]
        signals = ScoreSignals(
            syntax_valid=analysis.syntax_valid,
            module_imported=outcome.imported,
            function_exists=analysis.function_exists and outcome.function_exists,
            prohibited_behavior_absent=analysis.prohibited_behavior_absent,
            within_time_limit=not outcome.timed_out,
            no_runtime_error=outcome.fatal_code is None,
        )
        score, breakdown = calculate_score(normalized_results, signals)

        passed_count = sum(result.status == "passed" for result in normalized_results)
        visible_results = []
        for test in task.visible_tests:
            result = execution_by_id.get(test.id)
            if result is None:
                result = ExecutionTestResult(
                    id=test.id,
                    status="error",
                    runtime_ms=0,
                    message=outcome.fatal_message or "The test did not run.",
                )
            visible_results.append(
                TestResult(
                    id=test.id,
                    name=test.name,
                    status=result.status,
                    runtime_ms=result.runtime_ms,
                    message=result.message,
                )
            )

        hidden_results = [
            result
            for test in task.hidden_tests
            for result in [
                execution_by_id.get(
                    test.id,
                    ExecutionTestResult(
                        id=test.id,
                        status="error",
                        runtime_ms=0,
                        message=None,
                    ),
                )
            ]
        ]
        hidden_passed = sum(result.status == "passed" for result in hidden_results)
        report_passed = passed_count == len(task.tests)

        feedback = self._feedback(
            task=task,
            outcome=outcome,
            prohibited_imports=analysis.prohibited_imports,
            visible_results=visible_results,
            hidden_failed=len(hidden_results) - hidden_passed,
        )

        return EvaluationReport(
            evaluation_id=str(uuid.uuid4()),
            task_id=task.id,
            status="completed",
            score=score,
            score_breakdown=breakdown,
            passed=report_passed,
            summary=(
                f"The solution passed {passed_count} of {len(task.tests)} tests."
                if not report_passed
                else f"All {len(task.tests)} tests passed."
            ),
            visible_tests=visible_results,
            hidden_test_summary=HiddenTestSummary(
                passed=hidden_passed,
                failed=len(hidden_results) - hidden_passed,
                total=len(hidden_results),
            ),
            runtime_ms=outcome.runtime_ms,
            stdout=outcome.stdout,
            stderr=outcome.stderr,
            feedback=feedback,
        )

    @staticmethod
    def _fatal_outcome(task: TaskDefinition, code: str, message: str) -> ExecutionOutcome:
        return ExecutionOutcome(
            imported=False,
            function_exists=False,
            runtime_ms=0,
            fatal_code=code,
            fatal_message=message,
        )

    @staticmethod
    def _feedback(
        *,
        task: TaskDefinition,
        outcome: ExecutionOutcome,
        prohibited_imports: list[str],
        visible_results: list[TestResult],
        hidden_failed: int,
    ) -> list[FeedbackItem]:
        feedback: list[FeedbackItem] = []
        if outcome.fatal_code:
            feedback.append(
                FeedbackItem(
                    code=outcome.fatal_code,
                    message=outcome.fatal_message or "Execution did not complete.",
                    severity="error",
                )
            )
        if prohibited_imports:
            feedback.append(
                FeedbackItem(
                    code="prohibited_import",
                    message=(
                        "Remove imports that are outside this task's contract: "
                        + ", ".join(prohibited_imports)
                        + "."
                    ),
                    severity="warning",
                )
            )
        failed_visible = [result.name for result in visible_results if result.status != "passed"]
        if failed_visible and not outcome.fatal_code:
            feedback.append(
                FeedbackItem(
                    code="visible_test_failures",
                    message="Review the failing visible cases: " + ", ".join(failed_visible) + ".",
                    severity="warning",
                )
            )
        if hidden_failed and not outcome.fatal_code:
            feedback.append(
                FeedbackItem(
                    code="hidden_test_failures",
                    message=(
                        f"{hidden_failed} hidden case(s) failed. Re-check edge cases in the "
                        f"{task.title} contract."
                    ),
                    severity="warning",
                )
            )
        if not feedback:
            feedback.append(
                FeedbackItem(
                    code="all_tests_passed",
                    message="The submission satisfies every visible and hidden case.",
                    severity="info",
                )
            )
        return feedback
