from __future__ import annotations

from typing import Any

from ai_code_evaluator.models import TaskDefinition
from ai_code_evaluator.providers import ModelProvider

from .base import BaseAgent
from .models import AgentConfig, AgentMessage, AgentResponse, CodingPlan, ReviewVerdict


class CodingAgent(BaseAgent):
    """Generates and modifies Python code using tools."""

    def __init__(self, config: AgentConfig, provider: ModelProvider) -> None:
        super().__init__(
            agent_id="coder",
            role="Software Engineer",
            system_prompt=(
                "You are an expert Python software engineer. Your goal is to implement the requested "
                "task. You MUST use the provided tools to write your solution to a file. "
                "Always write clean, efficient, and well-documented code that strictly adheres to the "
                "provided function signature and instructions. Do not include prohibited imports."
            ),
            config=config,
            provider=provider,
        )

    async def invoke(self, context: dict[str, Any]) -> AgentResponse:
        task: TaskDefinition = context["task"]
        plan: CodingPlan | None = context.get("plan")
        review: ReviewVerdict | None = context.get("review")
        test_summary: str | None = context.get("test_summary")
        tool_schemas: list[dict[str, Any]] = context.get("tools", [])

        # On the first iteration, we get the task and the plan.
        if len(self.memory.messages) == 1:  # Only system prompt
            prompt = (
                f"Task: {task.title}\n\n"
                f"Starter Code:\n```python\n{task.starter_code}\n```\n\n"
            )
            if plan:
                prompt += f"Implementation Plan:\n{plan.model_dump_json(indent=2)}\n\n"
            
            prompt += "Please implement the solution and save it using the write_file tool to 'solution.py'."
            self.memory.append(AgentMessage(role="user", content=prompt))
        else:
            # Subsequent iterations: provide feedback
            feedback = "The previous implementation failed validation.\n\n"
            if test_summary:
                feedback += f"Test Results:\n{test_summary}\n\n"
            if review:
                feedback += f"Reviewer Feedback:\n{review.model_dump_json(indent=2)}\n\n"
                
            feedback += "Please fix the issues and overwrite 'solution.py' with the corrected code."
            self.memory.append(AgentMessage(role="user", content=feedback))

        response = await self._call_llm(
            messages=self.memory.messages,
            tools=tool_schemas if tool_schemas else None,
        )
        self._remember(response)
        return response

    async def follow_up(self, tool_schemas: list[dict[str, Any]] | None = None) -> AgentResponse:
        """Continue after the orchestrator appended tool results to memory."""
        response = await self._call_llm(messages=self.memory.messages, tools=tool_schemas)
        self._remember(response)
        return response

    def _remember(self, response: AgentResponse) -> None:
        """Keep the assistant turn in memory so tool results have something to attach to."""
        self.memory.append(
            AgentMessage(
                role="assistant",
                content=response.content,
                tool_calls=response.tool_calls,
            )
        )
