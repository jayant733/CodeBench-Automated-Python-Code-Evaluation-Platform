from __future__ import annotations

import asyncio
from typing import Any

from mcp.server.mcpserver import MCPServer
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from ai_code_evaluator.service import EvaluationService
from ai_code_evaluator.tasks import TaskLoader


class EvaluatorMCPServer:
    """MCP Server that exposes the EvaluationService."""

    def __init__(self, task_loader: TaskLoader, evaluation_service: EvaluationService) -> None:
        self.task_loader = task_loader
        self.eval_service = evaluation_service
        self.server = MCPServer("ai-code-evaluator")
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        @self.server.tool()
        async def evaluate_code(task_id: str, source_code: str) -> str:
            """Evaluate Python source code against a specific task's test suite."""
            task = self.task_loader.get(task_id)
            report = await asyncio.to_thread(self.eval_service.evaluate, task, source_code)
            return report.model_dump_json(indent=2)
            
        @self.server.tool()
        async def get_task(task_id: str) -> str:
            """Get details and starter code for a specific task."""
            task = self.task_loader.get_public(task_id)
            return task.model_dump_json(indent=2)


