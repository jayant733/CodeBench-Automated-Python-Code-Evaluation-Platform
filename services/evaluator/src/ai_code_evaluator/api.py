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


def create_app(
    *,
    task_loader: TaskLoader | None = None,
    evaluation_service: EvaluationService | None = None,
) -> FastAPI:
    loader = task_loader or TaskLoader()
    service = evaluation_service or EvaluationService()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.task_loader = loader
        app.state.evaluation_service = service
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
    def health(request: Request) -> dict[str, Any]:
        runner = request.app.state.evaluation_service.runner
        return {
            "status": "ok",
            "runner": "available" if runner.available() else "unavailable",
        }

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

    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "ai_code_evaluator.api:app",
        host=os.getenv("EVALUATOR_HOST", "0.0.0.0"),
        port=int(os.getenv("EVALUATOR_PORT", "8000")),
        reload=False,
    )
