from ai_code_evaluator.models import (
    ExecutionTestResult,
    ScoreSignals,
)
from ai_code_evaluator.scoring import calculate_score


def result(identifier: str, status: str) -> ExecutionTestResult:
    return ExecutionTestResult.model_validate({"id": identifier, "status": status, "runtime_ms": 1})


def test_perfect_submission_scores_100() -> None:
    score, breakdown = calculate_score(
        [result("a", "passed"), result("b", "passed")],
        ScoreSignals(
            syntax_valid=True,
            module_imported=True,
            function_exists=True,
            prohibited_behavior_absent=True,
            within_time_limit=True,
            no_runtime_error=True,
        ),
    )

    assert score == 100
    assert breakdown.correctness == 80
    assert breakdown.instruction_adherence == 10
    assert breakdown.execution_signals == 10


def test_partial_score_is_deterministic_and_explainable() -> None:
    score, breakdown = calculate_score(
        [
            result("a", "passed"),
            result("b", "failed"),
            result("c", "error"),
            result("d", "passed"),
        ],
        ScoreSignals(
            syntax_valid=True,
            module_imported=True,
            function_exists=True,
            prohibited_behavior_absent=False,
            within_time_limit=True,
            no_runtime_error=False,
        ),
    )

    assert breakdown.model_dump() == {
        "correctness": 40,
        "instruction_adherence": 6,
        "execution_signals": 8,
    }
    assert score == 54


def test_no_tests_cannot_earn_correctness_points() -> None:
    score, breakdown = calculate_score(
        [],
        ScoreSignals(
            syntax_valid=False,
            module_imported=False,
            function_exists=False,
            prohibited_behavior_absent=True,
            within_time_limit=True,
            no_runtime_error=False,
        ),
    )

    assert breakdown.correctness == 0
    assert score == 6
