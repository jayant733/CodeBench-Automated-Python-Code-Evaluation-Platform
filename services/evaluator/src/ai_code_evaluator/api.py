"""FastAPI application entrypoint."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .errors import (
    DockerUnavailableError,
    EvaluatorError,
    RunnerImageUnavailableError,
    TaskNotFoundError,
)
from .models import (
    ErrorDetail,
    ErrorResponse,
    EvaluationReport,
    EvaluationRequest,
    PublicTask,
    TaskSummary,
)
from .service import EvaluationService
from .tasks import TaskLoader
from .server import EvaluatorMCPServer


def create_app(
    *,
    task_loader: TaskLoader | None = None,
    evaluation_service: EvaluationService | None = None,
) -> FastAPI:
    loader = task_loader or TaskLoader()
    service = evaluation_service or EvaluationService()

    mcp_server = EvaluatorMCPServer(loader, service)
    mcp_asgi_app = mcp_server.server.streamable_http_app(streamable_http_path="/")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.task_loader = loader
        app.state.evaluation_service = service
        # Trigger the MCPServer lifespan so it initializes its background task group
        async with mcp_asgi_app.router.lifespan_context(app):
            yield

    app = FastAPI(
        title="AI Code Evaluation API",
        version="0.1.0",
        description="Typed task discovery and Docker-isolated Python evaluation.",
        lifespan=lifespan,
    )
    allowed_origins = [
        origin.strip()
        for origin in os.getenv(
            "EVALUATOR_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    # Mount the ASGI app
    app.mount("/mcp", mcp_asgi_app)

    @app.exception_handler(EvaluatorError)
    async def evaluator_error_handler(_request: Request, exc: EvaluatorError) -> JSONResponse:
        status_code = 500
        if isinstance(exc, TaskNotFoundError):
            status_code = 404
        elif isinstance(exc, (DockerUnavailableError, RunnerImageUnavailableError)):
            status_code = 503
        payload = ErrorResponse(error=ErrorDetail(code=exc.code, message=exc.public_message))
        return JSONResponse(status_code=status_code, content=payload.model_dump())

    @app.get("/health")
    async def health(request: Request) -> dict[str, Any]:
        runner = request.app.state.evaluation_service.runner
        status = {
            "status": "ok",
            "runner": "available" if runner.available() else "unavailable",
            "postgres": "unavailable",
            "mlflow": "unavailable",
        }
        
        # Check DB
        try:
            from sqlalchemy import text
            from .db.database import async_session_maker
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
            status["postgres"] = "available"
        except Exception:
            status["status"] = "degraded"
            
        # Check MLflow (simple HTTP GET to the tracking URI)
        try:
            import httpx
            import os
            mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{mlflow_uri}/health", timeout=2.0)
                if resp.status_code == 200:
                    status["mlflow"] = "available"
        except Exception:
            status["status"] = "degraded"
            
        return status

    @app.get("/api/tasks", response_model=list[TaskSummary])
    def list_tasks(request: Request) -> list[TaskSummary]:
        return request.app.state.task_loader.list_public()

    @app.get("/api/tasks/{task_id}", response_model=PublicTask)
    def get_task(task_id: str, request: Request) -> PublicTask:
        return request.app.state.task_loader.get_public(task_id)

    @app.post("/api/evaluations", response_model=EvaluationReport)
    def evaluate_submission(submission: EvaluationRequest, request: Request) -> EvaluationReport:
        task = request.app.state.task_loader.get(submission.task_id)
        return request.app.state.evaluation_service.evaluate(task, submission.source_code)

    # --- P1 Extensions ---

    @app.get("/api/agent/sessions")
    async def get_agent_sessions() -> list[dict[str, Any]]:
        from sqlalchemy import select
        from .db.database import async_session_maker
        from .db.models import AgentSession
        
        async with async_session_maker() as session:
            result = await session.execute(select(AgentSession).order_by(AgentSession.created_at.desc()).limit(100))
            sessions = result.scalars().all()
            return [
                {
                    "id": s.id,
                    "task_id": s.task_id,
                    "status": s.status,
                    "final_score": s.final_score,
                    "iterations_used": s.iterations_used,
                    "total_duration_ms": s.total_duration_ms,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in sessions
            ]

    @app.get("/api/agent/sessions/{session_id}")
    async def get_agent_session_details(session_id: str) -> dict[str, Any]:
        from fastapi import HTTPException
        from .db.database import async_session_maker
        from .db.crud import get_agent_session
        
        async with async_session_maker() as session:
            db_session = await get_agent_session(session, session_id)
            if not db_session:
                raise HTTPException(status_code=404, detail="Session not found")
                
            return {
                "id": db_session.id,
                "task_id": db_session.task_id,
                "status": db_session.status,
                "final_score": db_session.final_score,
                "iterations_used": db_session.iterations_used,
                "total_duration_ms": db_session.total_duration_ms,
                "iterations": [
                    {
                        "iteration_number": i.iteration_number,
                        "coding_duration_ms": i.coding_duration_ms,
                        "review_verdict": i.review_verdict,
                        "security_verdict": i.security_verdict,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "tool_name": tc.tool_name,
                                "arguments": tc.arguments,
                                "result": tc.result,
                                "duration_ms": tc.duration_ms,
                            } for tc in i.tool_calls
                        ]
                    } for i in db_session.iterations
                ]
            }

    @app.get("/api/experiments")
    async def list_experiments() -> list[dict[str, Any]]:
        from sqlalchemy import select
        from .db.database import async_session_maker
        from .db.models import Experiment
        
        async with async_session_maker() as session:
            result = await session.execute(select(Experiment).order_by(Experiment.created_at.desc()).limit(50))
            experiments = result.scalars().all()
            return [
                {
                    "id": e.id,
                    "name": e.name,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in experiments
            ]

    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "ai_code_evaluator.api:app",
        host=os.getenv("EVALUATOR_HOST", "0.0.0.0"),
        port=int(os.getenv("EVALUATOR_PORT", "8000")),
        reload=False,
    )
