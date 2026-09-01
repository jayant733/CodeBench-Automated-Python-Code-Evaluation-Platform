from __future__ import annotations

from typing import Any

from ai_code_evaluator.providers import ModelProvider
from ai_code_evaluator.models import TaskDefinition
from .base import BaseAgent
from .models import AgentConfig, AgentMessage, AgentResponse, CodingPlan


class PlannerAgent(BaseAgent):
    """Analyzes a task and creates a structured coding plan."""

    def __init__(self, config: AgentConfig, provider: ModelProvider) -> None:
        super().__init__(
            agent_id="planner",
            role="System Architect",
            system_prompt=(
                "You are an expert Python system architect. Analyze the provided coding task, "
                "including its instructions, function signature, and visible test cases. "
                "Produce a robust implementation plan detailing the approach, specific steps, "
                "and edge cases to handle. Do not write the code itself, just the plan."
            ),
            config=config,
            provider=provider,
        )

    async def invoke(self, context: dict[str, Any]) -> AgentResponse:
        task: TaskDefinition = context["task"]
        
        prompt = (
            f"Task: {task.title}\n\n"
            f"Instructions:\n{task.instructions}\n\n"
            f"Required Signature:\n```python\n{task.signature}\n```\n\n"
        )
        
        if task.examples:
            prompt += "Examples:\n"
            for ex in task.examples:
                prompt += f"Input: {ex.input}\nOutput: {ex.output}\n"
                
        prompt += "\nPlease provide a structured CodingPlan."

        self.memory.append(AgentMessage(role="user", content=prompt))
        
        response = await self._call_llm(
            messages=self.memory.messages,
            response_format=CodingPlan,
        )
        
        # We don't store the structured response in memory because it's not a text string,
        # but we can store a string representation if needed. For now, the orchestrator
        # handles the plan.
        
        return response
