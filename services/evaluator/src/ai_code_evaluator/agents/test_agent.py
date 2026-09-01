from __future__ import annotations

from typing import Any

from ai_code_evaluator.providers import ModelProvider
from ai_code_evaluator.models import EvaluationReport, TaskDefinition
from .base import BaseAgent
from .models import AgentConfig, AgentMessage, AgentResponse, TestFailureDetail, TestReport


class TestAgent(BaseAgent):
    """Analyzes test failures and summarizes them for the coder."""
    
    __test__ = False

    def __init__(self, config: AgentConfig, provider: ModelProvider) -> None:
        super().__init__(
            agent_id="tester",
            role="QA Engineer",
            system_prompt=(
                "You are an expert QA Engineer. Analyze the provided test evaluation report. "
                "Extract and explain the test failures clearly, detailing expected vs actual "
                "behavior to help the software engineer fix the code."
            ),
            config=config,
            provider=provider,
        )

    async def invoke(self, context: dict[str, Any]) -> AgentResponse:
        report: EvaluationReport = context["report"]
        task: TaskDefinition = context["task"]

        # Fast path: if perfect score, no need for LLM analysis
        if report.score == 100:
            structured = TestReport(
                tests_run=len(report.visible_tests),
                tests_passed=len(report.visible_tests),
                tests_failed=0,
                failure_details=[],
                execution_time_ms=report.runtime_ms,
            )
            return AgentResponse(
                content="All tests passed.",
                structured_output=structured,
                usage=self._empty_usage(),
                model=self.config.model,
                duration_ms=0,
            )

        prompt = (
            f"Task: {task.title}\n"
            f"Overall Score: {report.score}/100\n"
            f"Evaluation Report:\n{report.model_dump_json(indent=2)}\n\n"
            "Please analyze the failures and provide a structured TestReport."
        )

        self.memory.append(AgentMessage(role="user", content=prompt))
        
        response = await self._call_llm(
            messages=self.memory.messages,
            response_format=TestReport,
        )
        
        return response

    def _empty_usage(self) -> Any:
        from ai_code_evaluator.providers import TokenUsage
        return TokenUsage()
