from __future__ import annotations

from typing import Any

from ai_code_evaluator.providers import ModelProvider
from ai_code_evaluator.models import TaskDefinition
from .base import BaseAgent
from .models import AgentConfig, AgentMessage, AgentResponse, ReviewVerdict


class ReviewAgent(BaseAgent):
    """Reviews the source code for quality and adherence."""

    def __init__(self, config: AgentConfig, provider: ModelProvider) -> None:
        super().__init__(
            agent_id="reviewer",
            role="Senior Code Reviewer",
            system_prompt=(
                "You are an expert Senior Python Developer. Review the provided source code against "
                "the task instructions. Verify that the code is clean, handles edge cases, and "
                "doesn't take shortcuts. Provide a structured ReviewVerdict."
            ),
            config=config,
            provider=provider,
        )

    async def invoke(self, context: dict[str, Any]) -> AgentResponse:
        task: TaskDefinition = context["task"]
        source_code: str = context["source_code"]
        report = context.get("report")

        prompt = (
            f"Task: {task.title}\n"
            f"Instructions: {task.instructions}\n\n"
            f"Submission:\n```python\n{source_code}\n```\n\n"
        )

        # Review against sandbox evidence rather than reading the code blind.
        if report is not None:
            failing = [
                test.name for test in report.visible_tests if test.status != "passed"
            ]
            prompt += (
                f"Sandbox result: score {report.score}/100. {report.summary}\n"
                f"Failing visible cases: {', '.join(failing) if failing else 'none'}\n"
                f"Hidden cases: {report.hidden_test_summary.passed} passed, "
                f"{report.hidden_test_summary.failed} failed.\n\n"
            )

        prompt += (
            "Please review the code and output a structured ReviewVerdict. "
            "If the code perfectly solves the task, set `approved` to true."
        )

        self.memory.append(AgentMessage(role="user", content=prompt))
        
        response = await self._call_llm(
            messages=self.memory.messages,
            response_format=ReviewVerdict,
        )
        
        return response
