from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from ai_code_evaluator.tools.registry import (
    ToolContext,
    ToolPermission,
    ToolRegistry,
    ToolSchema,
)
from ai_code_evaluator.tools.sandbox import AgentWorkspace
from ai_code_evaluator.tools.definitions import (
    list_files_schema, list_files_handler,
    read_file_schema, read_file_handler,
    write_file_schema, write_file_handler,
)


@pytest.fixture
def registry() -> ToolRegistry:
    return ToolRegistry()


@pytest.fixture
def context(tmp_path: Path) -> ToolContext:
    workspace = AgentWorkspace("test_session")
    workspace.root = tmp_path  # Override for pytest
    return ToolContext(
        session_id="test_session",
        task_id="test_task",
        workspace_path=workspace.root,
        allowed_permissions={ToolPermission.READ, ToolPermission.WRITE, ToolPermission.EXECUTE},
    )


def dummy_handler(context: ToolContext, param: str) -> dict[str, str]:
    return {"result": param}


async def async_dummy_handler(context: ToolContext, param: str) -> dict[str, str]:
    await asyncio.sleep(0.01)
    return {"result": param}


def test_registry_registration(registry: ToolRegistry) -> None:
    schema = ToolSchema(
        name="dummy",
        description="A dummy tool",
        parameters={"type": "object", "properties": {"param": {"type": "string"}}},
        returns={"type": "object", "properties": {"result": {"type": "string"}}},
        permissions=[ToolPermission.READ],
    )
    registry.register(schema, dummy_handler)

    assert len(registry.list_tools()) == 1
    schemas = registry.get_schemas_for_llm()
    assert schemas[0]["function"]["name"] == "dummy"
    
    with pytest.raises(ValueError):
        registry.register(schema, dummy_handler)


@pytest.mark.asyncio
async def test_tool_execution(registry: ToolRegistry, context: ToolContext) -> None:
    schema = ToolSchema(
        name="dummy",
        description="A dummy tool",
        parameters={"type": "object", "properties": {"param": {"type": "string"}}},
        returns={"type": "object", "properties": {"result": {"type": "string"}}},
        permissions=[ToolPermission.READ],
    )
    registry.register(schema, dummy_handler)

    result = await registry.execute("dummy", {"param": "hello"}, context)
    assert result.success is True
    assert result.output == {"result": "hello"}
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_tool_permission_denied(registry: ToolRegistry, context: ToolContext) -> None:
    schema = ToolSchema(
        name="dangerous_tool",
        description="A dangerous tool",
        parameters={"type": "object"},
        returns={"type": "object"},
        permissions=[ToolPermission.EXECUTE],
    )
    registry.register(schema, lambda ctx: {})

    # Drop EXECUTE permission
    context.allowed_permissions = {ToolPermission.READ}
    
    result = await registry.execute("dangerous_tool", {}, context)
    assert result.success is False
    assert "Permission denied" in str(result.error)


@pytest.mark.asyncio
async def test_tool_timeout(registry: ToolRegistry, context: ToolContext) -> None:
    async def slow_handler(ctx: ToolContext) -> dict:
        await asyncio.sleep(0.5)
        return {}
        
    schema = ToolSchema(
        name="slow",
        description="A slow tool",
        parameters={"type": "object"},
        returns={"type": "object"},
        permissions=[ToolPermission.READ],
        timeout_seconds=0.1,
    )
    registry.register(schema, slow_handler)

    result = await registry.execute("slow", {}, context)
    assert result.success is False
    assert "timed out" in str(result.error)


def test_agent_workspace_path_validation(tmp_path: Path) -> None:
    workspace = AgentWorkspace("test")
    workspace.root = tmp_path
    
    # Valid relative path
    assert workspace.get_path("valid.txt") == tmp_path / "valid.txt"
    
    # Path escape attempts
    with pytest.raises(ValueError, match="Absolute paths"):
        workspace.get_path("/etc/passwd")
        
    with pytest.raises(ValueError, match="escape attempt"):
        workspace.get_path("../outside.txt")


@pytest.mark.asyncio
async def test_file_tools_in_registry(registry: ToolRegistry, context: ToolContext) -> None:
    registry.register(write_file_schema, write_file_handler)
    registry.register(read_file_schema, read_file_handler)
    registry.register(list_files_schema, list_files_handler)

    # 1. Write file
    res_write = await registry.execute("write_file", {"path": "test.txt", "content": "hello world"}, context)
    assert res_write.success is True
    assert res_write.output["bytes_written"] == 11
    
    # 2. Read file
    res_read = await registry.execute("read_file", {"path": "test.txt"}, context)
    assert res_read.success is True
    assert res_read.output["content"] == "hello world"
    
    # 3. List files
    res_list = await registry.execute("list_files", {}, context)
    assert res_list.success is True
    assert "test.txt" in res_list.output["files"]

    # 4. Path escape on read
    res_escape = await registry.execute("read_file", {"path": "../test.txt"}, context)
    assert res_escape.success is False
    assert "blocked" in str(res_escape.error)
