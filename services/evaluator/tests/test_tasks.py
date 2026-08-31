from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_code_evaluator.errors import TaskNotFoundError
from ai_code_evaluator.tasks import TaskLoader


def test_loads_five_ordered_tasks_with_both_test_visibilities(
    task_loader: TaskLoader,
) -> None:
    tasks = task_loader.load_all()

    assert len(tasks) == 5
    assert [task.id for task in tasks] == sorted(task.id for task in tasks)
    assert all(task.visible_tests for task in tasks)
    assert all(task.hidden_tests for task in tasks)


def test_public_projection_never_includes_hidden_case_details(
    task_loader: TaskLoader,
) -> None:
    definition = task_loader.get("palindrome-normalization")
    public = task_loader.get_public(definition.id)
    serialized = public.model_dump_json()

    assert len(public.visible_tests) == len(definition.visible_tests)
    assert public.hidden_test_count == len(definition.hidden_tests)
    for hidden_test in definition.hidden_tests:
        assert hidden_test.id not in serialized
        assert hidden_test.name not in serialized


def test_unknown_task_raises_domain_error(task_loader: TaskLoader) -> None:
    with pytest.raises(TaskNotFoundError):
        task_loader.get("not-a-task")


def test_rejects_task_without_hidden_tests(tmp_path: Path) -> None:
    task_dir = tmp_path / "sample"
    task_dir.mkdir()
    payload = {
        "id": "sample",
        "title": "Sample",
        "summary": "A sample",
        "difficulty": "introductory",
        "category": "Test",
        "instructions": "Implement it.",
        "function_name": "sample",
        "signature": "def sample(): ...",
        "starter_code": "def sample():\n    pass\n",
        "time_limit_seconds": 1,
        "memory_limit_mb": 64,
        "examples": [{"input": "None", "output": "None"}],
        "tests": [
            {
                "id": "one",
                "name": "Only visible",
                "visibility": "visible",
                "mode": "direct",
                "input": {"args": []},
                "expected": None,
            },
            {
                "id": "two",
                "name": "Also visible",
                "visibility": "visible",
                "mode": "direct",
                "input": {"args": []},
                "expected": None,
            },
        ],
    }
    (task_dir / "task.json").write_text(json.dumps(payload), encoding="utf-8")
    (task_dir / "reference_solution.py").write_text(
        "def sample():\n    return None\n", encoding="utf-8"
    )

    with pytest.raises(RuntimeError, match="visible and hidden"):
        TaskLoader(tmp_path).load_all()
