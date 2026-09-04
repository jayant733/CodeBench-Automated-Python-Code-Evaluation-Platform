from __future__ import annotations

from pathlib import Path

import pytest

from ai_code_evaluator.agents.models import AgentConfig
from ai_code_evaluator.orchestrator import AgentOrchestrator, OrchestratorConfig
from ai_code_evaluator.tools.registry import ToolRegistry
from ai_code_evaluator.models import TaskDefinition, EvaluationReport
from ai_code_evaluator.service import EvaluationService

from .test_base_agent import MockProvider


class MockEvaluationService(EvaluationService):
    def evaluate(self, task: TaskDefinition, source_code: str) -> EvaluationReport:
        return EvaluationReport(
            task_id=task.id,
            evaluation_id="eval_123",
            status="completed",
            score=100,
            passed=True,
            runtime_ms=10,
            score_breakdown={"correctness": 80, "instruction_adherence": 10, "execution_signals": 10},
            visible_tests=[],
            hidden_test_summary={"passed": 0, "failed": 0, "total": 0},
            stdout="",
            stderr="",
            summary="",
            feedback=[],
        )


@pytest.fixture
def dummy_task() -> TaskDefinition:
    return TaskDefinition(
        id="test-task",
        title="Test Task",
        summary="A summary",
        difficulty="introductory",
        category="Test",
        instructions="Do the thing",
        function_name="do_thing",
        signature="def do_thing(): ...",
        starter_code="def do_thing():\n    pass",
        time_limit_seconds=1,
        memory_limit_mb=64,
        examples=[{"input": "1", "output": "1"}],
        tests=[
            {"id": "t1", "name": "t1", "visibility": "visible", "input": {}, "expected": 1},
            {"id": "t2", "name": "t2", "visibility": "visible", "input": {}, "expected": 2}
        ],
    )


@pytest.mark.asyncio
async def test_agent_orchestrator_flow(tmp_path: Path, dummy_task: TaskDefinition) -> None:
    provider = MockProvider()
    registry = ToolRegistry()
    eval_svc = MockEvaluationService(None)
    
    config = OrchestratorConfig(max_iterations=1, require_planner=True, require_reviewer=True, require_security=False)
    agent_config = AgentConfig(model="test")
    
    orchestrator = AgentOrchestrator(
        provider=provider,
        tool_registry=registry,
        eval_service=eval_svc,
        config=config,
        agent_config=agent_config,
    )
    
    report = await orchestrator.run(
        task=dummy_task,
        session_id="session_1",
        workspace_path=tmp_path,
    )
    
    assert report.score == 100
    assert report.passed is True
    # A first-try success must still be recorded, not skipped by the early exit.
    assert len(orchestrator.last_iterations) == 1
    assert orchestrator.last_iterations[0].iteration_number == 1


class ImprovingEvaluationService(EvaluationService):
    """Scores 40, then 70, then 100 so the retry loop has something to react to."""

    def __init__(self) -> None:  # noqa: D107 - test double, no runner needed
        self.scores = [40, 70, 100]
        self.calls = 0

    def evaluate(self, task: TaskDefinition, source_code: str) -> EvaluationReport:
        score = self.scores[min(self.calls, len(self.scores) - 1)]
        self.calls += 1
        return EvaluationReport(
            task_id=task.id,
            evaluation_id=f"eval_{self.calls}",
            status="completed",
            score=score,
            passed=score == 100,
            runtime_ms=10,
            score_breakdown={
                "correctness": score - 20,
                "instruction_adherence": 10,
                "execution_signals": 10,
            },
            visible_tests=[],
            hidden_test_summary={"passed": 0, "failed": 0, "total": 0},
            stdout="",
            stderr="",
            summary=f"The solution passed {score // 25} of 4 tests.",
            feedback=[],
        )


@pytest.mark.asyncio
async def test_orchestrator_iterates_until_target_score(
    tmp_path: Path, dummy_task: TaskDefinition
) -> None:
    eval_svc = ImprovingEvaluationService()
    orchestrator = AgentOrchestrator(
        provider=MockProvider(),
        tool_registry=ToolRegistry(),
        eval_service=eval_svc,
        config=OrchestratorConfig(max_iterations=5, require_security=False),
        agent_config=AgentConfig(model="test"),
    )

    report = await orchestrator.run(
        task=dummy_task,
        session_id="session_iterating",
        workspace_path=tmp_path,
    )

    assert report.score == 100
    assert eval_svc.calls == 3
    # Every attempt is recorded, and the loop stops once the target is reached.
    assert [record.score for record in orchestrator.last_iterations] == [40, 70, 100]
    assert [record.iteration_number for record in orchestrator.last_iterations] == [1, 2, 3]


@pytest.mark.asyncio
async def test_orchestrator_stops_at_iteration_budget(
    tmp_path: Path, dummy_task: TaskDefinition
) -> None:
    class NeverPassingService(ImprovingEvaluationService):
        def __init__(self) -> None:
            super().__init__()
            self.scores = [50]

    orchestrator = AgentOrchestrator(
        provider=MockProvider(),
        tool_registry=ToolRegistry(),
        eval_service=NeverPassingService(),
        config=OrchestratorConfig(max_iterations=2, require_security=False),
        agent_config=AgentConfig(model="test"),
    )

    report = await orchestrator.run(
        task=dummy_task,
        session_id="session_budget",
        workspace_path=tmp_path,
    )

    assert report.score == 50
    assert len(orchestrator.last_iterations) == 2
