from __future__ import annotations

import logging
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


async def get_or_create_task(db: AsyncSession, task_id: str, title: str, summary: str, difficulty: str, category: str) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        task = Task(id=task_id, title=title, summary=summary, difficulty=difficulty, category=category)
        db.add(task)
        await db.commit()
    return task


async def create_evaluation_run(db: AsyncSession, eval_id: str, task_id: str, session_id: str | None, **kwargs: Any) -> EvaluationRun:
    run = EvaluationRun(id=eval_id, task_id=task_id, session_id=session_id, **kwargs)
    db.add(run)
    await db.commit()
    return run


async def create_agent_session(db: AsyncSession, session_id: str, task_id: str, experiment_run_id: str | None = None) -> AgentSession:
    session = AgentSession(id=session_id, task_id=task_id, experiment_run_id=experiment_run_id, status="in_progress")
    db.add(session)
    await db.commit()
    return session


async def update_agent_session(db: AsyncSession, session_id: str, **kwargs: Any) -> AgentSession | None:
    result = await db.execute(select(AgentSession).where(AgentSession.id == session_id))
    session = result.scalar_one_or_none()
    if session:
        for k, v in kwargs.items():
            setattr(session, k, v)
        await db.commit()
    return session


async def create_agent_iteration(db: AsyncSession, iteration_id: str, session_id: str, iteration_number: int, **kwargs: Any) -> AgentIteration:
    iteration = AgentIteration(id=iteration_id, session_id=session_id, iteration_number=iteration_number, **kwargs)
    db.add(iteration)
    await db.commit()
    return iteration


async def create_tool_call(db: AsyncSession, tool_call_id: str, iteration_id: str, tool_name: str, arguments: dict[str, Any], **kwargs: Any) -> ToolCall:
    tc = ToolCall(id=tool_call_id, iteration_id=iteration_id, tool_name=tool_name, arguments=arguments, **kwargs)
    db.add(tc)
    await db.commit()
    return tc


async def get_agent_session(db: AsyncSession, session_id: str) -> AgentSession | None:
    result = await db.execute(
        select(AgentSession)
        .options(
            selectinload(AgentSession.iterations).selectinload(AgentIteration.tool_calls)
        )
        .where(AgentSession.id == session_id)
    )
    return result.scalar_one_or_none()
