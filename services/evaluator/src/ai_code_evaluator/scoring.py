"""Deterministic and deliberately modest scoring rules."""

from __future__ import annotations

from .models import ExecutionTestResult, ScoreBreakdown, ScoreSignals


def calculate_score(
    results: list[ExecutionTestResult], signals: ScoreSignals
) -> tuple[int, ScoreBreakdown]:
    total = len(results)
    passed = sum(result.status == "passed" for result in results)
    correctness = round(80 * passed / total) if total else 0

    instruction_adherence = 0
    if signals.function_exists:
        instruction_adherence += 6
    if signals.prohibited_behavior_absent:
        instruction_adherence += 4

    execution_signals = 0
    if signals.syntax_valid:
        execution_signals += 3
    if signals.module_imported:
        execution_signals += 3
    if signals.within_time_limit:
        execution_signals += 2
    if signals.no_runtime_error:
        execution_signals += 2

    breakdown = ScoreBreakdown(
        correctness=correctness,
        instruction_adherence=instruction_adherence,
        execution_signals=execution_signals,
    )
    return correctness + instruction_adherence + execution_signals, breakdown
