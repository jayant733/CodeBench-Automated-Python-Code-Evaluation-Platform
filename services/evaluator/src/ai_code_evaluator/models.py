"""Typed domain and API models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Example(BaseModel):
    input: str
    output: str
    explanation: str | None = None


class TestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    visibility: Literal["visible", "hidden"]
    mode: Literal["direct", "retry", "pagination"] = "direct"
    input: dict[str, Any]
    expected: Any = None
    expected_exception: str | None = None


class TaskDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str
    summary: str
    difficulty: Literal["introductory", "intermediate", "advanced"]
    category: str
    instructions: str
    function_name: str
    signature: str
    starter_code: str
    time_limit_seconds: float = Field(gt=0, le=10)
    memory_limit_mb: int = Field(ge=64, le=512)
    examples: list[Example] = Field(min_length=1)
    tests: list[TestCase] = Field(min_length=2)

    @property
    def visible_tests(self) -> list[TestCase]:
        return [test for test in self.tests if test.visibility == "visible"]

    @property
    def hidden_tests(self) -> list[TestCase]:
        return [test for test in self.tests if test.visibility == "hidden"]


class PublicTestCase(BaseModel):
    id: str
    name: str
    input: dict[str, Any]
    expected: Any = None
    expected_exception: str | None = None


class TaskSummary(BaseModel):
    id: str
    title: str
    summary: str
    difficulty: Literal["introductory", "intermediate", "advanced"]
    category: str
    visible_test_count: int
    hidden_test_count: int


class PublicTask(TaskSummary):
    instructions: str
    function_name: str
    signature: str
    starter_code: str
    time_limit_seconds: float
    memory_limit_mb: int
    examples: list[Example]
    visible_tests: list[PublicTestCase]


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1, max_length=100)
    source_code: str = Field(min_length=1, max_length=50_000)


class TestResult(BaseModel):
    id: str
    name: str
    status: Literal["passed", "failed", "error"]
    runtime_ms: int = Field(ge=0)
    message: str | None = None


class HiddenTestSummary(BaseModel):
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    total: int = Field(ge=0)


class ScoreBreakdown(BaseModel):
    correctness: int = Field(ge=0, le=80)
    instruction_adherence: int = Field(ge=0, le=10)
    execution_signals: int = Field(ge=0, le=10)


class FeedbackItem(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"]


class EvaluationReport(BaseModel):
    evaluation_id: str
    task_id: str
    status: Literal["completed"]
    score: int = Field(ge=0, le=100)
    score_breakdown: ScoreBreakdown
    passed: bool
    summary: str
    visible_tests: list[TestResult]
    hidden_test_summary: HiddenTestSummary
    runtime_ms: int = Field(ge=0)
    stdout: str
    stderr: str
    feedback: list[FeedbackItem]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SourceAnalysis(BaseModel):
    syntax_valid: bool
    function_exists: bool
    prohibited_behavior_absent: bool
    syntax_message: str | None = None
    prohibited_imports: list[str] = Field(default_factory=list)


class ExecutionTestResult(BaseModel):
    id: str
    status: Literal["passed", "failed", "error"]
    runtime_ms: int
    message: str | None = None


class ExecutionOutcome(BaseModel):
    imported: bool
    function_exists: bool
    timed_out: bool = False
    runtime_ms: int
    stdout: str = ""
    stderr: str = ""
    tests: list[ExecutionTestResult] = Field(default_factory=list)
    fatal_code: str | None = None
    fatal_message: str | None = None


class ScoreSignals(BaseModel):
    syntax_valid: bool
    module_imported: bool
    function_exists: bool
    prohibited_behavior_absent: bool
    within_time_limit: bool
    no_runtime_error: bool
