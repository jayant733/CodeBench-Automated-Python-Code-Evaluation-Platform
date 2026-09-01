from __future__ import annotations

import pytest
from pydantic import BaseModel

from ai_code_evaluator.agents.base import AgentMemory, BaseAgent
from ai_code_evaluator.agents.models import AgentConfig, AgentMessage, AgentResponse
from ai_code_evaluator.providers.base import GenerateResult, ModelProvider, StructuredResult, TokenUsage


class MockProvider(ModelProvider):
    async def generate(self, messages, model, temperature=0.0, max_tokens=None, tools=None):
        return GenerateResult(
            content="mock response",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model=model,
            finish_reason="stop"
        )
        
    async def structured_generate(self, messages, response_format, model, temperature=0.0, max_tokens=None):
        class DummyOutput(BaseModel):
            result: str
            
        return StructuredResult(
            parsed=DummyOutput(result="mock structured response"),
            usage=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            model=model
        )


class DummyAgent(BaseAgent):
    async def invoke(self, context):
        self.memory.append(AgentMessage(role="user", content=context.get("prompt", "")))
        response = await self._call_llm(self.memory.messages)
        self.memory.append(AgentMessage(role="assistant", content=response.content))
        return response


def test_agent_memory_truncation() -> None:
    memory = AgentMemory(max_messages=3)
    memory.append(AgentMessage(role="system", content="System"))
    memory.append(AgentMessage(role="user", content="Msg 1"))
    memory.append(AgentMessage(role="user", content="Msg 2"))
    memory.append(AgentMessage(role="user", content="Msg 3"))
    
    assert len(memory.messages) == 3
    assert memory.messages[0].content == "System"
    assert memory.messages[1].content == "Msg 2"
    assert memory.messages[2].content == "Msg 3"


@pytest.mark.asyncio
async def test_base_agent_invoke() -> None:
    config = AgentConfig()
    provider = MockProvider()
    agent = DummyAgent("test", "test_role", "system prompt", config, provider)
    
    response = await agent.invoke({"prompt": "hello"})
    assert response.content == "mock response"
    assert response.usage.total_tokens == 15
    assert len(agent.memory.messages) == 3  # system, user, assistant
