from __future__ import annotations

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

from ai_code_evaluator.agents.coder import CodingAgent
from ai_code_evaluator.agents.models import AgentConfig, AgentMessage, AgentResponse
from ai_code_evaluator.agents.planner import PlannerAgent
from ai_code_evaluator.agents.reviewer import ReviewAgent
from ai_code_evaluator.agents.security_agent import SecurityAgent
from ai_code_evaluator.agents.test_agent import TestAgent
from ai_code_evaluator.logging import bind_contextvars, clear_contextvars, get_logger
from ai_code_evaluator.models import EvaluationReport, TaskDefinition
from ai_code_evaluator.providers import ModelProvider, TokenUsage
from ai_code_evaluator.service import EvaluationService
from ai_code_evaluator.tasks import TaskLoader
from ai_code_evaluator.tools.registry import ToolContext, ToolPermission, ToolRegistry

logger = get_logger(__name__)

SOLUTION_FILENAME = "solution.py"


class OrchestratorConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_iterations: int = 3
    require_planner: bool = True
    require_reviewer: bool = True
    require_security: bool = True
    """Stop as soon as an iteration reaches this score."""
    target_score: int = 100
    """Maximum tool-calling round trips granted to the coder per iteration."""
    max_tool_steps: int = 4
    experiment_name: str = "agent-benchmark"


class IterationRecord(BaseModel):
    """In-memory record of a single coding iteration."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    iteration_number: int
    duration_ms: int
    score: int
    passed: bool
    evaluation_id: str | None = None
    review_verdict: dict[str, Any] | None = None
    security_verdict: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = []


class SessionRecorder:
    """Persists orchestrator progress. Degrades to a no-op if the store is down."""

    def __init__(self, session_id: str, task: TaskDefinition, agent_config: AgentConfig) -> None:
        self.session_id = session_id
        self.task = task
        self.agent_config = agent_config
        self.enabled = False
        self.experiment_run_id: str | None = None

    async def start(self, config: OrchestratorConfig) -> None:
        try:
            from ai_code_evaluator.db import crud
            from ai_code_evaluator.db.database import async_session_maker, engine
            from ai_code_evaluator.db.models import Base

            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async with async_session_maker() as db:
                # agent_sessions.task_id is a foreign key; the row must exist first.
                await crud.get_or_create_task(
                    db,
                    task_id=self.task.id,
                    title=self.task.title,
                    summary=self.task.summary,
                    difficulty=self.task.difficulty,
                    category=self.task.category,
                )
                experiment = await crud.get_or_create_experiment(db, config.experiment_name)
                run = await crud.create_experiment_run(
                    db,
                    experiment_id=experiment.id,
                    session_id=self.session_id,
                    model=self.agent_config.model,
                    provider=self.agent_config.provider,
                    status="in_progress",
                    parameters={
                        "max_iterations": config.max_iterations,
                        "require_planner": config.require_planner,
                        "require_reviewer": config.require_reviewer,
                        "require_security": config.require_security,
                        "target_score": config.target_score,
                        "temperature": self.agent_config.temperature,
                    },
                )
                self.experiment_run_id = run.id
                await crud.create_agent_session(
                    db,
                    session_id=self.session_id,
                    task_id=self.task.id,
                    experiment_run_id=run.id,
                )
            self.enabled = True
        except Exception as exc:
            logger.warning(f"Session persistence unavailable, running without history: {exc}")

    async def record_iteration(self, record: IterationRecord) -> None:
        if not self.enabled:
            return
        try:
            from ai_code_evaluator.db import crud
            from ai_code_evaluator.db.database import async_session_maker

            async with async_session_maker() as db:
                await crud.add_iteration(
                    db,
                    session_id=self.session_id,
                    iteration_number=record.iteration_number,
                    coding_duration_ms=record.duration_ms,
                    evaluation_id=record.evaluation_id,
                    review_verdict=record.review_verdict,
                    security_verdict=record.security_verdict,
                    tool_calls=record.tool_calls,
                )
        except Exception as exc:
            logger.warning(f"Failed to persist iteration {record.iteration_number}: {exc}")

    async def record_evaluation(self, report: EvaluationReport, source_code: str) -> str | None:
        """Persist the sandbox result so an iteration can link to concrete evidence."""
        if not self.enabled:
            return None
        try:
            from ai_code_evaluator.db import crud
            from ai_code_evaluator.db.database import async_session_maker

            async with async_session_maker() as db:
                await crud.create_evaluation_run(
                    db,
                    eval_id=report.evaluation_id,
                    task_id=report.task_id,
                    session_id=self.session_id,
                    status=report.status,
                    score=report.score,
                    score_breakdown=report.score_breakdown.model_dump(mode="json"),
                    passed=report.passed,
                    runtime_ms=report.runtime_ms,
                    stdout=report.stdout,
                    stderr=report.stderr,
                    summary=report.summary,
                    feedback=[item.model_dump(mode="json") for item in report.feedback],
                    visible_tests=[test.model_dump(mode="json") for test in report.visible_tests],
                    hidden_test_summary=report.hidden_test_summary.model_dump(mode="json"),
                    source_code=source_code,
                )
            return report.evaluation_id
        except Exception as exc:
            logger.warning(f"Failed to persist evaluation {report.evaluation_id}: {exc}")
            return None

    async def finish(
        self,
        *,
        status: str,
        final_score: int | None,
        iterations_used: int,
        total_duration_ms: int,
        usage: TokenUsage,
    ) -> None:
        if not self.enabled:
            return
        try:
            from ai_code_evaluator.db import crud
            from ai_code_evaluator.db.database import async_session_maker

            async with async_session_maker() as db:
                await crud.update_agent_session(
                    db,
                    session_id=self.session_id,
                    status=status,
                    final_score=final_score,
                    iterations_used=iterations_used,
                    total_duration_ms=total_duration_ms,
                    prompt_tokens=usage.prompt_tokens,
                    completion_tokens=usage.completion_tokens,
                )
                if self.experiment_run_id:
                    await crud.update_experiment_run(
                        db,
                        self.experiment_run_id,
                        status=status,
                        metrics={
                            "final_score": final_score or 0,
                            "iterations_used": iterations_used,
                            "total_duration_ms": total_duration_ms,
                            "prompt_tokens": usage.prompt_tokens,
                            "completion_tokens": usage.completion_tokens,
                        },
                    )
        except Exception as exc:
            logger.warning(f"Failed to finalize session {self.session_id}: {exc}")


class AgentOrchestrator:
    """Manages the lifecycle and interactions of all agents."""

    def __init__(
        self,
        provider: ModelProvider,
        tool_registry: ToolRegistry,
        eval_service: EvaluationService,
        config: OrchestratorConfig | None = None,
        agent_config: AgentConfig | None = None,
        task_loader: TaskLoader | None = None,
    ) -> None:
        self.provider = provider
        self.tool_registry = tool_registry
        self.eval_service = eval_service
        self.task_loader = task_loader or TaskLoader()
        self.config = config or OrchestratorConfig()
        self.agent_config = agent_config or AgentConfig()

        self.planner = PlannerAgent(self.agent_config, provider)
        self.coder = CodingAgent(self.agent_config, provider)
        self.reviewer = ReviewAgent(self.agent_config, provider)
        self.tester = TestAgent(self.agent_config, provider)
        self.security = SecurityAgent(self.agent_config, provider)

        # Iterations recorded by the most recent run(), for callers that report on it.
        self.last_iterations: list[IterationRecord] = []

    async def run(
        self,
        task: TaskDefinition,
        session_id: str,
        workspace_path: Any,  # Path
        run_id: str | None = None,
    ) -> EvaluationReport:
        """Run the end-to-end agentic workflow until the target score or budget is reached."""
        run_id = run_id or str(uuid.uuid4())
        bind_contextvars(
            task_id=task.id, session_id=session_id, run_id=run_id, agent="orchestrator"
        )
        logger.info(f"Starting agent session {session_id} for task {task.id}")

        workspace = Path(workspace_path)
        workspace.mkdir(parents=True, exist_ok=True)

        recorder = SessionRecorder(session_id, task, self.agent_config)
        await recorder.start(self.config)

        tracker = self._start_tracking(task, session_id)

        tool_context = ToolContext(
            session_id=session_id,
            task_id=task.id,
            workspace_path=workspace,
            allowed_permissions={ToolPermission.READ, ToolPermission.WRITE, ToolPermission.EXECUTE},
            # Tool handlers resolve these by name; the keys are part of the tool contract.
            services={
                "task_loader": self.task_loader,
                "evaluation_service": self.eval_service,
            },
        )

        context: dict[str, Any] = {
            "task": task,
            "tools": self.tool_registry.get_schemas_for_llm(),
            "plan": None,
            "review": None,
            "test_summary": None,
        }

        usage = TokenUsage()
        iterations: list[IterationRecord] = []
        self.last_iterations = iterations
        report: EvaluationReport | None = None
        session_started = time.perf_counter()
        status = "failed"

        try:
            if self.config.require_planner:
                plan_response = await self.planner.invoke(context)
                usage = usage.add(plan_response.usage)
                context["plan"] = plan_response.structured_output

            for index in range(self.config.max_iterations):
                iteration_number = index + 1
                iteration_started = time.perf_counter()

                coder_response = await self.coder.invoke(context)
                usage = usage.add(coder_response.usage)

                tool_calls = await self._run_tool_calls(coder_response, tool_context)

                source_code = self._read_solution(workspace, task)

                report = await asyncio.to_thread(self.eval_service.evaluate, task, source_code)
                evaluation_id = await recorder.record_evaluation(report, source_code)

                context["report"] = report
                context["source_code"] = source_code

                review_verdict = None
                security_verdict = None

                # Failure analysis only matters when there is something left to fix.
                if report.score < self.config.target_score:
                    test_response = await self.tester.invoke(context)
                    usage = usage.add(test_response.usage)
                    if test_response.structured_output is not None:
                        context["test_summary"] = test_response.structured_output.model_dump_json(
                            indent=2
                        )

                # Review every attempt so the winning iteration carries a verdict too.
                if self.config.require_reviewer:
                    review_response = await self.reviewer.invoke(context)
                    usage = usage.add(review_response.usage)
                    context["review"] = review_response.structured_output
                    review_verdict = self._dump_verdict(review_response.structured_output)

                if self.config.require_security:
                    security_response = await self.security.invoke(
                        {"source_code": source_code, "analysis": None}
                    )
                    usage = usage.add(security_response.usage)
                    security_verdict = self._dump_verdict(security_response.structured_output)
                    if security_verdict and security_verdict.get("safe") is False:
                        report.score = 0
                        report.passed = False
                        report.summary = (
                            "Security check failed: "
                            f"{security_verdict.get('risk_level', 'unknown')} risk."
                        )

                record = IterationRecord(
                    iteration_number=iteration_number,
                    duration_ms=int((time.perf_counter() - iteration_started) * 1000),
                    score=report.score,
                    passed=report.passed,
                    evaluation_id=evaluation_id,
                    review_verdict=review_verdict,
                    security_verdict=security_verdict,
                    tool_calls=tool_calls,
                )
                iterations.append(record)

                # Persist before any exit so a first-try success is still visible.
                await recorder.record_iteration(record)
                self._log_iteration_metrics(tracker, record)
                logger.info(
                    f"Iteration {iteration_number}/{self.config.max_iterations} "
                    f"scored {report.score} ({len(tool_calls)} tool call(s))"
                )

                if report.score >= self.config.target_score:
                    break

            if report is None:
                raise RuntimeError("Coding loop failed to produce an evaluation report.")

            status = "completed"
            return report
        finally:
            total_duration_ms = int((time.perf_counter() - session_started) * 1000)
            await recorder.finish(
                status=status,
                final_score=report.score if report else None,
                iterations_used=len(iterations),
                total_duration_ms=total_duration_ms,
                usage=usage,
            )
            self._finish_tracking(tracker, report, iterations, total_duration_ms, usage, status)
            clear_contextvars()

    async def _run_tool_calls(
        self, coder_response: AgentResponse, tool_context: ToolContext
    ) -> list[dict[str, Any]]:
        """Execute the coder's tool calls and feed each result back into its memory."""
        executed: list[dict[str, Any]] = []
        response = coder_response

        for _ in range(self.config.max_tool_steps):
            requests = response.tool_calls or []
            if not requests:
                break

            for request in requests:
                name = request.function.get("name", "")
                raw_arguments = request.function.get("arguments") or {}
                if isinstance(raw_arguments, str):
                    try:
                        arguments = json.loads(raw_arguments) if raw_arguments.strip() else {}
                    except json.JSONDecodeError as exc:
                        executed.append(
                            {
                                "tool_name": name,
                                "arguments": {"raw": raw_arguments},
                                "result": None,
                                "error": f"Invalid tool arguments: {exc}",
                                "duration_ms": 0,
                            }
                        )
                        continue
                else:
                    arguments = raw_arguments

                result = await self.tool_registry.execute(name, arguments, tool_context)
                executed.append(
                    {
                        "tool_name": result.tool_name,
                        "arguments": arguments,
                        "result": self._json_safe(result.output) if result.success else None,
                        "error": result.error,
                        "duration_ms": result.duration_ms,
                    }
                )

                self.coder.memory.append(
                    AgentMessage(
                        role="tool",
                        name=result.tool_name,
                        tool_call_id=request.id,
                        content=json.dumps(
                            {
                                "success": result.success,
                                "output": self._json_safe(result.output),
                                "error": result.error,
                            }
                        ),
                    )
                )

            # Let the coder react to the tool output; it may need another round trip.
            response = await self.coder.follow_up(self.tool_registry.get_schemas_for_llm() or None)

        return executed

    def _read_solution(self, workspace: Path, task: TaskDefinition) -> str:
        solution_path = workspace / SOLUTION_FILENAME
        if solution_path.exists():
            return solution_path.read_text(encoding="utf-8")
        # No tool wrote a file; evaluate the starter so the failure is visible in the report.
        return task.starter_code

    @staticmethod
    def _dump_verdict(verdict: Any) -> dict[str, Any] | None:
        if verdict is None:
            return None
        if isinstance(verdict, BaseModel):
            return verdict.model_dump(mode="json")
        if isinstance(verdict, dict):
            return verdict
        return {"value": str(verdict)}

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, dict):
            return {str(k): AgentOrchestrator._json_safe(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [AgentOrchestrator._json_safe(item) for item in value]
        return str(value)

    def _start_tracking(self, task: TaskDefinition, session_id: str) -> Any:
        try:
            from ai_code_evaluator.mlops.mlflow_tracker import MLflowTracker

            tracker = MLflowTracker()
            experiment_id = tracker.create_experiment(self.config.experiment_name)
            if not tracker.start_run(experiment_id, run_name=f"{task.id}:{session_id[:8]}"):
                return None
            tracker.log_params(
                {
                    "task_id": task.id,
                    "model": self.agent_config.model,
                    "provider": self.agent_config.provider,
                    "max_iterations": self.config.max_iterations,
                    "require_planner": self.config.require_planner,
                    "require_reviewer": self.config.require_reviewer,
                    "require_security": self.config.require_security,
                }
            )
            return tracker
        except Exception as exc:
            logger.warning(f"MLflow tracking unavailable: {exc}")
            return None

    @staticmethod
    def _log_iteration_metrics(tracker: Any, record: IterationRecord) -> None:
        if tracker is None:
            return
        tracker.log_metric("iteration_score", record.score)
        tracker.log_metric("iteration_duration_ms", record.duration_ms)
        tracker.log_metric("iteration_tool_calls", len(record.tool_calls))

    @staticmethod
    def _finish_tracking(
        tracker: Any,
        report: EvaluationReport | None,
        iterations: list[IterationRecord],
        total_duration_ms: int,
        usage: TokenUsage,
        status: str,
    ) -> None:
        if tracker is None:
            return
        tracker.log_metrics(
            {
                "final_score": float(report.score) if report else 0.0,
                "iterations_used": float(len(iterations)),
                "total_duration_ms": float(total_duration_ms),
                "prompt_tokens": float(usage.prompt_tokens),
                "completion_tokens": float(usage.completion_tokens),
            }
        )
        tracker.end_run(status="FINISHED" if status == "completed" else "FAILED")
