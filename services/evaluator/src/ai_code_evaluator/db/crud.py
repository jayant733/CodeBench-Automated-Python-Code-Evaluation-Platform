from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    AgentIteration,
    AgentSession,
    EvaluationRun,
    Experiment,
    ExperimentRun,
    Task,
    ToolCall,
)

logger = logging.getLogger(__name__)


async def get_or_create_task(
    db: AsyncSession, task_id: str, title: str, summary: str, difficulty: str, category: str
) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        task = Task(
            id=task_id, title=title, summary=summary, difficulty=difficulty, category=category
        )
        db.add(task)
        await db.commit()
    return task


async def create_evaluation_run(
    db: AsyncSession, eval_id: str, task_id: str, session_id: str | None, **kwargs: Any
) -> EvaluationRun:
    run = EvaluationRun(id=eval_id, task_id=task_id, session_id=session_id, **kwargs)
    db.add(run)
    await db.commit()
    return run


async def create_agent_session(
    db: AsyncSession, session_id: str, task_id: str, experiment_run_id: str | None = None
) -> AgentSession:
    session = AgentSession(
        id=session_id, task_id=task_id, experiment_run_id=experiment_run_id, status="in_progress"
    )
    db.add(session)
    await db.commit()
    return session


async def update_agent_session(
    db: AsyncSession, session_id: str, **kwargs: Any
) -> AgentSession | None:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        for k, v in kwargs.items():
            setattr(session, k, v)
        await db.commit()
    return session


async def create_agent_iteration(
    db: AsyncSession, iteration_id: str, session_id: str, iteration_number: int, **kwargs: Any
) -> AgentIteration:
    iteration = AgentIteration(
        id=iteration_id, session_id=session_id, iteration_number=iteration_number, **kwargs
    )
    db.add(iteration)
    await db.commit()
    return iteration


async def create_tool_call(
    db: AsyncSession,
    tool_call_id: str,
    iteration_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    **kwargs: Any,
) -> ToolCall:
    tc = ToolCall(
        id=tool_call_id,
        iteration_id=iteration_id,
        tool_name=tool_name,
        arguments=arguments,
        **kwargs,
    )
    db.add(tc)
    await db.commit()
    return tc


async def get_agent_session(db: AsyncSession, session_id: str) -> AgentSession | None:
    result = await db.execute(
        select(AgentSession)
        .options(selectinload(AgentSession.iterations).selectinload(AgentIteration.tool_calls))
        .where(AgentSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def list_agent_sessions(db: AsyncSession, limit: int = 100) -> list[AgentSession]:
    result = await db.execute(
        select(AgentSession)
        .options(selectinload(AgentSession.iterations))
        .order_by(AgentSession.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def list_experiments(db: AsyncSession, limit: int = 50) -> list[Experiment]:
    result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.runs))
        .order_by(Experiment.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_experiment(db: AsyncSession, experiment_id: str) -> Experiment | None:
    result = await db.execute(
        select(Experiment)
        .options(selectinload(Experiment.runs))
        .where(Experiment.id == experiment_id)
    )
    return result.scalar_one_or_none()


async def add_iteration(
    db: AsyncSession,
    *,
    session_id: str,
    iteration_number: int,
    coding_duration_ms: int,
    evaluation_id: str | None = None,
    review_verdict: Any | None = None,
    security_verdict: Any | None = None,
    tool_calls: list[dict[str, Any]] | None = None,
) -> AgentIteration:
    """Persist one orchestrator iteration together with the tools it invoked."""
    iteration = AgentIteration(
        id=str(uuid.uuid4()),
        session_id=session_id,
        iteration_number=iteration_number,
        evaluation_id=evaluation_id,
        coding_duration_ms=coding_duration_ms,
        review_verdict=review_verdict,
        security_verdict=security_verdict,
    )
    db.add(iteration)

    for call in tool_calls or []:
        db.add(
            ToolCall(
                id=str(uuid.uuid4()),
                iteration_id=iteration.id,
                tool_name=call["tool_name"],
                arguments=call.get("arguments") or {},
                result=call.get("result"),
                error=call.get("error"),
                duration_ms=call.get("duration_ms") or 0,
            )
        )

    await db.commit()
    return iteration


async def get_or_create_experiment(db: AsyncSession, name: str) -> Experiment:
    result = await db.execute(select(Experiment).where(Experiment.name == name))
    experiment = result.scalar_one_or_none()
    if not experiment:
        experiment = Experiment(id=str(uuid.uuid4()), name=name)
        db.add(experiment)
        await db.commit()
    return experiment


async def create_experiment_run(
    db: AsyncSession,
    *,
    experiment_id: str,
    session_id: str,
    model: str,
    provider: str,
    status: str,
    metrics: dict[str, Any] | None = None,
    parameters: dict[str, Any] | None = None,
) -> ExperimentRun:
    run = ExperimentRun(
        id=str(uuid.uuid4()),
        experiment_id=experiment_id,
        session_id=session_id,
        model=model,
        provider=provider,
        status=status,
        metrics=metrics or {},
        parameters=parameters or {},
    )
    db.add(run)
    await db.commit()
    return run


async def update_experiment_run(
    db: AsyncSession, run_id: str, **kwargs: Any
) -> ExperimentRun | None:
    result = await db.execute(select(ExperimentRun).where(ExperimentRun.id == run_id))
    run = result.scalar_one_or_none()
    if run:
        for key, value in kwargs.items():
            setattr(run, key, value)
        await db.commit()
    return run
