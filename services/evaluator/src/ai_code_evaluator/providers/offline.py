"""Deterministic stand-in provider for running the agent loop without a model key.

This is not a language model and does not reason. It replays candidate solutions
that already exist in the benchmark fixtures so the orchestration path — tool
calls, evaluation, review, retry — can be exercised offline. Scores still come
from the sandbox, never from this class.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from ai_code_evaluator.models import TaskDefinition
from ai_code_evaluator.tasks import TaskLoader

from .base import GenerateResult, ModelProvider, StructuredResult, TokenUsage

TASK_TITLE_PATTERN = re.compile(r"^Task:\s*(.+)$", re.MULTILINE)


class OfflineProvider(ModelProvider):
    """Replays benchmark fixtures in escalating order of correctness."""

    def __init__(self, task_loader: TaskLoader | None = None) -> None:
        self.task_loader = task_loader or TaskLoader()
        self._model_name = "offline-fixture-replay"

    # --- code generation -------------------------------------------------

    async def generate(
        self,
        messages: Sequence[dict[str, Any]],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
        tools: list[dict[str, Any]] | None = None,
    ) -> GenerateResult:
        task = self._resolve_task(messages)
        tool_names = {
            tool.get("function", {}).get("name")
            for tool in tools or []
            if isinstance(tool, dict)
        }

        # Once the file is written, stop calling tools so the loop can evaluate.
        attempt = self._count_attempts(messages)
        if "write_file" not in tool_names or self._last_write_succeeded(messages):
            return GenerateResult(
                content="solution.py is in place; ready for evaluation.",
                tool_calls=None,
                usage=self._usage(messages),
                model=self._model_name,
                finish_reason="stop",
            )

        source = self._candidate_source(task, attempt)
        return GenerateResult(
            content=f"Writing attempt {attempt + 1} to solution.py.",
            tool_calls=[
                {
                    "id": f"call_offline_{attempt}",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps({"path": "solution.py", "content": source}),
                    },
                }
            ],
            usage=self._usage(messages),
            model=self._model_name,
            finish_reason="tool_calls",
        )

    # --- structured outputs ----------------------------------------------

    async def structured_generate(
        self,
        messages: Sequence[dict[str, Any]],
        response_format: type[BaseModel],
        model: str,
        temperature: float = 0.0,
        max_tokens: int | None = None,
    ) -> StructuredResult:
        # Agent memory accumulates across iterations; only the newest request is current.
        parsed = self._build_structured(response_format, self._latest_prompt(messages))
        return StructuredResult(
            parsed=parsed,
            usage=self._usage(messages),
            model=self._model_name,
        )

    def _build_structured(self, response_format: type[BaseModel], transcript: str) -> Any:
        name = response_format.__name__

        if name == "CodingPlan":
            return response_format(
                approach=(
                    "Implement the documented contract, then validate against the visible cases "
                    "before retrying."
                ),
                steps=[
                    {
                        "description": "Write the implementation to solution.py",
                        "tool_calls_needed": ["write_file"],
                    },
                    {
                        "description": "Evaluate the submission in the sandbox",
                        "tool_calls_needed": ["run_tests"],
                    },
                ],
                edge_cases=["empty input", "invalid types"],
                estimated_complexity="medium",
            )

        if name == "ReviewVerdict":
            failing = self._failure_count(transcript)
            return response_format(
                approved=failing == 0,
                issues=(
                    []
                    if failing == 0
                    else [
                        {
                            "severity": "error",
                            "location": "solution.py",
                            "description": f"{failing} case(s) still fail in the sandbox.",
                            "fix_hint": "Re-read the contract for the failing cases.",
                        }
                    ]
                ),
                suggestions=[] if failing == 0 else ["Handle the reported edge cases."],
                quality_score=10 if failing == 0 else 4,
            )

        if name == "SecurityVerdict":
            # Static signal only: the sandbox remains the real boundary.
            risky = [
                marker
                for marker in ("subprocess", "socket", "requests", "urllib", "os.system")
                if marker in transcript
            ]
            return response_format(
                safe=not risky,
                findings=[
                    {
                        "category": "prohibited_import",
                        "severity": "critical",
                        "evidence": f"Reference to '{marker}' found in the submission.",
                        "recommendation": "Remove network and process APIs.",
                    }
                    for marker in risky
                ],
                risk_level="none" if not risky else "high",
            )

        if name == "TestReport":
            passed, total = self._test_totals(transcript)
            return response_format(
                tests_run=total,
                tests_passed=passed,
                tests_failed=max(total - passed, 0),
                failure_details=[],
                execution_time_ms=0,
            )

        try:
            return response_format()
        except Exception:
            return None

    # --- fixture selection ------------------------------------------------

    def _candidate_source(self, task: TaskDefinition | None, attempt: int) -> str:
        """Escalate through plausible-but-wrong fixtures, then the reference solution."""
        if task is None:
            return "def solution():\n    raise NotImplementedError\n"

        task_dir = self.task_loader.root / task.id
        incorrect = sorted((task_dir / "incorrect_solutions").glob("*.py"))
        reference = task_dir / "reference_solution.py"

        if attempt < len(incorrect):
            return incorrect[attempt].read_text(encoding="utf-8")
        if reference.is_file():
            return reference.read_text(encoding="utf-8")
        return task.starter_code

    def _resolve_task(self, messages: Sequence[dict[str, Any]]) -> TaskDefinition | None:
        match = TASK_TITLE_PATTERN.search(self._transcript(messages))
        if not match:
            return None
        title = match.group(1).strip()
        for task in self.task_loader.load_all():
            if task.title == title:
                return task
        return None

    # --- transcript inspection --------------------------------------------

    @staticmethod
    def _latest_prompt(messages: Sequence[dict[str, Any]]) -> str:
        """Content of the most recent user turn, which is the request being answered."""
        for message in reversed(list(messages)):
            if message.get("role") == "user" and isinstance(message.get("content"), str):
                return message["content"]
        return ""

    @staticmethod
    def _transcript(messages: Sequence[dict[str, Any]]) -> str:
        parts: list[str] = []
        for message in messages:
            content = message.get("content")
            if isinstance(content, str):
                parts.append(content)
            for call in message.get("tool_calls") or []:
                function = call.get("function", {}) if isinstance(call, dict) else {}
                parts.append(str(function.get("arguments", "")))
        return "\n".join(parts)

    @staticmethod
    def _count_attempts(messages: Sequence[dict[str, Any]]) -> int:
        """Attempt number is derived from history, not a counter held by this class."""
        attempts = 0
        for message in messages:
            for call in message.get("tool_calls") or []:
                function = call.get("function", {}) if isinstance(call, dict) else {}
                if function.get("name") == "write_file":
                    attempts += 1
        return attempts

    @staticmethod
    def _last_write_succeeded(messages: Sequence[dict[str, Any]]) -> bool:
        """Only look at the current iteration, which starts at the latest user turn."""
        for message in reversed(list(messages)):
            if message.get("role") == "user":
                return False
            if message.get("role") != "tool" or message.get("name") != "write_file":
                continue
            content = message.get("content")
            if isinstance(content, str):
                try:
                    return bool(json.loads(content).get("success"))
                except (json.JSONDecodeError, AttributeError):
                    return False
        return False

    @staticmethod
    def _failure_count(transcript: str) -> int:
        match = re.search(r"passed (\d+) of (\d+) tests", transcript)
        if match:
            return int(match.group(2)) - int(match.group(1))
        # The reviewer prompt reports the sandbox score directly.
        match = re.search(r"score (\d+)/100", transcript)
        if match:
            return 0 if int(match.group(1)) == 100 else 1
        return 0

    @staticmethod
    def _test_totals(transcript: str) -> tuple[int, int]:
        match = re.search(r"passed (\d+) of (\d+) tests", transcript)
        if match:
            return int(match.group(1)), int(match.group(2))
        match = re.search(r"All (\d+) tests passed", transcript)
        if match:
            return int(match.group(1)), int(match.group(1))
        return 0, 0

    @staticmethod
    def _usage(messages: Sequence[dict[str, Any]]) -> TokenUsage:
        """Approximate accounting so token metrics are non-zero but clearly derived."""
        prompt_tokens = sum(
            len(str(message.get("content") or "")) // 4 for message in messages
        )
        return TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=0,
            total_tokens=prompt_tokens,
        )


def resolve_provider(task_loader: TaskLoader | None = None) -> tuple[ModelProvider, str]:
    """Return a real provider when a key is configured, otherwise the offline replay."""
    import os

    if os.getenv("OPENAI_API_KEY"):
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(), "openai"
    return OfflineProvider(task_loader), "offline"
