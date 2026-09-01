from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, Float, JSON
from sqlalchemy.orm import relationship

from .database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    summary = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    category = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class Experiment(Base):
    __tablename__ = "experiments"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    runs = relationship("ExperimentRun", back_populates="experiment")


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    
    id = Column(String, primary_key=True, index=True)
    experiment_id = Column(String, ForeignKey("experiments.id"), nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    status = Column(String, nullable=False) # completed, failed, error
    metrics = Column(JSON, nullable=False, default=dict)
    parameters = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    experiment = relationship("Experiment", back_populates="runs")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"
    
    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False, index=True)
    session_id = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False)
    score = Column(Integer, nullable=False, default=0)
    score_breakdown = Column(JSON, nullable=False, default=dict)
    passed = Column(Boolean, nullable=False, default=False)
    runtime_ms = Column(Integer, nullable=False, default=0)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    feedback = Column(JSON, nullable=False, default=list)
    visible_tests = Column(JSON, nullable=False, default=list)
    hidden_test_summary = Column(JSON, nullable=False, default=dict)
    source_code = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now)


class AgentSession(Base):
    __tablename__ = "agent_sessions"

    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False, index=True)
    experiment_run_id = Column(String, ForeignKey("experiment_runs.id"), nullable=True)
    status = Column(String, nullable=False) # in_progress, completed, failed
    final_score = Column(Integer, nullable=True)
    iterations_used = Column(Integer, nullable=False, default=0)
    total_duration_ms = Column(Integer, nullable=False, default=0)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    iterations = relationship("AgentIteration", back_populates="session", order_by="AgentIteration.iteration_number")


class AgentIteration(Base):
    __tablename__ = "agent_iterations"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("agent_sessions.id"), nullable=False, index=True)
    iteration_number = Column(Integer, nullable=False)
    evaluation_id = Column(String, ForeignKey("evaluation_runs.id"), nullable=True)
    coding_duration_ms = Column(Integer, nullable=False, default=0)
    review_verdict = Column(JSON, nullable=True)
    security_verdict = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    session = relationship("AgentSession", back_populates="iterations")
    tool_calls = relationship("ToolCall", back_populates="iteration")


class ToolCall(Base):
    __tablename__ = "tool_calls"
    
    id = Column(String, primary_key=True, index=True)
    iteration_id = Column(String, ForeignKey("agent_iterations.id"), nullable=False, index=True)
    tool_name = Column(String, nullable=False)
    arguments = Column(JSON, nullable=False, default=dict)
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=utc_now)
    
    iteration = relationship("AgentIteration", back_populates="tool_calls")
