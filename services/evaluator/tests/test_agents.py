from __future__ import annotations

import pytest

from ai_code_evaluator.agents.models import (
    AgentConfig,
    CodingPlan,
    ReviewVerdict,
    SecurityVerdict,
    TestReport,
)
from ai_code_evaluator.agents.planner import PlannerAgent
from ai_code_evaluator.agents.coder import CodingAgent
from ai_code_evaluator.agents.test_agent import TestAgent
from ai_code_evaluator.agents.reviewer import ReviewAgent
from ai_code_evaluator.agents.security_agent import SecurityAgent
from ai_code_evaluator.models import TaskDefinition, EvaluationReport, TestResult
from ai_code_evaluator.analysis import SourceAnalysis

from .test_base_agent import MockProvider


@pytest.fixture
def config() -> AgentConfig:
    return AgentConfig()


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider()


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
async def test_planner_agent(config: AgentConfig, provider: MockProvider, dummy_task: TaskDefinition) -> None:
    agent = PlannerAgent(config, provider)
    response = await agent.invoke({"task": dummy_task})
    
    # Provider mock returns a dummy structured object, but since we use response_format=CodingPlan,
    # the mock needs to return something that looks like CodingPlan. 
    # For testing, we just check that the prompt was formed correctly.
    assert len(agent.memory.messages) == 2
    assert "Do the thing" in agent.memory.messages[1].content


@pytest.mark.asyncio
async def test_coding_agent(config: AgentConfig, provider: MockProvider, dummy_task: TaskDefinition) -> None:
    agent = CodingAgent(config, provider)
    response = await agent.invoke({"task": dummy_task})
    
    assert len(agent.memory.messages) == 2
    assert "def do_thing():" in agent.memory.messages[1].content
    
    # Test iteration > 1
    await agent.invoke({
        "task": dummy_task,
        "test_summary": "Failed 1 test",
    })
    assert len(agent.memory.messages) == 3
    assert "Failed 1 test" in agent.memory.messages[2].content


@pytest.mark.asyncio
async def test_test_agent_perfect_score(config: AgentConfig, provider: MockProvider, dummy_task: TaskDefinition) -> None:
    agent = TestAgent(config, provider)
    report = EvaluationReport(
        task_id="test",
        evaluation_id="123",
        status="completed",
        score=100,
        passed=True,
        runtime_ms=10,
        score_breakdown={"correctness": 80, "instruction_adherence": 10, "execution_signals": 10},
        visible_tests=[
            TestResult(id="1", name="t1", status="passed", runtime_ms=5)
        ],
        hidden_test_summary={"passed": 0, "failed": 0, "total": 0},
        stdout="",
        stderr="",
        summary="",
        feedback=[],
    )
    response = await agent.invoke({"task": dummy_task, "report": report})
    
    # Should bypass LLM for score=100
    assert response.structured_output.tests_passed == 1
    assert response.structured_output.tests_failed == 0
    assert len(agent.memory.messages) == 1  # Only system prompt


@pytest.mark.asyncio
async def test_security_agent_overrides_llm(config: AgentConfig, provider: MockProvider) -> None:
    agent = SecurityAgent(config, provider)
    
    analysis = SourceAnalysis(
        syntax_valid=True,
        function_exists=True,
        prohibited_behavior_absent=False,
        prohibited_imports=["socket"],
    )
    
    # Provide a mock provider that returns a "safe" verdict to test the override
    class SafeMockProvider(MockProvider):
        async def structured_generate(self, messages, response_format, model, temperature=0.0, max_tokens=None):
            from ai_code_evaluator.providers.base import StructuredResult, TokenUsage
            return StructuredResult(
                parsed=SecurityVerdict(safe=True, risk_level="none", findings=[]),
                usage=TokenUsage(),
                model=model
            )
            
    agent.provider = SafeMockProvider()
    response = await agent.invoke({
        "source_code": "import socket",
        "analysis": analysis,
    })
    
    verdict: SecurityVerdict = response.structured_output
    assert verdict.safe is False
    assert verdict.risk_level == "high"
    assert len(verdict.findings) == 1
    assert verdict.findings[0].category == "prohibited_import"
