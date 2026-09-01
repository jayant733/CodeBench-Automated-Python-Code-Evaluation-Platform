from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from ai_code_evaluator.providers import ModelProvider
from .models import AgentConfig, AgentMessage, AgentResponse, ToolCallRequest


class AgentMemory:
    """Append-only conversation history with token-aware truncation."""

    def __init__(self, max_messages: int = 100) -> None:
        self.messages: list[AgentMessage] = []
        self.max_messages = max_messages

    def append(self, msg: AgentMessage) -> None:
        self.messages.append(msg)
        if len(self.messages) > self.max_messages:
            # Keep system message if it's first
            if self.messages[0].role == "system":
                self.messages = [self.messages[0]] + self.messages[-(self.max_messages - 1):]
            else:
                self.messages = self.messages[-self.max_messages:]

    def to_list(self) -> list[dict[str, Any]]:
        return [msg.model_dump(mode="json", exclude_none=True) for msg in self.messages]

    def clear(self) -> None:
        self.messages.clear()


class BaseAgent(ABC):
    """Abstract foundation for specialized agents."""

    def __init__(
        self,
        agent_id: str,
        role: str,
        system_prompt: str,
        config: AgentConfig,
        provider: ModelProvider,
    ) -> None:
        self.agent_id = agent_id
        self.role = role
        self.system_prompt = system_prompt
        self.config = config
        self.provider = provider
        self.memory = AgentMemory()
        
        # Initialize memory with system prompt
        self.memory.append(AgentMessage(role="system", content=self.system_prompt))

    @abstractmethod
    async def invoke(self, context: dict[str, Any]) -> AgentResponse:
        """Process the context and return a structured response."""
        ...

    async def _call_llm(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, Any]] | None = None,
        response_format: Any | None = None,
    ) -> AgentResponse:
        """Delegate generation to the ModelProvider."""
        start_time = time.perf_counter()
        
        raw_messages = [msg.model_dump(mode="json", exclude_none=True) for msg in messages]

        if response_format:
            result = await self.provider.structured_generate(
                messages=raw_messages,
                response_format=response_format,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )
            return AgentResponse(
                content="",
                structured_output=result.parsed,
                usage=result.usage,
                model=result.model,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )
        else:
            result = await self.provider.generate(
                messages=raw_messages,
                model=self.config.model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                tools=tools,
            )
            return AgentResponse(
                content=result.content,
                tool_calls=[ToolCallRequest(**tc) for tc in result.tool_calls] if result.tool_calls else None,
                usage=result.usage,
                model=result.model,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )
