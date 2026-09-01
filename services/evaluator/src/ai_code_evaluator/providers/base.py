from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Sequence

from pydantic import BaseModel, ConfigDict, Field


class TokenUsage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def add(self, other: TokenUsage) -> TokenUsage:
        return TokenUsage(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
        )


class GenerateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    tool_calls: list[dict[str, Any]] | None = None
    usage: TokenUsage
    model: str
    finish_reason: str


class StructuredResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parsed: Any
    usage: TokenUsage
    model: str


class ModelProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        messages: Sequence[dict[str, Any]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> GenerateResult:
        """Generate text or tool calls from a list of messages."""
        ...

    @abstractmethod
    async def structured_generate(
        self,
        messages: Sequence[dict[str, Any]],
        response_format: type[BaseModel],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> StructuredResult:
        """Generate a structured Pydantic output."""
        ...
