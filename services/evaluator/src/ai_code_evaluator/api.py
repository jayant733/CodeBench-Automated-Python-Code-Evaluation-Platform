"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

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
from .server import EvaluatorMCPServer
from .service import EvaluationService
from .tasks import TaskLoader

logger = logging.getLogger(__name__)


class AgentRunRequest(BaseModel):
    """Request body for launching an orchestrated agent run."""

    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1, max_length=100)
    max_iterations: int = Field(default=3, ge=1, le=10)
    require_security: bool = True


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
        app.state.agent_tasks = set()
        try:
            from .db.database import engine
            from .db.models import Base

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        except Exception:
            # Session/experiment routes degrade if the store is unavailable.
            pass
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

            mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{mlflow_uri}/health", timeout=2.0)
                if resp.status_code == 200:
                    status["mlflow"] = "available"
        except Exception:
            status["status"] = "degraded"

        # Submissions cannot run at all without the sandbox runner.
        if status["runner"] != "available" or status["mlflow"] != "available":
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

    # --- Agent session history ---

    @app.post("/api/agent/sessions", status_code=202)
    async def start_agent_session(
        request_body: AgentRunRequest, request: Request
    ) -> dict[str, Any]:
        """Launch an orchestrated run in the background and return its session id."""
        task = request.app.state.task_loader.get(request_body.task_id)
        session_id = str(uuid.uuid4())

        background = asyncio.create_task(
            _run_agent_session(
                task=task,
                session_id=session_id,
                task_loader=request.app.state.task_loader,
                evaluation_service=request.app.state.evaluation_service,
                max_iterations=request_body.max_iterations,
                require_security=request_body.require_security,
            )
        )
        # Hold a strong reference; bare tasks can be garbage collected mid-run.
        running: set[asyncio.Task[None]] = request.app.state.agent_tasks
        running.add(background)
        background.add_done_callback(running.discard)

        return {
            "session_id": session_id,
            "task_id": task.id,
            "status": "in_progress",
            "max_iterations": request_body.max_iterations,
        }

    @app.get("/api/agent/sessions")
    async def get_agent_sessions() -> list[dict[str, Any]]:
        from .db.crud import list_agent_sessions
        from .db.database import async_session_maker

        async with async_session_maker() as session:
            sessions = await list_agent_sessions(session, limit=100)
            return [
                {
                    "id": s.id,
                    "task_id": s.task_id,
                    "status": s.status,
                    "final_score": s.final_score,
                    "iterations_used": s.iterations_used,
                    "iteration_count": len(s.iterations),
                    "total_duration_ms": s.total_duration_ms,
                    "prompt_tokens": s.prompt_tokens,
                    "completion_tokens": s.completion_tokens,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "updated_at": s.updated_at.isoformat() if s.updated_at else None,
                }
                for s in sessions
            ]

    @app.get("/api/agent/sessions/{session_id}")
    async def get_agent_session_details(session_id: str) -> dict[str, Any]:
        from fastapi import HTTPException

        from .db.crud import get_agent_session
        from .db.database import async_session_maker

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
                "prompt_tokens": db_session.prompt_tokens,
                "completion_tokens": db_session.completion_tokens,
                "created_at": db_session.created_at.isoformat() if db_session.created_at else None,
                "iterations": [
                    {
                        "iteration_number": i.iteration_number,
                        "coding_duration_ms": i.coding_duration_ms,
                        "evaluation_id": i.evaluation_id,
                        "review_verdict": i.review_verdict,
                        "security_verdict": i.security_verdict,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "tool_name": tc.tool_name,
                                "arguments": tc.arguments,
                                "result": tc.result,
                                "error": tc.error,
                                "duration_ms": tc.duration_ms,
                            }
                            for tc in i.tool_calls
                        ],
                    }
                    for i in db_session.iterations
                ],
            }

    @app.get("/api/experiments")
    async def list_experiments() -> list[dict[str, Any]]:
        from .db.crud import list_experiments as list_stored_experiments
        from .db.database import async_session_maker

        async with async_session_maker() as session:
            experiments = await list_stored_experiments(session, limit=50)
            return [
                {
                    "id": e.id,
                    "name": e.name,
                    "run_count": len(e.runs),
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "latest_run": _serialize_experiment_run(
                        max(
                            e.runs,
                            key=lambda run: run.created_at.isoformat() if run.created_at else "",
                        )
                    )
                    if e.runs
                    else None,
                }
                for e in experiments
            ]

    @app.get("/api/experiments/{experiment_id}")
    async def get_experiment_details(experiment_id: str) -> dict[str, Any]:
        from fastapi import HTTPException

        from .db.crud import get_experiment
        from .db.database import async_session_maker

        async with async_session_maker() as session:
            experiment = await get_experiment(session, experiment_id)
            if not experiment:
                raise HTTPException(status_code=404, detail="Experiment not found")

            runs = sorted(
                experiment.runs,
                key=lambda run: run.created_at.isoformat() if run.created_at else "",
                reverse=True,
            )
            return {
                "id": experiment.id,
                "name": experiment.name,
                "run_count": len(runs),
                "created_at": (
                    experiment.created_at.isoformat() if experiment.created_at else None
                ),
                "runs": [_serialize_experiment_run(run) for run in runs],
            }

    return app


def _serialize_experiment_run(run: Any) -> dict[str, Any]:
    return {
        "id": run.id,
        "session_id": run.session_id,
        "model": run.model,
        "provider": run.provider,
        "status": run.status,
        "metrics": run.metrics or {},
        "parameters": run.parameters or {},
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }


async def _run_agent_session(
    *,
    task: Any,
    session_id: str,
    task_loader: TaskLoader,
    evaluation_service: EvaluationService,
    max_iterations: int,
    require_security: bool,
) -> None:
    """Background driver for POST /api/agent/sessions."""
    import tempfile

    from .agents.models import AgentConfig
    from .orchestrator import AgentOrchestrator, OrchestratorConfig
    from .providers import resolve_provider
    from .tools.definitions import build_default_registry

    provider, provider_name = resolve_provider(task_loader)

    with tempfile.TemporaryDirectory(prefix=f"agent-{session_id[:8]}-") as workspace:
        orchestrator = AgentOrchestrator(
            provider=provider,
            tool_registry=build_default_registry(),
            eval_service=evaluation_service,
            task_loader=task_loader,
            config=OrchestratorConfig(
                max_iterations=max_iterations,
                require_security=require_security,
            ),
            agent_config=AgentConfig(provider=provider_name),
        )
        try:
            await orchestrator.run(task, session_id, Path(workspace))
        except Exception:
            logger.exception(f"Agent session {session_id} failed")


app = create_app()


def run() -> None:
    uvicorn.run(
        "ai_code_evaluator.api:app",
        host=os.getenv("EVALUATOR_HOST", "0.0.0.0"),
        port=int(os.getenv("EVALUATOR_PORT", "8000")),
        reload=False,
    )
