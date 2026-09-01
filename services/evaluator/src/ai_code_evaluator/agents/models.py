from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_code_evaluator.providers import TokenUsage


class AgentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str = "gpt-4o"
    temperature: float = Field(0.0, ge=0, le=2)
    max_tokens: int = Field(4096, ge=1)
    provider: str = "openai"


class ToolCallRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: Literal["function"] = "function"
    function: dict[str, Any]


class AgentMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = None
    tool_calls: list[ToolCallRequest] | None = None
    name: str | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str
    structured_output: Any | None = None
    usage: TokenUsage
    model: str
    duration_ms: int


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    tool_calls_needed: list[str]


class CodingPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approach: str
    steps: list[PlanStep]
    edge_cases: list[str]
    estimated_complexity: Literal["low", "medium", "high"]


class ReviewIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["info", "warning", "error"]
    location: str
    description: str
    fix_hint: str | None = None


class ReviewVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool
    issues: list[ReviewIssue]
    suggestions: list[str]
    quality_score: int = Field(ge=0, le=10)


class SecurityFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "injection",
        "resource_abuse",
        "data_exfiltration",
        "prohibited_import",
        "sandbox_escape",
        "suspicious_pattern",
    ]
    severity: Literal["info", "warning", "critical"]
    evidence: str
    recommendation: str


class SecurityVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    safe: bool
    findings: list[SecurityFinding]
    risk_level: Literal["none", "low", "medium", "high", "critical"]


class TestFailureDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_id: str
    test_name: str
    expected: str
    actual: str
    message: str | None = None


class TestReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tests_run: int
    tests_passed: int
    tests_failed: int
    failure_details: list[TestFailureDetail]
    execution_time_ms: int
