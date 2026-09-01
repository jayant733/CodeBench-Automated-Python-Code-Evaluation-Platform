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
