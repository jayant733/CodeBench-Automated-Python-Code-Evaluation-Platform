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
        
        prompt = (
            f"Task: {task.title}\n"
            f"Instructions: {task.instructions}\n\n"
            f"Submission:\n```python\n{source_code}\n```\n\n"
            "Please review the code and output a structured ReviewVerdict. "
            "If the code perfectly solves the task, set `approved` to true."
        )

        self.memory.append(AgentMessage(role="user", content=prompt))
        
        response = await self._call_llm(
            messages=self.memory.messages,
            response_format=ReviewVerdict,
        )
        
        return response
