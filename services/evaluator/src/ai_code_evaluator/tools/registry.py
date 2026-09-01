from __future__ import annotations

import asyncio
import inspect
import time
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class ToolPermission(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


class ToolSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    returns: dict[str, Any]  # JSON Schema
    permissions: list[ToolPermission]
    timeout_seconds: float = 30.0


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    success: bool
    output: Any | None = None
    error: str | None = None
    duration_ms: int


class ToolContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str
    task_id: str
    workspace_path: Path
    allowed_permissions: set[ToolPermission]
    services: dict[str, Any] = Field(default_factory=dict)


class RegisteredTool:
    def __init__(self, schema: ToolSchema, handler: Callable[..., Any]):
        self.schema = schema
        self.handler = handler
        self._is_async = inspect.iscoroutinefunction(handler)

    async def __call__(self, context: ToolContext, **kwargs: Any) -> Any:
        if self._is_async:
            return await self.handler(context, **kwargs)
        # Run sync functions in a threadpool to avoid blocking the event loop
        return await asyncio.to_thread(self.handler, context, **kwargs)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, schema: ToolSchema, handler: Callable[..., Any]) -> None:
        """Register a tool with its schema and implementation."""
        if schema.name in self._tools:
            raise ValueError(f"Tool '{schema.name}' is already registered.")
        self._tools[schema.name] = RegisteredTool(schema, handler)

    def list_tools(self) -> list[ToolSchema]:
        """List all registered tools."""
        return [tool.schema for tool in self._tools.values()]

    def get_schemas_for_llm(self) -> list[dict[str, Any]]:
        """Return tool schemas formatted for OpenAI function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.schema.name,
                    "description": tool.schema.description,
                    "parameters": tool.schema.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    async def execute(
        self, name: str, arguments: dict[str, Any], context: ToolContext
    ) -> ToolResult:
        """Execute a tool with input validation, permission checks, and timeouts."""
        start_time = time.perf_counter()
        
        if name not in self._tools:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Tool '{name}' not found.",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        tool = self._tools[name]
        
        # Check permissions
        missing_perms = [
            p.value for p in tool.schema.permissions if p not in context.allowed_permissions
        ]
        if missing_perms:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Permission denied. Tool requires: {', '.join(missing_perms)}",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )

        try:
            # We don't use strict Pydantic validation for the arguments against the schema here
            # because the handler function will typically define Pydantic models for its kwargs.
            # We enforce timeout using asyncio.wait_for
            result = await asyncio.wait_for(
                tool(context, **arguments), timeout=tool.schema.timeout_seconds
            )
            return ToolResult(
                tool_name=name,
                success=True,
                output=result,
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except asyncio.TimeoutError:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Tool execution timed out after {tool.schema.timeout_seconds}s.",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except ValidationError as e:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Invalid arguments: {str(e)}",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )
        except Exception as e:
            return ToolResult(
                tool_name=name,
                success=False,
                error=f"Tool execution failed: {type(e).__name__}: {str(e)}",
                duration_ms=int((time.perf_counter() - start_time) * 1000),
            )
