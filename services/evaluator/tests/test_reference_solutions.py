from __future__ import annotations

import json
from pathlib import Path

from ai_code_evaluator.runtime.harness import evaluate
from ai_code_evaluator.tasks import TaskLoader


def test_every_reference_solution_passes_every_case(
    task_loader: TaskLoader, repository_root: Path
) -> None:
    for task in task_loader.load_all():
        task_dir = repository_root / "benchmarks" / "python" / task.id
        job = {
            "function_name": task.function_name,
            "tests": [test.model_dump(mode="json") for test in task.tests],
        }
        outcome = evaluate(job, task_dir / "reference_solution.py")

        assert outcome["imported"], task.id
        assert outcome["function_exists"], task.id
        failures = [result for result in outcome["tests"] if result["status"] != "passed"]
        assert not failures, f"{task.id}: {json.dumps(failures, indent=2)}"
