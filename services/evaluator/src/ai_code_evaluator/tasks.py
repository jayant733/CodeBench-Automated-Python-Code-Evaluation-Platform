"""Version-controlled task discovery and public projections."""

from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import ValidationError

from .errors import TaskNotFoundError
from .models import PublicTask, PublicTestCase, TaskDefinition, TaskSummary


def default_benchmark_root() -> Path:
    configured = os.getenv("EVALUATOR_BENCHMARK_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parents[4] / "benchmarks" / "python"


class TaskLoader:
    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or default_benchmark_root()).resolve()

    def load_all(self) -> list[TaskDefinition]:
        if not self.root.is_dir():
            raise RuntimeError(f"Benchmark directory is unavailable: {self.root}")

        tasks: list[TaskDefinition] = []
        seen_ids: set[str] = set()
        for path in sorted(self.root.glob("*/task.json")):
            try:
                task = TaskDefinition.model_validate_json(path.read_text(encoding="utf-8"))
            except (OSError, ValidationError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"Invalid task definition: {path}") from exc

            if task.id in seen_ids:
                raise RuntimeError(f"Duplicate task identifier: {task.id}")
            if path.parent.name != task.id:
                raise RuntimeError(
                    f"Task directory '{path.parent.name}' does not match identifier '{task.id}'"
                )
            if not task.visible_tests or not task.hidden_tests:
                raise RuntimeError(f"Task '{task.id}' needs visible and hidden tests")
            test_ids = [test.id for test in task.tests]
            if len(test_ids) != len(set(test_ids)):
                raise RuntimeError(f"Task '{task.id}' contains duplicate test identifiers")
            if not (path.parent / "reference_solution.py").is_file():
                raise RuntimeError(f"Task '{task.id}' has no reference solution")

            seen_ids.add(task.id)
            tasks.append(task)

        if not tasks:
            raise RuntimeError(f"No tasks found in {self.root}")
        return tasks

    def get(self, task_id: str) -> TaskDefinition:
        for task in self.load_all():
            if task.id == task_id:
                return task
        raise TaskNotFoundError(task_id)

    def list_public(self) -> list[TaskSummary]:
        return [
            TaskSummary(
                id=task.id,
                title=task.title,
                summary=task.summary,
                difficulty=task.difficulty,
                category=task.category,
                visible_test_count=len(task.visible_tests),
                hidden_test_count=len(task.hidden_tests),
            )
            for task in self.load_all()
        ]

    def get_public(self, task_id: str) -> PublicTask:
        task = self.get(task_id)
        return PublicTask(
            id=task.id,
            title=task.title,
            summary=task.summary,
            difficulty=task.difficulty,
            category=task.category,
            visible_test_count=len(task.visible_tests),
            hidden_test_count=len(task.hidden_tests),
            instructions=task.instructions,
            function_name=task.function_name,
            signature=task.signature,
            starter_code=task.starter_code,
            time_limit_seconds=task.time_limit_seconds,
            memory_limit_mb=task.memory_limit_mb,
            examples=task.examples,
            visible_tests=[
                PublicTestCase(
                    id=test.id,
                    name=test.name,
                    input=test.input,
                    expected=test.expected,
                    expected_exception=test.expected_exception,
                )
                for test in task.visible_tests
            ],
        )
