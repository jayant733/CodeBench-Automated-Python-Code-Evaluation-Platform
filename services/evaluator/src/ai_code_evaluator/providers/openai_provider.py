from __future__ import annotations

import json
from typing import Any, Sequence

from openai import AsyncOpenAI
from pydantic import BaseModel

from .base import GenerateResult, ModelProvider, StructuredResult, TokenUsage


class OpenAIProvider(ModelProvider):
    """OpenAI implementation of the ModelProvider interface."""

    def __init__(self, api_key: str | None = None, base_url: str | None = None) -> None:
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate(
        self,
        messages: Sequence[dict[str, Any]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> GenerateResult:
        response = await self.client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
            max_tokens=max_tokens,
            tools=tools,  # type: ignore
        )

        choice = response.choices[0]
        usage = response.usage

        return GenerateResult(
            content=choice.message.content or "",
            usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
            model=response.model,
            finish_reason=choice.finish_reason,
        )

    async def structured_generate(
        self,
        messages: Sequence[dict[str, Any]],
        response_format: type[BaseModel],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> StructuredResult:
        """
        Uses OpenAI's structured outputs via the `response_format` parameter.
        Requires models that support structured outputs (e.g. gpt-4o, gpt-4o-mini).
        """
        response = await self.client.beta.chat.completions.parse(
            model=model,
            messages=messages,  # type: ignore
            response_format=response_format,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        choice = response.choices[0]
        usage = response.usage

        # The parse method guarantees that `choice.message.parsed` matches the BaseModel
        if not choice.message.parsed:
            raise ValueError("Structured generation failed to return parsed data.")

        return StructuredResult(
            parsed=choice.message.parsed,
            usage=TokenUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
                total_tokens=usage.total_tokens if usage else 0,
            ),
            model=response.model,
        )
